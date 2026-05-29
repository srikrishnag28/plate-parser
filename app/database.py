import logging
from typing import Any, Optional
from .storage import get_client

logger = logging.getLogger(__name__)


# ── Jobs ──────────────────────────────────────────────────────────────────────

async def create_job(input_file_url: str, docs_url: str) -> str:
    client = get_client()
    result = (
        client.table("jobs")
        .insert({"input_file_url": input_file_url, "docs_url": docs_url, "status": "processing"})
        .execute()
    )
    return result.data[0]["id"]


async def update_job(job_id: str, **fields) -> None:
    client = get_client()
    client.table("jobs").update(fields).eq("id", job_id).execute()


async def get_job(job_id: str) -> Optional[dict]:
    client = get_client()
    result = client.table("jobs").select("*").eq("id", job_id).execute()
    return result.data[0] if result.data else None


# ── Parsers ───────────────────────────────────────────────────────────────────

async def save_parser(name: str, instrument: str, parser_code: str, job_id: str) -> str:
    client = get_client()
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
    client = get_client()
    result = client.table("parsers").select("*").eq("id", parser_id).execute()
    return result.data[0] if result.data else None


async def list_parsers() -> list[dict]:
    client = get_client()
    result = client.table("parsers").select("*").eq("is_active", True).order("created_at", desc=True).execute()
    return result.data


# ── Parser runs ───────────────────────────────────────────────────────────────

async def create_run(parser_id: str, output_json_url: str, status: str) -> str:
    client = get_client()
    result = (
        client.table("parser_runs")
        .insert({"parser_id": parser_id, "output_json_url": output_json_url, "status": status})
        .execute()
    )
    return result.data[0]["id"]
