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


def _list_all_paths(client: Client, bucket: str, prefix: str = "") -> list[str]:
    """Recursively collect every file path in a bucket (files are nested under uuid folders)."""
    paths: list[str] = []
    for item in client.storage.from_(bucket).list(prefix):
        name = item["name"]
        full = f"{prefix}/{name}" if prefix else name
        if item.get("id") is None:  # folder
            paths.extend(_list_all_paths(client, bucket, full))
        else:
            paths.append(full)
    return paths


async def clear_storage(buckets: tuple[str, ...] = ("uploads", "outputs")) -> None:
    """Remove all objects from the given storage buckets."""
    client = get_client()
    for bucket in buckets:
        paths = _list_all_paths(client, bucket)
        if paths:
            client.storage.from_(bucket).remove(paths)
