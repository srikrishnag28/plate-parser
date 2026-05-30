import jsonschema
import logging
from typing import Any

logger = logging.getLogger(__name__)

# anyOf helper: allows the value to be null OR match the given schema
def _nullable(schema: dict) -> dict:
    return {"anyOf": [schema, {"type": "null"}]}


PLATE_READER_SCHEMA = {
    "type": "object",
    "required": ["plate_reader_document"],
    "properties": {
        "plate_reader_document": {
            "type": "object",
            "required": ["instrument", "experiment", "measurement_settings", "wells"],
            "properties": {
                "instrument": {
                    "type": "object",
                    "required": ["manufacturer", "model"],
                    "properties": {
                        "manufacturer": {"type": ["string", "null"]},
                        "model":         {"type": ["string", "null"]},
                        "serial_number": {"type": ["string", "null"]},
                        "software":      {"type": ["string", "null"]},
                    },
                },
                "experiment": {
                    "type": "object",
                    "required": ["read_date", "read_time", "read_type", "detection_method", "plate_format"],
                    "properties": {
                        "id":         {"type": ["string", "null"]},
                        "read_date":  {"type": ["string", "null"]},
                        "read_time":  {"type": ["string", "null"]},
                        "read_type":  _nullable({"type": "string", "enum": ["endpoint", "kinetic"]}),
                        "detection_method": _nullable({
                            "type": "string",
                            "enum": ["absorbance", "fluorescence", "luminescence"],
                        }),
                        "plate_format": _nullable({
                            "type": "string",
                            "enum": ["96-well", "384-well", "1536-well"],
                        }),
                        "temperature_celsius": {"type": ["number", "null"]},
                    },
                },
                "measurement_settings": {
                    "type": "object",
                    "required": ["measurement_wavelength_nm"],
                    "properties": {
                        "measurement_wavelength_nm": {"type": ["number", "null"]},
                        "reference_wavelength_nm":   {"type": ["number", "null"]},
                        "excitation_wavelength_nm":  {"type": ["number", "null"]},
                        "emission_wavelength_nm":    {"type": ["number", "null"]},
                    },
                },
                "wells": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "required": ["well_position", "row", "column", "raw_value", "unit", "well_role"],
                        "properties": {
                            "well_position": {"type": "string"},
                            "row":           {"type": "string"},
                            "column":        {"type": "number"},
                            "raw_value":     {"type": "number"},
                            "unit":          {"type": "string"},
                            "sample_id":     {"type": ["string", "null"]},
                            "well_role": _nullable({
                                "type": "string",
                                "enum": ["sample", "blank", "control", "unknown"],
                            }),
                            "blank_corrected_value": {"type": ["number", "null"]},
                            "timepoints":            {"type": ["array", "null"]},
                        },
                    },
                },
            },
        }
    },
}


def validate_output(data: Any) -> tuple[bool, str]:
    """Validate parsed output against the plate reader schema. Returns (valid, error_message)."""
    try:
        jsonschema.validate(instance=data, schema=PLATE_READER_SCHEMA)
        return True, ""
    except jsonschema.ValidationError as e:
        msg = f"Schema validation failed: {e.message} at {list(e.absolute_path)}"
        logger.error(msg)
        return False, msg
    except jsonschema.SchemaError as e:
        msg = f"Internal schema error: {e.message}"
        logger.error(msg)
        return False, msg
