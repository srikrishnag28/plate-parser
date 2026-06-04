# Team AStra — InstrumentParser

> An AI **agent** that turns any lab instrument's raw export into clean, structured, schema-validated data — and writes a reusable parser while it's at it.

InstrumentParser is not a fixed set of parsing rules. It's a reasoning agent: hand it a sample export (and optionally the instrument's documentation) and it **identifies** the instrument, **researches** its export format, **writes** its own Python parser, **tests** that parser in a sandbox, and **extracts** the data. The first run does the hard thinking; every later file from the same instrument runs the saved parser instantly, deterministically, with zero AI cost.

Today the agent is focused on **plate readers** — any vendor, any format. The architecture is general: new instrument classes are a matter of giving the agent a new output schema to target.

---

## The problem

Every instrument exports data in its own quirky layout. Getting it usable traditionally means **outsourcing to an engineering team** to hand-write a custom parsing script per instrument and format — slow, expensive, and brittle. InstrumentParser removes the script-commissioning step entirely: you throw in the files, the agent produces the structured data **and** the parser.

---

## How the agent works

A five-stage pipeline runs on every file and streams its progress live (Server-Sent Events):

```
   ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌────────┐   ┌──────────┐
   │ Identify │──▶│ Research │──▶│ Generate │──▶│  Save  │──▶│ Extract  │
   └──────────┘   └──────────┘   └──────────┘   └────────┘   └──────────┘
   recognise the   study format    write parser,   version it   schema-valid
   instrument &    (docs + web      sandbox-test,   in the       structured
   read type       search)          self-correct    library      JSON out
```

1. **Identify** — works out the instrument and read type purely from the data (no hardcoded vendor list). If the file clearly isn't a plate reader, it stops and says so.
2. **Research** — reads your uploaded docs and web-searches for the export spec: delimiters, plate dimensions, multi-row blocks, value qualifiers (`>`, `<`), negative blank-corrected values.
3. **Generate** — writes a self-contained Python parser, runs it in a locked-down sandbox, validates the output, and on any failure feeds the error back to itself and retries.
4. **Save** — stores the working parser in the library, keyed to instrument + read type, for instant reuse.
5. **Extract** — returns clean, schema-validated JSON: instrument metadata, experiment settings, and every well with raw / blank-corrected / concentration values.

---

## Architecture

```
┌───────────────────────────────────────────────┐
│  Next.js frontend (frontend/)                  │
│  /            landing                          │
│  /plate-reader  upload + live pipeline flowchart│
│  /parsers     saved-parser library + run       │
│  /docs        product documentation            │
└───────────────────────┬───────────────────────┘
                        │ SSE  (POST /parse)
┌───────────────────────▼───────────────────────┐
│  FastAPI backend (app/)                        │
│  pipeline.py  5-stage agent orchestration      │
│  identifier.py  AI instrument classification   │
│  agent.py    research + parser generation      │
│  sandbox.py  isolated parser execution         │
│  validator.py  JSON schema + plate consistency │
└───────┬───────────────────────────┬───────────┘
        │                           │
        ▼                           ▼
┌───────────────┐         ┌──────────────────────┐
│  Private AI    │         │  Supabase            │
│  provider —    │         │  Postgres: parsers,  │
│  private       │         │  jobs, pipeline_runs,│
│  inference,    │         │  pipeline_stages     │
│  TEE-ready,    │         │  Storage: uploads,   │
│  + web search  │         │  outputs             │
└───────────────┘         └──────────────────────┘
```

| Module | Responsibility |
|---|---|
| `app/pipeline.py` | Orchestrates the 5-stage agent, streams SSE events |
| `app/identifier.py` | Single AI call: instrument/read-type classification + non-plate-reader rejection |
| `app/agent.py` | Private-AI research + parser generation, self-correcting retry loop |
| `app/sandbox.py` | Runs generated parsers in isolation (no network, timeout) |
| `app/validator.py` | JSON schema validation + plate-format consistency checks |
| `app/database.py` / `app/storage.py` | Supabase Postgres tables + storage buckets |
| `app/main.py` | FastAPI routes |

---

## Quick start

### Prerequisites
- Python 3.13, Node.js 18+
- An API key for the private AI provider, a [Supabase](https://supabase.com) project

### 1. Backend

```bash
git clone <repo> && cd plate-parser
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env        # fill in your keys (see below)

uvicorn app.main:app --reload --port 8000
```

### 2. Supabase

Apply the schema and create the storage buckets + access policies:

```sql
-- Run supabase_setup.sql in the Supabase SQL editor, then:
insert into storage.buckets (id, name, public) values
  ('uploads','uploads',false), ('outputs','outputs',false)
  on conflict (id) do nothing;
```

Tables created: `jobs`, `parsers`, `parser_runs`, `pipeline_runs`, `pipeline_stages`.

### 3. Frontend

```bash
cd frontend
npm install
npm run dev          # http://localhost:3000
```

Open **http://localhost:3000**, go to the Plate Reader demo, drop in a file from `samples/`, and watch the agent build a parser live.

---

## Environment variables

| Variable | Description |
|---|---|
| `PRIVATE_AI_API_KEY` | Key for the private AI provider (private inference, OpenAI-compatible endpoint) |
| `SUPABASE_URL` | Your Supabase project URL |
| `SUPABASE_KEY` | Supabase API key |
| `MAX_FILE_SIZE_MB` | Max upload size per file (default 10) |

Frontend reads `NEXT_PUBLIC_API_URL` (defaults to `http://localhost:8000`).

---

## API

| Endpoint | Description |
|---|---|
| `POST /parse` | **Main flow.** Multipart `file` (+ optional `docs` PDF). Streams SSE events for each pipeline stage; final event carries the output JSON, parser code, and IDs. |
| `GET /parsers` | List saved parsers |
| `POST /run/{parser_id}` | Run a saved parser on a new file — deterministic, no AI |
| `POST /upload`, `POST /approve/{job_id}`, `POST /feedback/{job_id}` | Legacy human-in-the-loop generate/approve/refine flow |
| `GET /jobs/{job_id}` | Job status |
| `GET /health` | Health check |

---

## Output schema

Every parser produces a `plate_reader_document`:

```json
{
  "plate_reader_document": {
    "instrument": { "manufacturer": "...", "model": "...", "serial_number": null, "software": "..." },
    "experiment": { "id": null, "read_date": "...", "read_time": "...", "read_type": "endpoint|kinetic",
                    "detection_method": "absorbance|fluorescence|luminescence",
                    "plate_format": "96-well|384-well|1536-well", "temperature_celsius": null },
    "measurement_settings": { "measurement_wavelength_nm": 630, "reference_wavelength_nm": null,
                              "excitation_wavelength_nm": null, "emission_wavelength_nm": null },
    "wells": [
      { "well_position": "A1", "row": "A", "column": 1, "raw_value": 3.337, "unit": "OD",
        "sample_id": "STD1", "well_role": "control", "blank_corrected_value": 3.336,
        "concentration": ">209.845", "timepoints": null }
    ]
  }
}
```

Output is validated against this schema **and** a plate-consistency check (well counts and positions must match the declared plate format).

---

## Privacy

Inference runs on a **privacy-focused private AI provider** — your instrument data is processed with private inference rather than sent to a general public model API. The inference layer can be **moved into a Trusted Execution Environment (TEE) on demand**, so sensitive lab data is processed inside hardware-isolated enclaves when required.

## Safety & correctness

- Generated parsers run in a **restricted sandbox** — no network, no shell, with a timeout.
- Untrusted file content is fenced in `<raw_data>` tags so it can't steer the agent.
- Output is strictly schema-validated, including plate-format consistency.
- On validation failure the agent **self-corrects and retries** rather than returning bad data.
- File type/size validation on upload; non-plate-reader files are rejected early.

---

## Sample files

`samples/` contains real instrument exports for testing:

| File | Instrument | Detection |
|---|---|---|
| `biotek_sample.txt` / `.csv` | BioTek Synergy (Gen5) | Absorbance 630 nm |
| `spectramax_sample.txt` | Molecular Devices SpectraMax | Fluorescence Ex 485 / Em 535 nm |

Matching `*_docs.pdf` files can be supplied to the optional `docs` input.

---

## Tests

```bash
source .venv/bin/activate
pytest -q
```

Covers schema/plate-consistency validation, sandbox execution, upload validation, and instrument-format parsers.

---

## Roadmap

- **More instrument classes** — mass spec, qPCR, chromatography, sequencers (same agent, new schemas)
- **Human-in-the-loop refinement** — correct an edge case once; the agent regenerates and re-versions
- **Confidence scoring** — per-field confidence and anomaly flagging
- **Batch & API ingestion** — folder watch / endpoint for unattended bulk parsing
- **Standards alignment** — map output to lab-data standards (e.g. Allotrope) for direct LIMS/ELN ingestion

---

**Team AStra**
