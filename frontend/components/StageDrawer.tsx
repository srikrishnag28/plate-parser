'use client'

import { useEffect } from 'react'
import { X, CheckCircle2, XCircle, Loader2, MinusCircle, Circle } from 'lucide-react'
import type { StageStatus } from '@/lib/pipeline'
import { type PipelineStage, type LogLine, fmtDuration } from '@/lib/pipelineTypes'

const STATUS_BADGE: Record<StageStatus, string> = {
  running: 'bg-green-500/15 text-green-400',
  done:    'bg-green-500/15 text-green-400',
  skipped: 'bg-zinc-700/40 text-zinc-400',
  error:   'bg-red-500/15 text-red-400',
  idle:    'bg-zinc-700/40 text-zinc-500',
}

function StatusIcon({ status }: { status: StageStatus }) {
  switch (status) {
    case 'running': return <Loader2 className="w-5 h-5 text-green-400 animate-spin" />
    case 'done':    return <CheckCircle2 className="w-5 h-5 text-green-400" />
    case 'skipped': return <MinusCircle className="w-5 h-5 text-zinc-500" />
    case 'error':   return <XCircle className="w-5 h-5 text-red-400" />
    default:        return <Circle className="w-5 h-5 text-zinc-600" />
  }
}

export function StageDrawer({
  stage,
  logs,
  onClose,
}: {
  stage: PipelineStage | null
  logs: LogLine[]
  onClose: () => void
}) {
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose() }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [onClose])

  const open = stage !== null

  return (
    <div className={`fixed inset-0 z-50 ${open ? '' : 'pointer-events-none'}`} aria-hidden={!open}>
      {/* Backdrop */}
      <div
        onClick={onClose}
        className={`absolute inset-0 bg-black/50 transition-opacity duration-300 ${open ? 'opacity-100' : 'opacity-0'}`}
      />
      {/* Panel */}
      <aside
        className={`absolute top-0 right-0 h-full w-full max-w-md bg-zinc-950 border-l border-zinc-800 shadow-2xl flex flex-col transition-transform duration-300 ${
          open ? 'translate-x-0' : 'translate-x-full'
        }`}
      >
        {stage && (
          <>
            <div className="flex items-start justify-between gap-3 px-5 py-4 border-b border-zinc-800">
              <div className="flex items-center gap-3">
                <StatusIcon status={stage.status} />
                <div>
                  <h3 className="font-semibold text-zinc-100 leading-tight">{stage.label}</h3>
                  <div className="flex items-center gap-2 mt-1">
                    <span className={`text-[11px] px-2 py-0.5 rounded-full font-medium ${STATUS_BADGE[stage.status]}`}>
                      {stage.status}
                    </span>
                    {fmtDuration(stage.duration_ms) && (
                      <span className="text-[11px] font-mono text-zinc-500">{fmtDuration(stage.duration_ms)}</span>
                    )}
                  </div>
                </div>
              </div>
              <button onClick={onClose} className="text-zinc-500 hover:text-zinc-200 transition-colors">
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="flex-1 overflow-y-auto px-5 py-4 space-y-5">
              {/* Summary */}
              <div>
                <p className="text-xs font-semibold uppercase tracking-wider text-zinc-600 mb-2">Summary</p>
                {stage.error ? (
                  <p className="text-sm text-red-400 whitespace-pre-wrap leading-relaxed">{stage.error}</p>
                ) : stage.summary ? (
                  <p className="text-sm text-zinc-300 whitespace-pre-wrap leading-relaxed">{stage.summary}</p>
                ) : (
                  <p className="text-sm text-zinc-600">No summary for this stage yet.</p>
                )}
              </div>

              {/* Logs */}
              <div>
                <p className="text-xs font-semibold uppercase tracking-wider text-zinc-600 mb-2">
                  Logs <span className="text-zinc-700">({logs.length})</span>
                </p>
                {logs.length > 0 ? (
                  <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-3 font-mono text-xs leading-relaxed space-y-0.5">
                    {logs.map((line, i) => (
                      <div key={i} className={`flex gap-2 ${
                        line.level === 'error'   ? 'text-red-400' :
                        line.level === 'warning' ? 'text-yellow-400' :
                        'text-zinc-400'
                      }`}>
                        <span className="text-zinc-700 flex-shrink-0 select-none">
                          {line.level === 'error' ? '[ERR]' : line.level === 'warning' ? '[WRN]' : '[INF]'}
                        </span>
                        <span className="break-all">{line.message}</span>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-sm text-zinc-600">No logs captured for this stage.</p>
                )}
              </div>
            </div>
          </>
        )}
      </aside>
    </div>
  )
}
