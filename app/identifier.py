"""
Plate-reader identification via a single AI classification call.

Produces a composite key like "<manufacturer>_<model>_<read_type>" (used to look
up and store parsers in the DB) plus an is_plate_reader flag so the pipeline can reject
non-plate-reader files early. Nothing about specific vendors is hardcoded —
the model decides everything from the file. Never raises.
"""

import re
import json
import logging
from collections import Counter
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class InstrumentID:
    instrument: str    # snake_case vendor+model slug, or "unknown"
    read_type: str     # "endpoint" | "kinetic" | "fluorescence" | "spectrum" | "unknown"
    type_key: str      # composite DB key: f"{instrument}_{read_type}"
    method: str        # "llm" | "unknown"
    confidence: str    # "high" | "medium" | "low"
    is_plate_reader: bool = True


_CLASSIFICATION_SYSTEM = """You are a plate reader data format expert.
Analyse the file summary below and classify it. Decide everything from the data itself — do not assume a vendor.

Return ONLY valid JSON with exactly these fields:
{
  "is_plate_reader": true|false,
  "instrument_type": "<lowercase snake_case manufacturer_model slug derived from the file, or 'unknown' if it cannot be determined>",
  "read_type": "endpoint|kinetic|fluorescence|spectrum|unknown",
  "confidence": "high|medium|low"
}

Set "is_plate_reader" to false if the file is clearly some other instrument (e.g. mass spectrometry, qPCR, chromatography) or not instrument data at all."""


def identify(content: str) -> InstrumentID:
    """Classify the file with one AI call. Never raises — falls back to unknown."""
    try:
        result = _classify(content)

        if not bool(result.get("is_plate_reader", True)):
            logger.info("Classified as NOT a plate reader")
            return InstrumentID(
                instrument="unknown", read_type="unknown", type_key="unknown",
                method="llm", confidence=result.get("confidence", "high"),
                is_plate_reader=False,
            )

        inst = (result.get("instrument_type") or "unknown").strip().lower() or "unknown"
        rt   = (result.get("read_type") or "unknown").strip().lower() or "unknown"
        logger.info("Classified as plate reader: %s / %s", inst, rt)
        return InstrumentID(
            instrument=inst, read_type=rt, type_key=f"{inst}_{rt}",
            method="llm", confidence=result.get("confidence", "medium"),
            is_plate_reader=True,
        )
    except Exception as e:
        # Fail open: don't block a possibly-valid file if classification fails.
        logger.warning("Identifier error (%s) — treating as unknown plate reader", e)
        return InstrumentID(
            instrument="unknown", read_type="unknown", type_key="unknown",
            method="unknown", confidence="low", is_plate_reader=True,
        )


def _build_summary(content: str) -> str:
    """Compress a possibly-large file into a representative summary for the LLM."""
    lines = content.splitlines()
    n = len(lines)
    mid = n // 2

    col_counts = Counter(len(l.split("\t")) for l in lines if l.strip())
    header_lines = [l for l in lines if re.match(r"^[A-Za-z][A-Za-z ]+[\t:]", l)][:20]

    return (
        f"Total lines: {n}\n"
        f"Likely delimiter: {'tab' if col_counts and col_counts.most_common(1)[0][0] > 2 else 'comma'}\n"
        f"Column count distribution: {dict(col_counts.most_common(5))}\n"
        f"First 10 lines:\n" + "\n".join(lines[:10]) + "\n\n"
        f"Lines around middle (line {mid}):\n" + "\n".join(lines[max(0, mid - 5):mid + 5]) + "\n\n"
        f"Last 10 lines:\n" + "\n".join(lines[-10:]) + "\n\n"
        f"Metadata-style lines found anywhere:\n" + "\n".join(header_lines)
    )


def _classify(content: str) -> dict:
    # Import here to avoid a circular import (agent imports nothing from here at module load).
    from .agent import _get_client, AI_MODEL

    client = _get_client()
    response = client.chat.completions.create(
        model=AI_MODEL,
        messages=[
            {"role": "system", "content": _CLASSIFICATION_SYSTEM},
            {"role": "user",   "content": f"Classify this file:\n\n{_build_summary(content)}"},
        ],
        temperature=0,
    )
    raw = (response.choices[0].message.content or "").strip()
    match = re.search(r"```(?:json)?\n?(.*?)```", raw, re.DOTALL)
    if match:
        raw = match.group(1).strip()
    return json.loads(raw)
