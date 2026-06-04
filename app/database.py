import uuid
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# In-memory parser cache — keyed by instrument_type.
# Survives for the lifetime of the server process.
# Acts as a fallback when the DB migration hasn't been run yet.
_parser_cache: dict[str, dict] = {}


def _get_client():
    from .storage import get_client
    return get_client()


# ── Jobs ──────────────────────────────────────────────────────────────────────

async def create_job(input_file_url: str, docs_url: str) -> str:
    client = _get_client()
    result = (
        client.table("jobs")
        .insert({"input_file_url": input_file_url, "docs_url": docs_url, "status": "processing"})
        .execute()
    )
    return result.data[0]["id"]


async def update_job(job_id: str, **fields) -> None:
    client = _get_client()
    client.table("jobs").update(fields).eq("id", job_id).execute()


async def get_job(job_id: str) -> Optional[dict]:
    client = _get_client()
    result = client.table("jobs").select("*").eq("id", job_id).execute()
    return result.data[0] if result.data else None


# ── Parsers ───────────────────────────────────────────────────────────────────

async def save_parser(name: str, instrument: str, parser_code: str, job_id: str) -> str:
    client = _get_client()
    result = (
        client.table("parsers")
        .insert({
            "name": name,
            "instrument": instrument,
            "parser_code": parser_code,
            "job_id": job_id,
            "is_active": True,
            "version": 1,
        })
        .execute()
    )
    return result.data[0]["id"]


async def get_parser(parser_id: str) -> Optional[dict]:
    client = _get_client()
    result = client.table("parsers").select("*").eq("id", parser_id).execute()
    return result.data[0] if result.data else None


async def list_parsers() -> list[dict]:
    client = _get_client()
    result = (
        client.table("parsers")
        .select("*")
        .eq("is_active", True)
        .order("created_at", desc=True)
        .execute()
    )
    return result.data


# ── Parser runs ───────────────────────────────────────────────────────────────

async def create_run(parser_id: str, output_json_url: str, status: str) -> str:
    client = _get_client()
    result = (
        client.table("parser_runs")
        .insert({"parser_id": parser_id, "output_json_url": output_json_url, "status": status})
        .execute()
    )
    return result.data[0]["id"]


# ── Pipeline rearchitecture ───────────────────────────────────────────────────

async def get_parser_by_type(instrument_type: str) -> Optional[dict]:
    """
    Look up the active parser for a given instrument_type key.
    Falls back to in-memory cache if the DB column doesn't exist yet (pre-migration).
    """
    # Try DB first
    try:
        client = _get_client()
        result = (
            client.table("parsers")
            .select("*")
            .eq("instrument_type", instrument_type)
            .eq("is_active", True)
            .limit(1)
            .execute()
        )
        if result.data:
            _parser_cache[instrument_type] = result.data[0]  # keep cache warm
            return result.data[0]
        return None
    except Exception:
        # Column doesn't exist yet — fall back to in-memory cache
        return _parser_cache.get(instrument_type)


async def save_parser_by_type(
    instrument_type: str,
    name: str,
    instrument: str,
    parser_code: str,
    research_summary: str,
    job_id: Optional[str] = None,
) -> str:
    """
    Upsert parser by instrument_type.
    Deactivates any existing active parser for that type and saves a new versioned row.
    """
    client = _get_client()
    existing = await get_parser_by_type(instrument_type)

    new_version = 1
    if existing:
        client.table("parsers").update({"is_active": False}).eq("id", existing["id"]).execute()
        new_version = existing.get("version", 1) + 1

    result = (
        client.table("parsers")
        .insert({
            "name": name,
            "instrument": instrument,
            "instrument_type": instrument_type,
            "parser_code": parser_code,
            "research_summary": research_summary,
            "job_id": job_id,
            "is_active": True,
            "version": new_version,
        })
        .execute()
    )
    parser_id = result.data[0]["id"]
    # Keep in-memory cache in sync
    _parser_cache[instrument_type] = {**result.data[0]}
    return parser_id


async def create_pipeline_run(parser_id: Optional[str] = None) -> str:
    client = _get_client()
    result = (
        client.table("pipeline_runs")
        .insert({"parser_id": parser_id})
        .execute()
    )
    return result.data[0]["id"]


async def record_pipeline_stage(
    pipeline_run_id: str,
    stage: str,
    status: str,
    summary: str = "",
    duration_ms: int = 0,
) -> None:
    client = _get_client()
    client.table("pipeline_stages").insert({
        "pipeline_run_id": pipeline_run_id,
        "stage": stage,
        "status": status,
        "summary": summary,
        "duration_ms": duration_ms,
    }).execute()
