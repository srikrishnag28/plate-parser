'use client'

import {
  Loader2, CheckCircle2, XCircle, MinusCircle, Circle, Info, ChevronRight,
} from 'lucide-react'
import type { StageStatus } from '@/lib/pipeline'
import { type PipelineStage, fmtDuration } from '@/lib/pipelineTypes'

// Per-status visual treatment for a node.
const NODE_STYLE: Record<StageStatus, string> = {
  running: 'border-green-400/70 bg-green-500/5 shadow-[0_0_24px_-4px_rgba(74,222,128,0.45)] ring-1 ring-green-400/40',
  done:    'border-green-500/40 bg-zinc-900',
  skipped: 'border-zinc-800 bg-zinc-900/40',
  error:   'border-red-500/50 bg-red-500/5 ring-1 ring-red-500/30',
  idle:    'border-zinc-800 bg-zinc-900/40',
}

const LABEL_STYLE: Record<StageStatus, string> = {
  running: 'text-zinc-100',
  done:    'text-zinc-200',
  skipped: 'text-zinc-500',
  error:   'text-red-300',
  idle:    'text-zinc-500',
}

function StatusIcon({ status }: { status: StageStatus }) {
  switch (status) {
    case 'running': return <Loader2 className="w-4 h-4 text-green-400 animate-spin" />
    case 'done':    return <CheckCircle2 className="w-4 h-4 text-green-400" />
    case 'skipped': return <MinusCircle className="w-4 h-4 text-zinc-600" />
    case 'error':   return <XCircle className="w-4 h-4 text-red-400" />
    default:        return <Circle className="w-4 h-4 text-zinc-700" />
  }
}

export function PipelineFlow({
  stages,
  onInfo,
}: {
  stages: PipelineStage[]
  onInfo: (stageName: string) => void
}) {
  return (
    <div className="bg-zinc-900 border border-zinc-800 rounded-xl overflow-hidden">
      <div className="px-5 py-3 border-b border-zinc-800">
        <p className="text-xs font-semibold uppercase tracking-wider text-zinc-500">Pipeline</p>
      </div>
      <div className="flex items-stretch gap-0 overflow-x-auto px-5 py-6">
        {stages.map((stage, i) => {
          const hasDetail = !!stage.summary || !!stage.error || stage.status !== 'idle'
          const connectorActive = stage.status === 'done' || stage.status === 'skipped'
          return (
            <div key={stage.name} className="flex items-center flex-shrink-0">
              {/* Stage node */}
              <div
                className={`relative w-44 rounded-lg border px-4 py-3 transition-all duration-300 ${NODE_STYLE[stage.status]} ${
                  stage.status === 'running' ? 'animate-[pulse_2.5s_ease-in-out_infinite]' : ''
                }`}
              >
                <button
                  onClick={() => onInfo(stage.name)}
                  disabled={!hasDetail}
                  title="View stage details"
                  className="absolute top-2 right-2 text-zinc-600 hover:text-green-400 disabled:opacity-0 transition-colors"
                >
                  <Info className="w-3.5 h-3.5" />
                </button>
                <div className="flex items-center gap-2">
                  <StatusIcon status={stage.status} />
                  <span className="text-[10px] font-mono uppercase tracking-wider text-zinc-600">
                    {String(i + 1).padStart(2, '0')}
                  </span>
                </div>
                <p className={`mt-2 text-sm font-medium leading-tight ${LABEL_STYLE[stage.status]}`}>
                  {stage.label}
                </p>
                <div className="mt-1.5 h-4 flex items-center">
                  {fmtDuration(stage.duration_ms) ? (
                    <span className="text-[11px] font-mono text-zinc-600">{fmtDuration(stage.duration_ms)}</span>
                  ) : stage.status === 'running' ? (
                    <span className="text-[11px] text-green-400/80">running…</span>
                  ) : null}
                </div>
              </div>

              {/* Connector to next stage */}
              {i < stages.length - 1 && (
                <ChevronRight
                  className={`w-5 h-5 mx-1 flex-shrink-0 transition-colors duration-300 ${
                    connectorActive ? 'text-green-500' : 'text-zinc-700'
                  }`}
                />
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}
