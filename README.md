# plate-parser

AI-powered lab plate reader file parser. Upload a plate reader data file (CSV or TXT) alongside its PDF documentation — an AI agent (Gemini 2.0 Flash, with Groq/Llama fallback) reads both and generates a deterministic Python parser. Once you approve the parser, future files from the same instrument run instantly without any AI.

Includes a browser UI served at `/` — no separate frontend setup required.

## How it works

```
Upload file + PDF → AI generates parser → Run in sandbox → Human reviews JSON
       ↓ approve                               ↓ feedback
Save parser to DB                        AI refines parser (up to 3 retries)
       ↓
Future files: run saved parser (no AI, fully deterministic)
```

## AI backend

- **Primary:** Google Gemini `gemini-2.0-flash` — 1,500 req/day free, 1M tokens/min
- **Fallback:** Groq `llama-3.3-70b-versatile` — activates automatically if Gemini fails or is rate-limited

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Browser UI  (GET /)                   │
│          templates/index.html — vanilla JS + fetch()     │
└──────────────────────┬──────────────────────────────────┘
                       │ HTTP + x-api-key
┌──────────────────────▼──────────────────────────────────┐
│                  FastAPI  (app/main.py)                   │
│  Rate limiting · API key auth · File validation          │
│  Injection scan · Sanitization                           │
└────┬──────────┬──────────┬──────────────────────────────┘
     │          │          │
     ▼          ▼          ▼
┌─────────┐ ┌──────┐ ┌────────────────────────────────────┐
│Supabase │ │ DB   │ │         AI Agent  (app/agent.py)    │
│Storage  │ │Tables│ │  Primary:  Gemini gemini-2.0-flash  │
│uploads/ │ │jobs  │ │  Fallback: Groq llama-3.3-70b       │
│outputs/ │ │parser│ │  Auto-retry up to 3×  on failure    │
└─────────┘ │runs  │ └──────────────┬─────────────────────┘
            └──────┘                │ generated Python code
                       ┌────────────▼─────────────────────┐
                       │   Subprocess Sandbox (app/sandbox) │
                       │   30s timeout · no network · runs  │
                       │   parser.py against uploaded file  │
                       └────────────┬─────────────────────┘
                                    │ JSON output
                       ┌────────────▼─────────────────────┐
                       │  Schema Validator (app/validator)  │
                       │  jsonschema · plate_reader_document│
                       └──────────────────────────────────┘
```

**Key modules:**

| File | Responsibility |
|---|---|
| `app/main.py` | FastAPI routes, rate limiting, request lifecycle |
| `app/agent.py` | LLM calls (Gemini → Groq fallback), auto-retry loop |
| `app/sandbox.py` | Subprocess execution of generated parsers, 30s timeout |
| `app/validator.py` | JSON schema validation of parser output |
| `app/security.py` | API key check, file type/size, injection scan, sanitizer |
| `app/database.py` | Supabase DB — jobs, parsers, parser_runs tables |
| `app/storage.py` | Supabase Storage — uploads and outputs buckets |
| `app/schemas.py` | Pydantic request/response models |
| `templates/index.html` | Single-file browser UI |

## Quick start

```bash
# 1. Clone and install
git clone <repo>
cd plate-parser
pip install -r requirements.txt

# 2. Configure
cp .env.example .env
# Edit .env with your keys

# 3. Set up Supabase tables and storage buckets
# Paste supabase_setup.sql into your Supabase SQL editor
# Create two storage buckets: uploads, outputs

# 4. Run
uvicorn app.main:app --reload
```

## Environment variables

| Variable | Description |
|---|---|
| `GEMINI_API_KEY` | Google Gemini API key (get free key from [aistudio.google.com](https://aistudio.google.com)) |
| `GROQ_API_KEY` | Groq API key — fallback if Gemini fails (get free key from [console.groq.com](https://console.groq.com)) |
| `SUPABASE_URL` | Your Supabase project URL |
| `SUPABASE_KEY` | Supabase **service_role** key (not the publishable/anon key) |
| `API_SECRET_KEY` | Secret for `x-api-key` header auth |
| `MAX_FILE_SIZE_MB` | Max upload size per file (default 10) |
| `RATE_LIMIT_PER_HOUR` | Requests per hour per IP (default 10) |

## API endpoints

All endpoints (except `/health`) require the `x-api-key` header.

### `POST /upload`
Upload a plate reader data file + PDF documentation. The AI generates a parser and returns a sample JSON for review.

**Form data:** `file` (CSV or TXT), `docs` (PDF)

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
Approve the generated parser and save it for future deterministic use.

**Response:**
```json
{
  "parser_id": "uuid",
  "job_id": "uuid",
  "message": "Parser approved and saved successfully."
}
```

### `POST /feedback/{job_id}`
Send feedback to refine the parser. The AI revises it and returns updated JSON.

**Body:** `{"feedback": "The wavelength is wrong, it should be 490nm not 450nm"}`

**Response:** Same shape as `/upload` response.

### `POST /run/{parser_id}`
Run a saved parser on a new data file. No AI involved — fully deterministic.

**Form data:** `file` (CSV or TXT)

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

### `GET /`
Browser UI — upload files, review JSON, approve or give feedback, and run saved parsers. No API client needed.

## Output JSON schema

Every parser produces this structure:

```json
{
  "plate_reader_document": {
    "instrument": {
      "manufacturer": "BioTek",
      "model": "Synergy H1",
      "serial_number": null,
      "software": "Gen5 3.12"
    },
    "experiment": {
      "id": null,
      "read_date": "2024-01-15",
      "read_time": "10:30:00",
      "read_type": "endpoint",
      "detection_method": "absorbance",
      "plate_format": "96-well",
      "temperature_celsius": null
    },
    "measurement_settings": {
      "measurement_wavelength_nm": 630.0,
      "reference_wavelength_nm": null,
      "excitation_wavelength_nm": null,
      "emission_wavelength_nm": null
    },
    "wells": [
      {
        "well_position": "A1",
        "row": "A",
        "column": 1,
        "raw_value": 3.337,
        "unit": "OD",
        "sample_id": null,
        "well_role": "unknown",
        "blank_corrected_value": null,
        "timepoints": null
      }
    ]
  }
}
```

## Safety layers

Every request passes through these layers in order:

1. API key authentication via `x-api-key` header
2. Rate limiting (10 requests/hour per IP via slowapi)
3. File type validation — CSV, TXT, and PDF only
4. File size validation — 10MB max per file
5. Prompt injection scan — blocks patterns like "ignore previous", "act as", "jailbreak"
6. Content sanitization — removes suspicious lines and logs them
7. AI called with strict system prompt; file content wrapped in `<raw_data>` tags
8. AI output validated against exact JSON schema
9. Generated parser run in subprocess sandbox (no network, minimal environment, 30s timeout)
10. Sandbox output re-validated before returning to caller

## Sample files

Two real instrument exports are included in `samples/` for testing:

| File | Instrument | Detection | Format |
|---|---|---|---|
| `biotek_sample.txt` | BioTek Synergy (Gen5 3.12) | Absorbance 630 nm | Tab-delimited grid, rows A–H |
| `spectramax_sample.txt` | Molecular Devices SpectraMax M5 | Fluorescence Ex 485 / Em 535 nm | `##BLOCKS=` header, temperature column |

Matching documentation PDFs (`biotek_docs.pdf`, `spectramax_docs.pdf`) are included for the `/upload` `docs` field.

## Running tests

```bash
pytest tests/ -v
```

41 tests covering upload validation, injection detection, schema validation, sandbox execution, determinism, error handling, and two instrument format parsers (BioTek Gen5 and SpectraMax M5).

## Docker

```bash
docker build -t plate-parser .
docker run -p 8000:8000 --env-file .env plate-parser
```

## Supabase setup

Run `supabase_setup.sql` in your Supabase SQL editor, then create two storage buckets in the dashboard:
- `uploads` — stores uploaded data files and PDFs
- `outputs` — stores generated JSON results

Use the **service_role** key (not the anon/publishable key) in `SUPABASE_KEY` — the backend needs full write access.
