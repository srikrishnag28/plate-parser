import pytest
from app.validator import validate_output
from tests.conftest import SAMPLE_OUTPUT_JSON
import copy


def test_valid_output_passes():
    valid, err = validate_output(SAMPLE_OUTPUT_JSON)
    assert valid is True
    assert err == ""


def test_missing_instrument_fails():
    data = copy.deepcopy(SAMPLE_OUTPUT_JSON)
    del data["plate_reader_document"]["instrument"]
    valid, err = validate_output(data)
    assert valid is False
    assert "instrument" in err


def test_missing_wells_fails():
    data = copy.deepcopy(SAMPLE_OUTPUT_JSON)
    del data["plate_reader_document"]["wells"]
    valid, err = validate_output(data)
    assert valid is False
    assert "wells" in err


def test_invalid_read_type_fails():
    data = copy.deepcopy(SAMPLE_OUTPUT_JSON)
    data["plate_reader_document"]["experiment"]["read_type"] = "continuous"
    valid, err = validate_output(data)
    assert valid is False


def test_invalid_detection_method_fails():
    data = copy.deepcopy(SAMPLE_OUTPUT_JSON)
    data["plate_reader_document"]["experiment"]["detection_method"] = "xray"
    valid, err = validate_output(data)
    assert valid is False


def test_invalid_plate_format_fails():
    data = copy.deepcopy(SAMPLE_OUTPUT_JSON)
    data["plate_reader_document"]["experiment"]["plate_format"] = "24-well"
    valid, err = validate_output(data)
    assert valid is False


def test_invalid_well_role_fails():
    data = copy.deepcopy(SAMPLE_OUTPUT_JSON)
    data["plate_reader_document"]["wells"][0]["well_role"] = "standard"
    valid, err = validate_output(data)
    assert valid is False


def test_missing_manufacturer_fails():
    data = copy.deepcopy(SAMPLE_OUTPUT_JSON)
    del data["plate_reader_document"]["instrument"]["manufacturer"]
    valid, err = validate_output(data)
    assert valid is False


def test_missing_measurement_wavelength_fails():
    data = copy.deepcopy(SAMPLE_OUTPUT_JSON)
    del data["plate_reader_document"]["measurement_settings"]["measurement_wavelength_nm"]
    valid, err = validate_output(data)
    assert valid is False


def test_null_optional_fields_pass():
    data = copy.deepcopy(SAMPLE_OUTPUT_JSON)
    data["plate_reader_document"]["instrument"]["serial_number"] = None
    data["plate_reader_document"]["experiment"]["temperature_celsius"] = None
    data["plate_reader_document"]["measurement_settings"]["reference_wavelength_nm"] = None
    valid, err = validate_output(data)
    assert valid is True


def test_not_a_dict_fails():
    valid, err = validate_output(["not", "a", "dict"])
    assert valid is False


def test_empty_dict_fails():
    valid, err = validate_output({})
    assert valid is False
