const API = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000'

async function apiFetch(path: string, init?: RequestInit) {
  const res = await fetch(`${API}${path}`, init)
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(err.detail ?? res.statusText)
  }
  return res.json()
}

export interface UploadResult {
  job_id: string
  status: string
  sample_json: PlateReaderOutput
  parser_code: string
  message: string
}

export interface ApproveResult {
  parser_id: string
  job_id: string
  message: string
}

export interface FeedbackResult {
  job_id: string
  status: string
  sample_json: PlateReaderOutput
  parser_code: string
  message: string
}

export interface Parser {
  id: string
  name: string
  instrument: string
  version: number
  is_active: boolean
  created_at: string
}

export interface RunResult {
  run_id: string
  parser_id: string
  output_json: PlateReaderOutput
  status: string
  message: string
}

export interface PlateReaderOutput {
  plate_reader_document: {
    instrument: {
      manufacturer?: string | null
      model?: string | null
      serial_number?: string | null
      software?: string | null
    }
    experiment: {
      id?: string | null
      read_date?: string | null
      read_time?: string | null
      read_type?: string | null
      detection_method?: string | null
      plate_format?: string | null
      temperature_celsius?: number | null
    }
    measurement_settings: {
      measurement_wavelength_nm?: number | null
      reference_wavelength_nm?: number | null
      excitation_wavelength_nm?: number | null
      emission_wavelength_nm?: number | null
    }
    wells: Well[]
  }
}

export interface Well {
  well_position: string
  row: string
  column: number
  raw_value: number
  unit: string
  well_role?: string | null
  sample_id?: string | null
  blank_corrected_value?: number | null
}

export async function uploadAndParse(file: File, docs: File): Promise<UploadResult> {
  const fd = new FormData()
  fd.append('file', file)
  fd.append('docs', docs)
  return apiFetch('/upload', { method: 'POST', body: fd })
}

export async function approveParser(jobId: string): Promise<ApproveResult> {
  return apiFetch(`/approve/${jobId}`, { method: 'POST' })
}

export async function submitFeedback(jobId: string, feedback: string): Promise<FeedbackResult> {
  return apiFetch(`/feedback/${jobId}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ feedback }),
  })
}

export async function listParsers(): Promise<Parser[]> {
  return apiFetch('/parsers')
}

export async function runParser(parserId: string, file: File): Promise<RunResult> {
  const fd = new FormData()
  fd.append('file', file)
  return apiFetch(`/run/${parserId}`, { method: 'POST', body: fd })
}

export async function clearDatabase(): Promise<{ message: string }> {
  return apiFetch('/database', { method: 'DELETE' })
}
