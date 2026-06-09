import os
import json
import logging
import traceback
from pathlib import Path
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from dotenv import load_dotenv

load_dotenv()

from .schemas import (
    UploadResponse, ApproveResponse, FeedbackRequest, FeedbackResponse,
    RunResponse, ParserInfo, JobStatus, HealthResponse,
)
from .security import (
    validate_file_type, validate_file_size,
    ALLOWED_CSV_TYPES, ALLOWED_PDF_TYPES,
)
from .storage import upload_file, upload_json, clear_storage
from .database import (
    create_job, update_job, get_job,
    save_parser, get_parser, list_parsers, create_run, clear_database,
)
from .agent import generate_parser, refine_parser
from .sandbox import run_parser_in_sandbox
from .validator import validate_output
from .pipeline import run_pipeline

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="plate-parser", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

_UI_PATH = Path(__file__).parent.parent / "templates" / "index.html"


@app.get("/", include_in_schema=False)
async def ui():
    return FileResponse(_UI_PATH)


@app.get("/health", response_model=HealthResponse)
async def health():
    return {"status": "ok"}


@app.post("/parse")
async def parse(
    file: UploadFile = File(...),
    docs: UploadFile = File(None),
):
    """
    Research-first autonomous pipeline. Streams SSE events for each stage.
    docs (PDF) is optional — the agent will web-search for instrument docs if omitted.
    Final SSE event carries output_json and parser_id.
    """
    await validate_file_type(file, ALLOWED_CSV_TYPES, "data")
    csv_bytes = await file.read()
    await validate_file_size(file, csv_bytes, "data")
    csv_content = csv_bytes.decode("utf-8", errors="replace")

    pdf_bytes: bytes | None = None
    if docs and docs.filename:
        await validate_file_type(docs, ALLOWED_PDF_TYPES, "pdf")
        pdf_bytes = await docs.read()
        await validate_file_size(docs, pdf_bytes, "docs")

    async def event_stream():
        try:
            async for event in run_pipeline(csv_content, pdf_bytes, file.filename or "input.csv"):
                yield f"data: {json.dumps(event)}\n\n"
        except Exception as e:
            logger.error("Pipeline error: %s", traceback.format_exc())
            yield f"data: {json.dumps({'stage': 'error', 'status': 'error', 'error': str(e)})}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.post("/upload", response_model=UploadResponse)
async def upload(
    file: UploadFile = File(...),
    docs: UploadFile = File(...),
):
    await validate_file_type(file, ALLOWED_CSV_TYPES, "data")
    await validate_file_type(docs, ALLOWED_PDF_TYPES, "pdf")

    data_bytes = await file.read()
    pdf_bytes = await docs.read()

    await validate_file_size(file, data_bytes, "data")
    await validate_file_size(docs, pdf_bytes, "docs")

    csv_content = data_bytes.decode("utf-8", errors="replace")

    csv_url = await upload_file("uploads", data_bytes, file.filename or "input.txt", "text/csv")
    pdf_url = await upload_file("uploads", pdf_bytes, docs.filename or "docs.pdf", "application/pdf")

    job_id = await create_job(csv_url, pdf_url)

    try:
        parser_code, sample_json = generate_parser(csv_content, pdf_bytes)
        await update_job(job_id, status="pending_review", sample_json=sample_json, parser_code_temp=parser_code)
    except Exception as e:
        await update_job(job_id, status="failed", error_message=str(e))
        raise HTTPException(status_code=500, detail=f"Agent failed: {e}")

    return UploadResponse(
        job_id=job_id,
        status="pending_review",
        sample_json=sample_json,
        parser_code=parser_code,
        message="Parser generated. Review the sample JSON and approve or provide feedback.",
    )


@app.post("/approve/{job_id}", response_model=ApproveResponse)
async def approve(job_id: str):
    job = await get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job["status"] != "pending_review":
        raise HTTPException(status_code=400, detail=f"Job is in status '{job['status']}', must be 'pending_review'")

    parser_code = job.get("parser_code_temp")
    if not parser_code:
        raise HTTPException(status_code=400, detail="No parser code found for this job")

    sample_json = job.get("sample_json", {})
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


@app.post("/feedback/{job_id}", response_model=FeedbackResponse)
async def feedback(job_id: str, body: FeedbackRequest):
    job = await get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job["status"] not in ("pending_review", "failed"):
        raise HTTPException(status_code=400, detail="Job is not awaiting feedback")

    parser_code = job.get("parser_code_temp", "")

    import httpx

    async def _fetch(url: str) -> bytes:
        if url.startswith("local://"):
            return Path(url[len("local://"):]).read_bytes()
        async with httpx.AsyncClient() as hc:
            r = await hc.get(url)
            r.raise_for_status()
            return r.content

    csv_bytes_raw = await _fetch(job["input_file_url"])
    pdf_bytes = await _fetch(job["docs_url"])
    csv_content = csv_bytes_raw.decode("utf-8", errors="replace")

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
        parser_code=new_code,
        message="Parser refined. Review updated JSON and approve or give more feedback.",
    )


@app.post("/run/{parser_id}", response_model=RunResponse)
async def run_parser(parser_id: str, file: UploadFile = File(...)):
    try:
        parser = await get_parser(parser_id)
    except Exception as e:
        logger.error("DB error fetching parser %s:\n%s", parser_id, traceback.format_exc())
        raise HTTPException(status_code=503, detail=f"Database error: {e}")

    if not parser:
        raise HTTPException(status_code=404, detail=f"Parser '{parser_id}' not found")
    if not parser["is_active"]:
        raise HTTPException(status_code=400, detail="Parser is inactive")

    await validate_file_type(file, ALLOWED_CSV_TYPES, "data")
    csv_bytes = await file.read()
    await validate_file_size(file, csv_bytes, "data")

    csv_content = csv_bytes.decode("utf-8", errors="replace")

    try:
        output_json = run_parser_in_sandbox(parser["parser_code"], csv_content)
    except Exception as e:
        logger.error("Sandbox failed for parser %s:\n%s", parser_id, traceback.format_exc())
        try:
            await create_run(parser_id, "", "failed")
        except Exception:
            pass
        raise HTTPException(status_code=500, detail=f"Parser execution failed: {e}")

    valid, error = validate_output(output_json)
    if not valid:
        logger.error("Output validation failed for parser %s: %s", parser_id, error)
        try:
            await create_run(parser_id, "", "failed")
        except Exception:
            pass
        raise HTTPException(status_code=422, detail=f"Output validation failed: {error}")

    try:
        output_url = await upload_json("outputs", output_json, f"run_{parser_id}.json")
        run_id = await create_run(parser_id, output_url, "success")
    except Exception as e:
        logger.error("Failed to persist run result for parser %s:\n%s", parser_id, traceback.format_exc())
        raise HTTPException(status_code=503, detail=f"Storage/DB error saving result: {e}")

    return RunResponse(
        run_id=run_id,
        parser_id=parser_id,
        output_json=output_json,
        status="success",
        message="Parser ran successfully.",
    )


@app.get("/parsers", response_model=list[ParserInfo])
async def get_parsers():
    parsers = await list_parsers()
    return [
        ParserInfo(
            id=p["id"],
            name=p.get("name", ""),
            instrument=p.get("instrument", ""),
            version=p.get("version", 1),
            is_active=p.get("is_active", True),
            created_at=str(p.get("created_at", "")),
        )
        for p in parsers
    ]


@app.delete("/database")
async def clear_db():
    try:
        await clear_database()
        await clear_storage()
    except Exception as e:
        logger.error("Failed to clear database/storage:\n%s", traceback.format_exc())
        raise HTTPException(status_code=503, detail=f"Clear failed: {e}")
    return {"message": "Database and storage cleared."}


@app.get("/jobs/{job_id}", response_model=JobStatus)
async def get_job_status(job_id: str):
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
