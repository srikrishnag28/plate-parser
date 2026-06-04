-- Plate Parser Database Schema
-- Run this in your Supabase SQL editor

CREATE TABLE IF NOT EXISTS jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    input_file_url TEXT,
    docs_url TEXT,
    status TEXT NOT NULL DEFAULT 'processing',
    sample_json JSONB,
    parser_code_temp TEXT,
    error_message TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS parsers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    instrument TEXT NOT NULL,
    version INTEGER NOT NULL DEFAULT 1,
    parser_code TEXT NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT true,
    job_id UUID REFERENCES jobs(id) ON DELETE SET NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS parser_runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    parser_id UUID NOT NULL REFERENCES parsers(id) ON DELETE CASCADE,
    output_json_url TEXT,
    status TEXT NOT NULL DEFAULT 'success',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes for common queries
CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status);
CREATE INDEX IF NOT EXISTS idx_parsers_is_active ON parsers(is_active);
CREATE INDEX IF NOT EXISTS idx_parser_runs_parser_id ON parser_runs(parser_id);

-- Storage buckets (run in Supabase dashboard or via API)
-- INSERT INTO storage.buckets (id, name, public) VALUES ('uploads', 'uploads', false);
-- INSERT INTO storage.buckets (id, name, public) VALUES ('outputs', 'outputs', false);

-- ── Pipeline rearchitecture migration ────────────────────────────────────────

ALTER TABLE parsers
  ADD COLUMN IF NOT EXISTS instrument_type TEXT,
  ADD COLUMN IF NOT EXISTS research_summary TEXT;

-- One active parser per instrument+read_type combo
CREATE UNIQUE INDEX IF NOT EXISTS idx_parsers_instrument_type
  ON parsers(instrument_type)
  WHERE instrument_type IS NOT NULL AND is_active = TRUE;

-- Pipeline run record (one per POST /parse call)
CREATE TABLE IF NOT EXISTS pipeline_runs (
  id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  parser_id   UUID REFERENCES parsers(id) ON DELETE SET NULL,
  created_at  TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Individual stage records within a pipeline run
CREATE TABLE IF NOT EXISTS pipeline_stages (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  pipeline_run_id UUID NOT NULL REFERENCES pipeline_runs(id) ON DELETE CASCADE,
  stage           TEXT NOT NULL,
  status          TEXT NOT NULL,
  summary         TEXT,
  duration_ms     INTEGER,
  created_at      TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_pipeline_stages_run_id
  ON pipeline_stages(pipeline_run_id);
