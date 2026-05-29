from pydantic import BaseModel, Field
from typing import Optional, List, Union
from enum import Enum


class ReadType(str, Enum):
    endpoint = "endpoint"
    kinetic = "kinetic"


class DetectionMethod(str, Enum):
    absorbance = "absorbance"
    fluorescence = "fluorescence"
    luminescence = "luminescence"


class PlateFormat(str, Enum):
    well_96 = "96-well"
    well_384 = "384-well"
    well_1536 = "1536-well"


class WellRole(str, Enum):
    sample = "sample"
    blank = "blank"
    control = "control"
    unknown = "unknown"


class Instrument(BaseModel):
    manufacturer: str
    model: str
    serial_number: Optional[str] = None
    software: Optional[str] = None


class Experiment(BaseModel):
    id: Optional[str] = None
    read_date: str
    read_time: str
    read_type: ReadType
    detection_method: DetectionMethod
    plate_format: PlateFormat
    temperature_celsius: Optional[float] = None


class MeasurementSettings(BaseModel):
    measurement_wavelength_nm: float
    reference_wavelength_nm: Optional[float] = None
    excitation_wavelength_nm: Optional[float] = None
    emission_wavelength_nm: Optional[float] = None


class Well(BaseModel):
    well_position: str
    row: str
    column: int
    raw_value: float
    unit: str
    sample_id: Optional[str] = None
    well_role: WellRole
    blank_corrected_value: Optional[float] = None
    timepoints: Optional[List] = None


class PlateReaderDocument(BaseModel):
    instrument: Instrument
    experiment: Experiment
    measurement_settings: MeasurementSettings
    wells: List[Well]


class PlateReaderOutput(BaseModel):
    plate_reader_document: PlateReaderDocument


# API request/response schemas

class UploadResponse(BaseModel):
    job_id: str
    status: str
    sample_json: Optional[dict] = None
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
