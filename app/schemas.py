from pydantic import BaseModel
from typing import Optional, List


class UploadResponse(BaseModel):
    job_id: str
    status: str
    sample_json: Optional[dict] = None
    parser_code: Optional[str] = None
    message: str


class ApproveResponse(BaseModel):
    parser_id: str
    job_id: str
    message: str


class FeedbackRequest(BaseModel):
    feedback: str


class FeedbackResponse(BaseModel):
    job_id: str
    status: str
    sample_json: Optional[dict] = None
    parser_code: Optional[str] = None
    message: str


class RunResponse(BaseModel):
    run_id: str
    parser_id: str
    output_json: Optional[dict] = None
    status: str
    message: str


class ParserInfo(BaseModel):
    id: str
    name: str
    instrument: str
    version: int
    is_active: bool
    created_at: str


class JobStatus(BaseModel):
    job_id: str
    status: str
    sample_json: Optional[dict] = None
    error_message: Optional[str] = None
    created_at: str


class HealthResponse(BaseModel):
    status: str
