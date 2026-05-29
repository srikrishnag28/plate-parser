# plate-parser

AI-powered lab plate reader file parser. Upload a CSV from your plate reader instrument alongside its PDF documentation — an AI agent (Google Gemini) reads both and generates a deterministic Python parser. Once you approve the parser, future files from the same instrument run instantly without any AI.

## How it works

```
Upload CSV + PDF → Gemini generates parser → Run in sandbox → Human reviews JSON
        ↓ approve                                ↓ feedback
Save parser to DB                         Gemini refines parser
        ↓
Future files: run saved parser (no AI, deterministic)
```

## Quick start

```bash
# 1. Clone and install
git clone <repo>
cd plate-parser
pip install -r requirements.txt

# 2. Configure
cp .env.example .env
# Edit .env with your keys

# 3. Set up Supabase tables
# Paste supabase_setup.sql into your Supabase SQL editor

# 4. Run
uvicorn app.main:app --reload
```

## Environment variables

| Variable | Description |
|---|---|
| `GEMINI_API_KEY` | Google Gemini API key |
| `SUPABASE_URL` | Your Supabase project URL |
| `SUPABASE_KEY` | Supabase service role key |
| `API_SECRET_KEY` | Secret for x-api-key header auth |
| `MAX_FILE_SIZE_MB` | Max upload size (default 10) |
| `RATE_LIMIT_PER_HOUR` | Uploads per hour per IP (default 10) |

## API endpoints

All endpoints (except `/health`) require the `x-api-key` header.

### `POST /upload`
Upload a CSV + PDF pair. Triggers Gemini to generate a parser.

**Form data:** `csv_file` (CSV), `pdf_file` (PDF)

**Response:**
```json
{
  "job_id": "uuid",
  "status": "pending_review",
  "sample_json": { ... },
  "message": "Parser generated. Review the sample JSON and approve or provide feedback."
}
```

### `POST /approve/{job_id}`
Approve the generated parser and save it for future use.

**Response:**
```json
{
  "parser_id": "uuid",
  "job_id": "uuid",
  "message": "Parser approved and saved successfully."
}
```

### `POST /feedback/{job_id}`
Send feedback to refine the parser. Gemini will revise and return new JSON.

**Body:** `{"feedback": "The wavelength is wrong, it should be 490nm not 450nm"}`

**Response:** Same as `/upload` response.

### `POST /run/{parser_id}`
Run a saved parser on a new CSV file. No AI involved — fully deterministic.

**Form data:** `csv_file` (CSV)

**Response:**
```json
{
  "run_id": "uuid",
  "parser_id": "uuid",
  "output_json": { ... },
  "status": "success",
  "message": "Parser ran successfully."
}
```

### `GET /parsers`
List all approved parsers.

### `GET /jobs/{job_id}`
Get job status and result.

### `GET /health`
Health check. Returns `{"status": "ok"}`.

## Output JSON schema

Every parser produces this structure:

```json
{
  "plate_reader_document": {
    "instrument": {
      "manufacturer": "BioTek",
      "model": "Synergy H1",
      "serial_number": "SN123456",
      "software": "Gen5 3.11"
    },
    "experiment": {
      "id": "DEMO-001",
      "read_date": "2024-01-15",
      "read_time": "10:30:00",
      "read_type": "endpoint",
      "detection_method": "absorbance",
      "plate_format": "96-well",
      "temperature_celsius": null
    },
    "measurement_settings": {
      "measurement_wavelength_nm": 450.0,
      "reference_wavelength_nm": 620.0,
      "excitation_wavelength_nm": null,
      "emission_wavelength_nm": null
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
        "blank_corrected_value": null,
        "timepoints": null
      }
    ]
  }
}
```

## Safety layers

Every request passes through 10 safety layers in order:

1. API key authentication via `x-api-key` header
2. Rate limiting (10 uploads/hour per IP via slowapi)
3. File type validation (CSV and PDF only)
4. File size validation (10MB max per file)
5. Prompt injection scan (blocks patterns like "ignore previous", "act as", "jailbreak")
6. Content sanitization (removes suspicious lines, logs them)
7. Gemini called with strict system prompt; file content wrapped in `<raw_data>` tags
8. Gemini output validated against exact JSON schema
9. Generated parser run in subprocess sandbox (no network, minimal environment)
10. Sandbox output re-validated before returning to caller

## Running tests

```bash
pytest tests/ -v
```

## Docker

```bash
docker build -t plate-parser .
docker run -p 8000:8000 --env-file .env plate-parser
```

## Supabase storage buckets

Create two buckets in your Supabase dashboard:
- `uploads` — stores uploaded CSV and PDF files
- `outputs` — stores generated JSON results
