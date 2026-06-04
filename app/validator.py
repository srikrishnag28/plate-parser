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
                            "concentration":         {"type": ["string", "null"]},
                            "timepoints":            {"type": ["array", "null"]},
                        },
                    },
                },
            },
        }
    },
}


# Plate-format dimensions: format -> (rows, columns)
PLATE_DIMENSIONS = {
    "96-well":   (8, 12),
    "384-well":  (16, 24),
    "1536-well": (32, 48),
}


def _row_labels(n: int) -> list[str]:
    """Excel-style row labels: A..Z, AA, AB, ... — enough for any plate format."""
    labels = []
    for i in range(n):
        s, x = "", i + 1
        while x > 0:
            x, r = divmod(x - 1, 26)
            s = chr(65 + r) + s
        labels.append(s)
    return labels


def _check_plate_consistency(data: Any) -> str:
    """Semantic guardrail: wells must be consistent with the declared plate_format."""
    doc = data.get("plate_reader_document", {})
    plate_format = (doc.get("experiment") or {}).get("plate_format")
    wells = doc.get("wells") or []
    dims = PLATE_DIMENSIONS.get(plate_format)
    if not dims:
        return ""  # unknown/null format — nothing to enforce

    rows, cols = dims
    capacity = rows * cols
    if len(wells) > capacity:
        return f"{len(wells)} wells exceed {plate_format} capacity ({capacity})"

    allowed_rows = set(_row_labels(rows))
    for w in wells:
        r, c = w.get("row"), w.get("column")
        if r not in allowed_rows:
            return f"well row '{r}' is outside {plate_format} range (A-{_row_labels(rows)[-1]})"
        if not isinstance(c, (int, float)) or not (1 <= c <= cols):
            return f"well column '{c}' is outside {plate_format} range (1-{cols})"
    return ""


def validate_output(data: Any) -> tuple[bool, str]:
    """Validate parsed output against the plate reader schema. Returns (valid, error_message)."""
    try:
        jsonschema.validate(instance=data, schema=PLATE_READER_SCHEMA)
    except jsonschema.ValidationError as e:
        msg = f"Schema validation failed: {e.message} at {list(e.absolute_path)}"
        logger.error(msg)
        return False, msg
    except jsonschema.SchemaError as e:
        msg = f"Internal schema error: {e.message}"
        logger.error(msg)
        return False, msg

    consistency_error = _check_plate_consistency(data)
    if consistency_error:
        msg = f"Plate consistency check failed: {consistency_error}"
        logger.error(msg)
        return False, msg
    return True, ""
