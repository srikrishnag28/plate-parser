import os
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from starlette.requests import Request
from dotenv import load_dotenv

load_dotenv()

from .schemas import (
    UploadResponse, ApproveResponse, FeedbackRequest, FeedbackResponse,
    RunResponse, ParserInfo, JobStatus, HealthResponse,
)
from .security import (
    verify_api_key, validate_file_type, validate_file_size,
    scan_for_injection, sanitize_content,
    ALLOWED_CSV_TYPES, ALLOWED_PDF_TYPES,
)
from .storage import upload_file, upload_json
from .database import (
    create_job, update_job, get_job,
    save_parser, get_parser, list_parsers, create_run,
)
from .agent import generate_parser, refine_parser
from .sandbox import run_parser_in_sandbox
from .validator import validate_output

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

limiter = Limiter(key_func=get_remote_address)

app = FastAPI(title="plate-parser", version="1.0.0")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

RATE_LIMIT = os.getenv("RATE_LIMIT_PER_HOUR", "10")


# ── Health ─────────────────────────────────────────────────────────────────────

@app.get("/health", response_model=HealthResponse)
async def health():
    return {"status": "ok"}


# ── Upload ─────────────────────────────────────────────────────────────────────

@app.post("/upload", response_model=UploadResponse)
@limiter.limit(f"{RATE_LIMIT}/hour")
async def upload(
    request: Request,
    csv_file: UploadFile = File(...),
    pdf_file: UploadFile = File(...),
    api_key: str = Depends(verify_api_key),
):
    # Validate file types
    await validate_file_type(csv_file, ALLOWED_CSV_TYPES, "csv")
    await validate_file_type(pdf_file, ALLOWED_PDF_TYPES, "pdf")

    csv_bytes = await csv_file.read()
    pdf_bytes = await pdf_file.read()

    # Validate file sizes
    await validate_file_size(csv_file, csv_bytes, "csv")
    await validate_file_size(pdf_file, pdf_bytes, "pdf")

    csv_content = csv_bytes.decode("utf-8", errors="replace")

    # Injection scan
    has_injection, suspicious = scan_for_injection(csv_content)
    if has_injection:
        logger.warning("Injection patterns found in upload, sanitizing")
        csv_content, removed = sanitize_content(csv_content)
        if not csv_content.strip():
            raise HTTPException(status_code=400, detail="File rejected: contains prompt injection patterns")

    # Upload to Supabase storage
    csv_url = await upload_file("uploads", csv_bytes, csv_file.filename or "input.csv", "text/csv")
    pdf_url = await upload_file("uploads", pdf_bytes, pdf_file.filename or "docs.pdf", "application/pdf")

    job_id = await create_job(csv_url, pdf_url)

    try:
        parser_code, sample_json = generate_parser(csv_content, pdf_bytes)
        await update_job(job_id, status="pending_review", sample_json=sample_json, parser_code_temp=parser_code)
    except Exception as e:
        await update_job(job_id, status="failed", error_message=str(e))
        raise HTTPException(status_code=500, detail=f"Agent failed: {e}")

    # Store parser_code temporarily in job record for later approval
    await update_job(job_id, parser_code_temp=parser_code)

    return UploadResponse(
        job_id=job_id,
        status="pending_review",
        sample_json=sample_json,
        message="Parser generated. Review the sample JSON and approve or provide feedback.",
    )


# ── Approve ────────────────────────────────────────────────────────────────────

@app.post("/approve/{job_id}", response_model=ApproveResponse)
async def approve(job_id: str, api_key: str = Depends(verify_api_key)):
    job = await get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job["status"] != "pending_review":
        raise HTTPException(status_code=400, detail=f"Job is in status '{job['status']}', must be 'pending_review'")

    parser_code = job.get("parser_code_temp")
    if not parser_code:
        raise HTTPException(status_code=400, detail="No parser code found for this job")

    sample_json = job.get("sample_json", {})
    instrument = ""
    try:
        instrument = sample_json["plate_reader_document"]["instrument"]["model"]
    except (KeyError, TypeError):
        instrument = "unknown"

    parser_id = await save_parser(
        name=f"Parser for {instrument}",
        instrument=instrument,
        parser_code=parser_code,
        job_id=job_id,
    )
    await update_job(job_id, status="approved")

    return ApproveResponse(
        parser_id=parser_id,
        job_id=job_id,
        message="Parser approved and saved successfully.",
    )


# ── Feedback ───────────────────────────────────────────────────────────────────

@app.post("/feedback/{job_id}", response_model=FeedbackResponse)
@limiter.limit(f"{RATE_LIMIT}/hour")
async def feedback(
    request: Request,
    job_id: str,
    body: FeedbackRequest,
    api_key: str = Depends(verify_api_key),
):
    job = await get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job["status"] not in ("pending_review", "failed"):
        raise HTTPException(status_code=400, detail="Job is not awaiting feedback")

    parser_code = job.get("parser_code_temp", "")

    # Fetch original CSV and PDF
    from .storage import get_client
    import httpx

    async with httpx.AsyncClient() as client:
        csv_resp = await client.get(job["input_file_url"])
        pdf_resp = await client.get(job["docs_url"])

    csv_content = csv_resp.text
    pdf_bytes = pdf_resp.content

    # Injection scan on feedback itself
    has_injection, _ = scan_for_injection(body.feedback)
    if has_injection:
        raise HTTPException(status_code=400, detail="Feedback contains injection patterns")

    try:
        new_code, new_json = refine_parser(parser_code, csv_content, pdf_bytes, body.feedback)
    except Exception as e:
        await update_job(job_id, status="failed", error_message=str(e))
        raise HTTPException(status_code=500, detail=f"Refinement failed: {e}")

    await update_job(job_id, status="pending_review", sample_json=new_json, parser_code_temp=new_code)

    return FeedbackResponse(
        job_id=job_id,
        status="pending_review",
        sample_json=new_json,
        message="Parser refined. Review updated JSON and approve or give more feedback.",
    )


# ── Run ────────────────────────────────────────────────────────────────────────

@app.post("/run/{parser_id}", response_model=RunResponse)
@limiter.limit(f"{RATE_LIMIT}/hour")
async def run_parser(
    request: Request,
    parser_id: str,
    csv_file: UploadFile = File(...),
    api_key: str = Depends(verify_api_key),
):
    parser = await get_parser(parser_id)
    if not parser:
        raise HTTPException(status_code=404, detail="Parser not found")
    if not parser["is_active"]:
        raise HTTPException(status_code=400, detail="Parser is inactive")

    await validate_file_type(csv_file, ALLOWED_CSV_TYPES, "csv")
    csv_bytes = await csv_file.read()
    await validate_file_size(csv_file, csv_bytes, "csv")

    csv_content = csv_bytes.decode("utf-8", errors="replace")
    has_injection, _ = scan_for_injection(csv_content)
    if has_injection:
        csv_content, _ = sanitize_content(csv_content)

    try:
        output_json = run_parser_in_sandbox(parser["parser_code"], csv_content)
    except Exception as e:
        run_id = await create_run(parser_id, "", "failed")
        raise HTTPException(status_code=500, detail=f"Parser run failed: {e}")

    valid, error = validate_output(output_json)
    if not valid:
        run_id = await create_run(parser_id, "", "failed")
        raise HTTPException(status_code=500, detail=f"Output validation failed: {error}")

    output_url = await upload_json("outputs", output_json, f"run_{parser_id}.json")
    run_id = await create_run(parser_id, output_url, "success")

    return RunResponse(
        run_id=run_id,
        parser_id=parser_id,
        output_json=output_json,
        status="success",
        message="Parser ran successfully.",
    )


# ── List parsers ───────────────────────────────────────────────────────────────

@app.get("/parsers", response_model=list[ParserInfo])
async def get_parsers(api_key: str = Depends(verify_api_key)):
    parsers = await list_parsers()
    return [
        ParserInfo(
            id=p["id"],
            name=p["name"],
            instrument=p["instrument"],
            version=p["version"],
            is_active=p["is_active"],
            created_at=str(p["created_at"]),
        )
        for p in parsers
    ]


# ── Job status ─────────────────────────────────────────────────────────────────

@app.get("/jobs/{job_id}", response_model=JobStatus)
async def get_job_status(job_id: str, api_key: str = Depends(verify_api_key)):
    job = await get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return JobStatus(
        job_id=job["id"],
        status=job["status"],
        sample_json=job.get("sample_json"),
        error_message=job.get("error_message"),
        created_at=str(job["created_at"]),
    )
