import os
import logging
from fastapi import HTTPException, UploadFile

logger = logging.getLogger(__name__)

MAX_FILE_SIZE_MB = int(os.getenv("MAX_FILE_SIZE_MB", "25"))
MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024

ALLOWED_CSV_TYPES = {"text/csv", "application/csv", "text/plain", "application/vnd.ms-excel"}
ALLOWED_PDF_TYPES = {"application/pdf"}
ALLOWED_DATA_EXTENSIONS = {"csv", "txt"}


async def validate_file_type(file: UploadFile, allowed_types: set[str], file_label: str) -> None:
    extension = (file.filename or "").lower().rsplit(".", 1)[-1]
    content_type = file.content_type or ""

    if file_label == "data" and extension not in ALLOWED_DATA_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Data file must be CSV or TXT — got .{extension}",
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
