import json
import os
import sys
import textwrap
import pytest
from app.sandbox import run_parser_in_sandbox
from app.validator import validate_output
from tests.conftest import SAMPLE_OUTPUT_JSON


BIOTEK_PARSER_CODE = textwrap.dedent("""
import csv, json, sys, re

def parse(csv_path):
    with open(csv_path, newline='', encoding='utf-8') as f:
        lines = f.readlines()

    instrument = {"manufacturer": "BioTek", "model": "Synergy H1",
                  "serial_number": "SN123456", "software": "Gen5 3.11"}
    experiment = {
        "id": "DEMO-001", "read_date": "2024-01-15", "read_time": "10:30:00",
        "read_type": "endpoint", "detection_method": "absorbance",
        "plate_format": "96-well", "temperature_celsius": None,
    }
    measurement_settings = {
        "measurement_wavelength_nm": 450.0, "reference_wavelength_nm": 620.0,
        "excitation_wavelength_nm": None, "emission_wavelength_nm": None,
    }

    wells = []
    in_results = False
    for line in lines:
        line = line.strip()
        if line.startswith("Results"):
            in_results = True
            continue
        if not in_results:
            continue
        if line.startswith("Well,"):
            continue
        if not line:
            continue
        parts = [p.strip() for p in line.split(",")]
        if len(parts) < 3:
            continue
        pos = parts[0]
        sample_id = parts[1] if parts[1] else None
        try:
            raw_val = float(parts[2])
        except ValueError:
            continue

        row = pos[0]
        col = int(pos[1:])
        role = "blank" if (sample_id or "").upper().startswith("BLANK") else \
               "control" if (sample_id or "").upper().startswith("CTRL") else "sample"

        wells.append({
            "well_position": pos, "row": row, "column": col,
            "raw_value": raw_val, "unit": "OD",
            "sample_id": sample_id, "well_role": role,
            "blank_corrected_value": None, "timepoints": None,
        })

    return {
        "plate_reader_document": {
            "instrument": instrument, "experiment": experiment,
            "measurement_settings": measurement_settings, "wells": wells,
        }
    }

if __name__ == "__main__":
    print(json.dumps(parse(sys.argv[1])))
""").strip()


BIOTEK_CSV_PATH = os.path.join(os.path.dirname(__file__), "..", "samples", "biotek_sample.csv")


def _read_biotek_csv():
    with open(BIOTEK_CSV_PATH, encoding="utf-8") as f:
        return f.read()


def test_biotek_parser_produces_valid_json():
    csv_content = _read_biotek_csv()
    result = run_parser_in_sandbox(BIOTEK_PARSER_CODE, csv_content)
    valid, err = validate_output(result)
    assert valid is True, f"Validation error: {err}"


def test_biotek_parser_has_correct_structure():
    csv_content = _read_biotek_csv()
    result = run_parser_in_sandbox(BIOTEK_PARSER_CODE, csv_content)
    doc = result["plate_reader_document"]

    assert doc["instrument"]["manufacturer"] == "BioTek"
    assert doc["instrument"]["model"] == "Synergy H1"
    assert doc["experiment"]["read_type"] == "endpoint"
    assert doc["experiment"]["detection_method"] == "absorbance"
    assert doc["experiment"]["plate_format"] == "96-well"
    assert doc["measurement_settings"]["measurement_wavelength_nm"] == 450.0
    assert len(doc["wells"]) > 0


def test_parser_is_deterministic():
    """Running the same parser twice produces identical output."""
    csv_content = _read_biotek_csv()
    result1 = run_parser_in_sandbox(BIOTEK_PARSER_CODE, csv_content)
    result2 = run_parser_in_sandbox(BIOTEK_PARSER_CODE, csv_content)
    assert result1 == result2


def test_broken_parser_fails_gracefully():
    broken_code = "import sys\nraise RuntimeError('parser exploded')"
    with pytest.raises(RuntimeError, match="Parser failed"):
        run_parser_in_sandbox(broken_code, "well,value\nA1,0.5\n")


def test_parser_with_no_output_fails_gracefully():
    silent_code = "import sys\n# does nothing"
    with pytest.raises(RuntimeError, match="no output"):
        run_parser_in_sandbox(silent_code, "well,value\nA1,0.5\n")


def test_parser_with_invalid_json_fails_gracefully():
    bad_json_code = "import sys\nprint('not json at all')"
    with pytest.raises(RuntimeError, match="not valid JSON"):
        run_parser_in_sandbox(bad_json_code, "well,value\nA1,0.5\n")


def test_well_roles_assigned_correctly():
    csv_content = _read_biotek_csv()
    result = run_parser_in_sandbox(BIOTEK_PARSER_CODE, csv_content)
    wells = result["plate_reader_document"]["wells"]
    roles = {w["well_position"]: w["well_role"] for w in wells}

    assert roles.get("A1") == "blank"
    assert roles.get("A2") == "control"
    assert roles.get("A3") == "sample"
