import os
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi.testclient import TestClient

os.environ.setdefault("API_SECRET_KEY", "test-secret-key")
os.environ.setdefault("GEMINI_API_KEY", "test-gemini-key")
os.environ.setdefault("SUPABASE_URL", "https://test.supabase.co")
os.environ.setdefault("SUPABASE_KEY", "test-supabase-key")
os.environ.setdefault("MAX_FILE_SIZE_MB", "10")
os.environ.setdefault("RATE_LIMIT_PER_HOUR", "100")

VALID_API_KEY = "test-secret-key"
HEADERS = {"x-api-key": VALID_API_KEY}

SAMPLE_OUTPUT_JSON = {
    "plate_reader_document": {
        "instrument": {
            "manufacturer": "BioTek",
            "model": "Synergy H1",
            "serial_number": "SN123456",
            "software": "Gen5 3.11",
        },
        "experiment": {
            "id": "DEMO-001",
            "read_date": "2024-01-15",
            "read_time": "10:30:00",
            "read_type": "endpoint",
            "detection_method": "absorbance",
            "plate_format": "96-well",
            "temperature_celsius": None,
        },
        "measurement_settings": {
            "measurement_wavelength_nm": 450.0,
            "reference_wavelength_nm": 620.0,
            "excitation_wavelength_nm": None,
            "emission_wavelength_nm": None,
        },
        "wells": [
            {
                "well_position": "A1",
                "row": "A",
                "column": 1,
                "raw_value": 0.052,
                "unit": "OD",
                "sample_id": "BLANK",
                "well_role": "blank",
                "blank_corrected_value": None,
                "timepoints": None,
            },
        ],
    }
}


@pytest.fixture
def client():
    with patch("app.storage.get_client"), \
         patch("app.database.get_client"):
        from app.main import app
        return TestClient(app)
