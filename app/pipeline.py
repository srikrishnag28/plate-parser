"""
Research-first autonomous pipeline.

Orchestrates the 5-stage flow and yields SSE-ready dicts:
  identify → research → generate → save → execute

Each stage emits {stage, status, summary?, duration_ms?, error?}.
Log events:         {stage: "log",      status: "info"|"warning"|"error", message}.
Final event:        {stage: "complete", status: "done", output_json, parser_id, ...}.
"""

import asyncio
import json
import time
import logging
from typing import AsyncGenerator

from .identifier import identify, InstrumentID
from .agent import research_instrument, generate_parser_with_research
from .sandbox import run_parser_in_sandbox
from .validator import validate_output
from .database import (
    get_parser_by_type,
    save_parser_by_type,
    create_pipeline_run,
    record_pipeline_stage,
)
from .storage import upload_json

logger = logging.getLogger(__name__)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _ev(stage: str, status: str, **kwargs) -> dict:
    return {"stage": stage, "status": status, **kwargs}


def _log(message: str, level: str = "info") -> dict:
    return {"stage": "log", "status": level, "message": message}


def _ms(t0: float) -> int:
    return int((time.monotonic() - t0) * 1000)


def _truncate(s: str, n: int = 300) -> str:
    return s[:n] + "…" if len(s) > n else s


async def _record(pipeline_run_id: str, stage: str, status: str, summary: str = "", duration_ms: int = 0) -> None:
    """Non-fatal wrapper — silently ignores DB errors (e.g. missing tables before migration)."""
    try:
        await record_pipeline_stage(pipeline_run_id, stage, status, summary, duration_ms)
    except Exception as e:
        logger.debug("record_pipeline_stage skipped: %s", e)


# ── Pipeline ──────────────────────────────────────────────────────────────────

async def run_pipeline(
    csv_content: str,
    pdf_bytes: bytes | None,
    csv_filename: str,
) -> AsyncGenerator[dict, None]:
    """
    Async generator — yields SSE event dicts for each stage transition + log events.
    Uses asyncio.to_thread() for all synchronous blocking calls (AI provider, sandbox).
    """
    yield _log(f"Pipeline started — file: {csv_filename} ({len(csv_content.splitlines())} lines)")
    if pdf_bytes:
        yield _log(f"PDF documentation attached ({len(pdf_bytes) // 1024} KB)")
    else:
        yield _log("No PDF — will use web search for instrument documentation")

    try:
        pipeline_run_id = await create_pipeline_run()
        yield _log(f"Pipeline run ID: {pipeline_run_id[:8]}…")
    except Exception:
        import uuid as _uuid
        pipeline_run_id = str(_uuid.uuid4())
        yield _log("pipeline_runs table not found — run SQL migration in Supabase (using in-memory ID)", "warning")

    existing_parser: dict | None = None

    # ── Stage 1: IDENTIFY ────────────────────────────────────────────────────
    yield _ev("identify", "running")
    yield _log("Scanning file for instrument keywords…")
    t0 = time.monotonic()
    try:
        iid: InstrumentID = await asyncio.to_thread(identify, csv_content)
        dur = _ms(t0)

        if iid.method == "llm" and iid.type_key != "unknown":
            yield _log(f"AI classification: {iid.instrument} / {iid.read_type} ({iid.confidence} confidence, {dur}ms)")
        else:
            yield _log("Instrument not recognised — will research from scratch", "warning")

        summary = (
            f"{iid.type_key} ({iid.method} match, {iid.confidence} confidence)"
            if iid.method != "unknown"
            else "Unknown instrument — will research and generate fresh parser"
        )
        await _record(pipeline_run_id, "identify", "done", summary, dur)
        yield _ev("identify", "done", summary=summary, duration_ms=dur)
    except Exception as e:
        yield _log(f"Identification failed: {e}", "error")
        yield _ev("identify", "error", error=str(e))
        return

    # ── Reject non-plate-reader files early ────────────────────────────────────
    if not iid.is_plate_reader:
        msg = "This file does not look like a plate reader export. This system only parses plate reader data."
        yield _log(msg, "error")
        await _record(pipeline_run_id, "identify", "error", msg, 0)
        yield _ev("identify", "error", error=msg)
        yield _ev("complete", "error", error=msg)
        return

    # ── DB lookup ────────────────────────────────────────────────────────────
    if iid.type_key != "unknown":
        yield _log(f"Checking parser library for: {iid.type_key}")
        try:
            existing_parser = await get_parser_by_type(iid.type_key)
            if existing_parser:
                yield _log(f"Cache hit — parser v{existing_parser.get('version', 1)} found (id: {existing_parser['id'][:8]}…)")
            else:
                yield _log("Cache miss — no saved parser for this instrument type")
        except Exception as e:
            yield _log(f"DB lookup failed (migration needed?): {e}", "warning")
            existing_parser = None

    # ── CACHED PATH ───────────────────────────────────────────────────────────
    if existing_parser:
        yield _ev("research", "skipped", summary=f"Known instrument — using saved parser v{existing_parser.get('version', 1)}")
        yield _ev("generate", "skipped", summary="Cached parser loaded")
        yield _ev("save",     "skipped", summary="Parser already in library")

        yield _ev("execute", "running")
        yield _log("Running cached parser in sandbox…")
        t0 = time.monotonic()
        try:
            output_json = await asyncio.to_thread(
                run_parser_in_sandbox, existing_parser["parser_code"], csv_content
            )
            valid, err = validate_output(output_json)
            if not valid:
                raise RuntimeError(f"Schema validation failed: {err}")
            dur = _ms(t0)
            wells = len(output_json.get("plate_reader_document", {}).get("wells", []))
            yield _log(f"Sandbox OK — {wells} wells extracted in {dur}ms")
            await _record(pipeline_run_id, "execute", "done", f"{wells} wells extracted", dur)
            yield _ev("execute", "done", summary=f"{wells} wells extracted", duration_ms=dur)
            yield _ev(
                "complete", "done",
                output_json=output_json,
                parser_id=existing_parser["id"],
                parser_code=existing_parser["parser_code"],
                pipeline_run_id=pipeline_run_id,
                cached=True,
            )
            return
        except Exception as e:
            yield _log(f"Cached parser failed: {e} — triggering re-research", "warning")
            yield _ev("execute", "error", error=str(e), summary="Saved parser failed — re-researching and regenerating")
            existing_parser = None

    # ── FULL PIPELINE PATH ────────────────────────────────────────────────────

    # Stage 2: RESEARCH
    yield _ev("research", "running")
    yield _log("Calling private AI provider (private inference) with web search enabled…")
    yield _log(f"Research target: {iid.type_key} export format")
    t0 = time.monotonic()
    research_summary = ""
    try:
        research_summary = await asyncio.to_thread(
            research_instrument, iid.type_key, csv_content, pdf_bytes
        )
        dur = _ms(t0)
        yield _log(f"Research complete — {len(research_summary)} chars of context gathered in {dur}ms)")
        try:
            rdata = json.loads(research_summary)
            if rdata.get("known_edge_cases"):
                yield _log(f"Edge cases found: {len(rdata['known_edge_cases'])} — {', '.join(str(e) for e in rdata['known_edge_cases'][:3])}")
            if rdata.get("delimiter"):
                yield _log(f"Delimiter: {rdata['delimiter']}")
            if rdata.get("sources"):
                yield _log(f"Sources: {', '.join(str(s) for s in rdata['sources'][:3])}")
            excerpt = (
                f"{rdata.get('instrument_name', '')} — "
                f"{rdata.get('export_format_description', '')[:150]}"
            ).strip(" —")
        except Exception:
            excerpt = _truncate(research_summary)
        await _record(pipeline_run_id, "research", "done", excerpt, dur)
        yield _ev("research", "done", summary=excerpt, duration_ms=dur)
    except Exception as e:
        dur = _ms(t0)
        yield _log(f"Research failed: {e} — continuing with data-only generation", "warning")
        await _record(pipeline_run_id, "research", "error", str(e), dur)
        yield _ev("research", "error", error=str(e), summary="Research failed — generating from data only")

    # Stage 3: GENERATE
    yield _ev("generate", "running")
    yield _log("Sending data sample + research context to private AI provider…")
    t0 = time.monotonic()
    try:
        parser_code, output_json = await asyncio.to_thread(
            generate_parser_with_research,
            csv_content, pdf_bytes, research_summary, iid.type_key,
        )
        dur = _ms(t0)
        lines = len(parser_code.splitlines())
        yield _log(f"Parser generated — {lines} lines of Python in {dur}ms")
        yield _log("Running generated parser in sandbox to validate…")

        wells_count = len(output_json.get("plate_reader_document", {}).get("wells", []))
        instrument_name = output_json.get("plate_reader_document", {}).get("instrument", {}).get("model", "?")
        yield _log(f"Sandbox OK — {wells_count} wells, instrument: {instrument_name}")

        await _record(pipeline_run_id, "generate", "done", f"Parser generated ({lines} lines)", dur)
        yield _ev("generate", "done", summary=f"Parser generated ({lines} lines)", duration_ms=dur)
    except Exception as e:
        dur = _ms(t0)
        yield _log(f"Generation failed after retries: {e}", "error")
        await _record(pipeline_run_id, "generate", "error", str(e), dur)
        yield _ev("generate", "error", error=str(e))
        return

    # Stage 4: SAVE
    yield _ev("save", "running")
    t0 = time.monotonic()
    instrument_label = iid.type_key.replace("_", " ").title()
    try:
        rdata = json.loads(research_summary)
        instrument_label = rdata.get("instrument_name") or instrument_label
    except Exception:
        pass

    save_key = iid.type_key
    if save_key == "unknown":
        try:
            rdata = json.loads(research_summary)
            guessed = rdata.get("instrument_type") or rdata.get("manufacturer", "unknown")
            read_t  = iid.read_type if iid.read_type != "unknown" else "endpoint"
            save_key = f"{guessed.lower().replace(' ', '_')}_{read_t}"
            yield _log(f"Unknown instrument resolved to: {save_key}")
        except Exception:
            save_key = f"unknown_{int(time.time())}"

    yield _log(f"Saving parser as: {save_key}")
    try:
        try:
            parser_id = await save_parser_by_type(
                instrument_type=save_key,
                name=f"Parser for {instrument_label}",
                instrument=instrument_label,
                parser_code=parser_code,
                research_summary=research_summary,
            )
        except Exception as db_err:
            from .database import save_parser, _parser_cache
            parser_id = await save_parser(
                name=f"Parser for {instrument_label}",
                instrument=instrument_label,
                parser_code=parser_code,
                job_id=None,
            )
            # Populate in-memory cache so next call for same instrument is instant
            _parser_cache[save_key] = {
                "id": parser_id,
                "parser_code": parser_code,
                "version": 1,
                "instrument_type": save_key,
            }
            yield _log(f"Used legacy save (run SQL migration to enable versioning): {db_err}", "warning")

        dur = _ms(t0)
        yield _log(f"Parser saved — id: {parser_id[:8]}… version: {save_key}")
        await _record(pipeline_run_id, "save", "done", f"Saved as {save_key} (id: {parser_id[:8]}…)", dur)
        yield _ev("save", "done", summary=f"Saved as {save_key}", duration_ms=dur)
    except Exception as e:
        dur = _ms(t0)
        yield _log(f"Save failed: {e}", "error")
        await _record(pipeline_run_id, "save", "error", str(e), dur)
        yield _ev("save", "error", error=str(e))
        return

    # Stage 5: EXECUTE
    yield _ev("execute", "running")
    t0 = time.monotonic()
    wells = len(output_json.get("plate_reader_document", {}).get("wells", []))
    dur = _ms(t0)
    yield _log(f"Pipeline complete — {wells} wells ready")
    await _record(pipeline_run_id, "execute", "done", f"{wells} wells extracted", dur)
    yield _ev("execute", "done", summary=f"{wells} wells extracted", duration_ms=dur)

    try:
        await upload_json("outputs", output_json, f"run_{parser_id}.json")
        yield _log("Output JSON persisted to storage")
    except Exception as e:
        yield _log(f"Storage upload failed (non-fatal): {e}", "warning")

    yield _ev(
        "complete", "done",
        output_json=output_json,
        parser_id=parser_id,
        parser_code=parser_code,
        pipeline_run_id=pipeline_run_id,
        cached=False,
    )
