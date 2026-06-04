import type { StageStatus } from './pipeline'

export interface PipelineStage {
  name: string
  label: string
  status: StageStatus
  summary?: string
  duration_ms?: number
  error?: string
}

export interface LogLine {
  level: string  // 'info' | 'warning' | 'error'
  message: string
  ts: number
}

export function fmtDuration(ms?: number): string | null {
  if (ms === undefined) return null
  return ms < 1000 ? `${ms}ms` : `${(ms / 1000).toFixed(1)}s`
}
