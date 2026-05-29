import os
import logging
import uuid
from supabase import create_client, Client

logger = logging.getLogger(__name__)

_client: Client | None = None


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
    client.storage.from_(bucket).upload(
        path,
        content,
        file_options={"content-type": content_type},
    )
    result = client.storage.from_(bucket).get_public_url(path)
    return result


async def upload_json(bucket: str, data: dict, filename: str) -> str:
    """Serialize dict to JSON and upload to storage. Returns public URL."""
    import json
    content = json.dumps(data, indent=2).encode("utf-8")
    return await upload_file(bucket, content, filename, "application/json")
