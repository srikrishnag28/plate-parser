import os
import logging
import uuid
import json
from supabase import create_client, Client

logger = logging.getLogger(__name__)

_client: Client | None = None

_MIME_BY_EXT = {
    "csv": "text/csv",
    "txt": "text/csv",
    "pdf": "application/pdf",
    "json": "application/json",
}


def _mime_for(filename: str, fallback: str) -> str:
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    return _MIME_BY_EXT.get(ext, fallback)


def get_client() -> Client:
    global _client
    if _client is None:
        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_KEY")
        if not url or not key:
            raise RuntimeError("SUPABASE_URL and SUPABASE_KEY must be set")
        _client = create_client(url, key)
    return _client


async def upload_file(bucket: str, content: bytes, filename: str, content_type: str) -> str:
    """Upload bytes to Supabase storage bucket. Returns public URL."""
    client = get_client()
    path = f"{uuid.uuid4()}/{filename}"
    mime = _mime_for(filename, content_type)
    client.storage.from_(bucket).upload(
        path,
        content,
        file_options={"content-type": mime},
    )
    return client.storage.from_(bucket).get_public_url(path)


async def upload_json(bucket: str, data: dict, filename: str) -> str:
    """Serialize dict to JSON and upload to storage. Returns public URL."""
    content = json.dumps(data, indent=2).encode("utf-8")
    return await upload_file(bucket, content, filename, "application/json")
