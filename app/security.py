import os
import logging
from fastapi import HTTPException, Security, UploadFile
from fastapi.security.api_key import APIKeyHeader

logger = logging.getLogger(__name__)

API_KEY_HEADER = APIKeyHeader(name="x-api-key", auto_error=False)

MAX_FILE_SIZE_MB = int(os.getenv("MAX_FILE_SIZE_MB", "10"))
MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024

ALLOWED_CSV_TYPES = {"text/csv", "application/csv", "text/plain", "application/vnd.ms-excel"}
ALLOWED_PDF_TYPES = {"application/pdf"}

INJECTION_PATTERNS = [
    "ignore previous",
    "ignore all",
    "you are now",
    "new instructions",
    "system prompt",
    "disregard",
    "forget everything",
    "act as",
    "jailbreak",
]


def verify_api_key(api_key: str = Security(API_KEY_HEADER)) -> str:
    expected = os.getenv("API_SECRET_KEY")
    if not expected:
        raise HTTPException(status_code=500, detail="API key not configured")
    if not api_key or api_key != expected:
        raise HTTPException(status_code=401, detail="Invalid or missing API key")
    return api_key


ALLOWED_DATA_EXTENSIONS = {"csv", "txt"}


async def validate_file_type(file: UploadFile, allowed_types: set[str], file_label: str) -> None:
    content_type = file.content_type or ""
    extension = (file.filename or "").lower().rsplit(".", 1)[-1]

    if file_label == "data" and extension not in ALLOWED_DATA_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Data file must be a CSV or TXT (.csv, .txt) — got .{extension}",
        )
    if file_label == "pdf" and extension != "pdf":
        raise HTTPException(status_code=400, detail="Docs file must be a PDF (.pdf)")

    if content_type and content_type not in allowed_types and "octet-stream" not in content_type:
        logger.warning("Unexpected content-type %s for %s", content_type, file_label)


async def validate_file_size(file: UploadFile, content: bytes, file_label: str) -> None:
    if len(content) > MAX_FILE_SIZE_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"{file_label} file exceeds {MAX_FILE_SIZE_MB}MB limit",
        )


def scan_for_injection(content: str) -> tuple[bool, list[str]]:
    """Return (has_injection, suspicious_lines)."""
    lower = content.lower()
    for pattern in INJECTION_PATTERNS:
        if pattern in lower:
            suspicious = [
                line for line in content.splitlines()
                if pattern in line.lower()
            ]
            return True, suspicious
    return False, []


def sanitize_content(content: str) -> tuple[str, list[str]]:
    """Remove lines containing injection patterns. Returns (clean_content, removed_lines)."""
    removed: list[str] = []
    clean_lines: list[str] = []
    lower_content = content.lower()

    for line in content.splitlines():
        line_lower = line.lower()
        if any(pat in line_lower for pat in INJECTION_PATTERNS):
            removed.append(line)
            logger.warning("Removed suspicious line: %r", line)
        else:
            clean_lines.append(line)

    return "\n".join(clean_lines), removed
