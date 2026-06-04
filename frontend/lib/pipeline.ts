import type { PlateReaderOutput } from './api'

const API = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000'

export type StageStatus = 'idle' | 'running' | 'done' | 'skipped' | 'error'

export interface StageEvent {
  stage: string
  status: StageStatus
  summary?: string
  duration_ms?: number
  error?: string
  message?: string  // present on stage === 'log' events
  // present only on stage === 'complete'
  output_json?: PlateReaderOutput
  parser_id?: string
  parser_code?: string
  pipeline_run_id?: string
  cached?: boolean
}

export async function streamParse(
  file: File,
  docs: File | null,
  onEvent: (e: StageEvent) => void,
): Promise<void> {
  const fd = new FormData()
  fd.append('file', file)
  if (docs) fd.append('docs', docs)

  const res = await fetch(`${API}/parse`, { method: 'POST', body: fd })

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(err.detail ?? res.statusText)
  }

  const reader = res.body!.getReader()
  const decoder = new TextDecoder()
  let buffer = ''

  while (true) {
    const { done, value } = await reader.read()
    if (done) break

    buffer += decoder.decode(value, { stream: true })
    const lines = buffer.split('\n')
    buffer = lines.pop() ?? ''

    for (const line of lines) {
      if (!line.startsWith('data: ')) continue
      const payload = line.slice(6).trim()
      if (payload === '[DONE]') return
      try {
        onEvent(JSON.parse(payload) as StageEvent)
      } catch {
        // ignore malformed lines
      }
    }
  }
}
