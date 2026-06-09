'use client'

import { useState, useCallback, useRef } from 'react'
import Link from 'next/link'
import { Zap, BarChart3, Code2, Microscope, Braces, ArrowRight, AlertTriangle, Trash2 } from 'lucide-react'
import { Nav } from '@/components/Nav'
import { DropZone } from '@/components/DropZone'
import { WellsTable } from '@/components/WellsTable'
import { PipelineFlow } from '@/components/PipelineFlow'
import { StageDrawer } from '@/components/StageDrawer'
import { streamParse, type StageEvent } from '@/lib/pipeline'
import { type PipelineStage, type LogLine } from '@/lib/pipelineTypes'
import { clearDatabase, type PlateReaderOutput, type Well } from '@/lib/api'

interface ParseResult {
  output_json: PlateReaderOutput
  parser_id: string
  parser_code: string
  pipeline_run_id: string
  cached: boolean
}

type OutputTab = 'summary' | 'code' | 'wells' | 'json'

const STAGE_DEFS: PipelineStage[] = [
  { name: 'identify', label: 'Identify',         status: 'idle' },
  { name: 'research', label: 'Research Format',   status: 'idle' },
  { name: 'generate', label: 'Generate Parser',   status: 'idle' },
  { name: 'save',     label: 'Save to Library',   status: 'idle' },
  { name: 'execute',  label: 'Extract Data',      status: 'idle' },
]

function Stat({ value, label }: { value: string; label: string }) {
  return (
    <div className="text-center px-3">
      <div className="text-lg font-bold text-green-400 leading-tight">{value}</div>
      <div className="text-xs text-zinc-500 mt-0.5">{label}</div>
    </div>
  )
}

function CopyBtn({ text }: { text: string }) {
  const [done, setDone] = useState(false)
  return (
    <button
      onClick={() => { navigator.clipboard.writeText(text); setDone(true); setTimeout(() => setDone(false), 2000) }}
      className="text-xs px-2 py-1 rounded border border-zinc-700 text-zinc-400 hover:text-zinc-200 hover:border-zinc-500 transition-colors"
    >
      {done ? '✓ Copied' : 'Copy'}
    </button>
  )
}

const TAB_META: { id: OutputTab; label: string; Icon: typeof BarChart3 }[] = [
  { id: 'summary', label: 'Summary',     Icon: BarChart3 },
  { id: 'code',    label: 'Parser Code', Icon: Code2 },
  { id: 'wells',   label: 'Wells',       Icon: Microscope },
  { id: 'json',    label: 'Raw JSON',    Icon: Braces },
]

export default function PlateReaderTool() {
  const [dataFile, setDataFile] = useState<File | null>(null)
  const [docsFile, setDocsFile] = useState<File | null>(null)
  const [parsing,  setParsing]  = useState(false)
  const [stages,   setStages]   = useState<PipelineStage[]>(STAGE_DEFS)
  const [result,   setResult]   = useState<ParseResult | null>(null)
  const [error,    setError]    = useState<string | null>(null)
  const [tab,      setTab]      = useState<OutputTab>('summary')
  const [logsByStage, setLogsByStage] = useState<Record<string, LogLine[]>>({})
  const [drawerStage, setDrawerStage] = useState<string | null>(null)

  const [clearing, setClearing] = useState(false)

  // Tracks which stage is currently running, so interleaved log events get attributed to it.
  const currentStageRef = useRef<string>('identify')

  const handleClearDb = useCallback(async () => {
    if (clearing) return
    if (!confirm('Clear everything? This permanently deletes all jobs, parsers, runs, and uploaded/output files.')) return
    setClearing(true)
    try {
      await clearDatabase()
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to clear database')
    } finally {
      setClearing(false)
    }
  }, [clearing])

  const handleParse = useCallback(async () => {
    if (!dataFile || parsing) return
    setError(null)
    setResult(null)
    setLogsByStage({})
    setDrawerStage(null)
    currentStageRef.current = 'identify'
    setStages(STAGE_DEFS.map(s => ({ ...s, status: 'idle', summary: undefined, duration_ms: undefined, error: undefined })))
    setParsing(true)
    setTab('summary')

    try {
      await streamParse(dataFile, docsFile, (event: StageEvent) => {
        if (event.stage === 'log') {
          const bucket = currentStageRef.current
          setLogsByStage(prev => ({
            ...prev,
            [bucket]: [...(prev[bucket] ?? []), { level: event.status, message: event.message ?? '', ts: Date.now() }],
          }))
          return
        }
        if (event.stage === 'complete') {
          if (event.output_json) {
            setResult({
              output_json:     event.output_json,
              parser_id:       event.parser_id!,
              parser_code:     event.parser_code!,
              pipeline_run_id: event.pipeline_run_id!,
              cached:          event.cached ?? false,
            })
          } else if (event.status === 'error') {
            setError(event.error ?? 'Pipeline failed')
          }
          setParsing(false)
          return
        }
        if (event.stage === 'error') {
          setError(event.error ?? 'Pipeline failed')
          setParsing(false)
          return
        }
        // Stage transition event
        if (event.status === 'running') currentStageRef.current = event.stage
        setStages(prev => prev.map(s =>
          s.name === event.stage
            ? { ...s, status: event.status, summary: event.summary, duration_ms: event.duration_ms, error: event.error }
            : s
        ))
      })
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Parse failed')
      setParsing(false)
    }
  }, [dataFile, docsFile, parsing])

  const prd   = result?.output_json?.plate_reader_document
  const wells = (prd?.wells ?? []) as Well[]
  const inst  = prd?.instrument  ?? {}
  const exp   = prd?.experiment  ?? {}
  const ms    = prd?.measurement_settings ?? {}

  const isPipelineActive = parsing || stages.some(s => s.status !== 'idle')
  const drawerStageObj = stages.find(s => s.name === drawerStage) ?? null

  return (
    <div className="min-h-screen bg-zinc-950">
      <Nav />

      <main className="max-w-4xl mx-auto px-4 py-8 space-y-5">
        <div className="flex items-start justify-between gap-4">
          <div>
            <h1 className="text-2xl font-bold text-zinc-100">Plate Reader Parser</h1>
            <p className="text-sm text-zinc-500 mt-1">
              Drop a plate reader export — the AI pipeline identifies it, generates a parser, and extracts structured data.
            </p>
          </div>
          <button
            onClick={handleClearDb}
            disabled={clearing}
            className="flex-shrink-0 flex items-center gap-1.5 text-xs px-3 py-1.5 rounded-lg border border-red-500/30 text-red-400 hover:bg-red-500/10 hover:border-red-500/50 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
          >
            <Trash2 className="w-3.5 h-3.5" />
            {clearing ? 'Clearing…' : 'Clear DB'}
          </button>
        </div>

        {error && (
          <div className="bg-red-500/10 border border-red-500/30 rounded-xl p-4 text-red-400 text-sm flex items-center gap-2">
            <AlertTriangle className="w-4 h-4 flex-shrink-0" /> {error}
          </div>
        )}

        {/* Upload card */}
        <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-6 space-y-5">
          <h2 className="font-semibold text-zinc-100">Upload Files</h2>
          <div className="grid grid-cols-2 gap-3">
            <DropZone
              label="Plate Reader File"
              hint="CSV or TXT — required"
              accept=".csv,.txt"
              file={dataFile}
              onFile={setDataFile}
              onClear={() => setDataFile(null)}
              icon="📄"
            />
            <DropZone
              label="PDF Documentation"
              hint="Optional — AI will web search if omitted"
              accept=".pdf"
              file={docsFile}
              onFile={setDocsFile}
              onClear={() => setDocsFile(null)}
              icon="📋"
            />
          </div>
          <button
            onClick={handleParse}
            disabled={!dataFile || parsing}
            className="w-full py-2.5 rounded-lg font-semibold text-sm bg-green-500 text-black hover:bg-green-400 disabled:opacity-40 disabled:cursor-not-allowed transition-colors flex items-center justify-center gap-2"
          >
            <Zap className="w-4 h-4" />
            {parsing ? 'Running pipeline…' : 'Parse File'}
          </button>
        </div>

        {/* Pipeline flowchart */}
        {isPipelineActive && <PipelineFlow stages={stages} onInfo={setDrawerStage} />}

        {/* Output */}
        {result && (
          <>
            {/* Stats bar */}
            <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-5">
              <div className="flex items-center gap-2 mb-4 flex-wrap">
                <span className={`text-xs px-2 py-1 rounded-full font-medium ${
                  result.cached ? 'bg-zinc-700/50 text-zinc-400' : 'bg-green-500/20 text-green-400'
                }`}>
                  {result.cached ? '⚡ cached' : '✓ generated'}
                </span>
                <span className="text-xs font-mono px-2 py-1 rounded-full bg-zinc-800 text-zinc-400">
                  parser: {result.parser_id.slice(0, 8)}…
                </span>
              </div>
              <div className="flex divide-x divide-zinc-800 justify-around">
                <Stat value={String(wells.length)}                    label="Wells" />
                <Stat value={exp.plate_format ?? '—'}                 label="Format" />
                <Stat value={exp.detection_method ?? '—'}             label="Detection" />
                <Stat value={ms.measurement_wavelength_nm ? `${ms.measurement_wavelength_nm} nm` : '—'} label="Wavelength" />
                <Stat value={`${inst.manufacturer ?? ''} ${inst.model ?? ''}`.trim() || '—'} label="Instrument" />
              </div>
            </div>

            {/* Tabs */}
            <div className="bg-zinc-900 border border-zinc-800 rounded-xl overflow-hidden">
              <div className="flex border-b border-zinc-800 overflow-x-auto">
                {TAB_META.map(({ id, label, Icon }) => (
                  <button
                    key={id}
                    onClick={() => setTab(id)}
                    className={`flex items-center gap-1.5 px-4 py-2.5 text-sm font-medium whitespace-nowrap transition-colors flex-shrink-0 ${
                      tab === id
                        ? 'text-green-400 border-b-2 border-green-400 bg-zinc-800/50'
                        : 'text-zinc-500 hover:text-zinc-300'
                    }`}
                  >
                    <Icon className="w-4 h-4" /> {label}
                  </button>
                ))}
              </div>

              <div className="p-5">
                {tab === 'summary' && (
                  <div className="grid grid-cols-2 gap-6 text-sm">
                    <div className="space-y-2.5">
                      <p className="text-xs font-semibold uppercase tracking-wider text-zinc-600">Instrument</p>
                      {([
                        ['Manufacturer', inst.manufacturer],
                        ['Model',        inst.model],
                        ['Software',     inst.software],
                        ['Serial',       inst.serial_number],
                      ] as [string, string | null | undefined][]).filter(([, v]) => v).map(([k, v]) => (
                        <div key={k} className="flex justify-between gap-4">
                          <span className="text-zinc-500">{k}</span>
                          <span className="font-mono text-zinc-100 text-right">{v}</span>
                        </div>
                      ))}
                    </div>
                    <div className="space-y-2.5">
                      <p className="text-xs font-semibold uppercase tracking-wider text-zinc-600">Experiment</p>
                      {([
                        ['Read Type',  exp.read_type],
                        ['Detection',  exp.detection_method],
                        ['Plate',      exp.plate_format],
                        ['Date',       exp.read_date],
                        ['Time',       exp.read_time],
                        ['Temp °C',    exp.temperature_celsius != null ? String(exp.temperature_celsius) : null],
                        ['Wavelength', ms.measurement_wavelength_nm ? `${ms.measurement_wavelength_nm} nm` : null],
                        ['Excitation', ms.excitation_wavelength_nm ? `${ms.excitation_wavelength_nm} nm` : null],
                        ['Emission',   ms.emission_wavelength_nm   ? `${ms.emission_wavelength_nm} nm`   : null],
                      ] as [string, string | null | undefined][]).filter(([, v]) => v).map(([k, v]) => (
                        <div key={k} className="flex justify-between gap-4">
                          <span className="text-zinc-500">{k}</span>
                          <span className="font-mono text-zinc-100 text-right">{v}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {tab === 'code' && (
                  <div>
                    <div className="flex items-center justify-between mb-3">
                      <p className="text-xs text-zinc-500">Generated Python parser — deterministic, zero AI cost on future runs</p>
                      <CopyBtn text={result.parser_code} />
                    </div>
                    <pre className="bg-zinc-950 border border-zinc-800 rounded-lg p-4 overflow-auto max-h-[420px] text-xs font-mono text-zinc-300 leading-relaxed">
                      {result.parser_code}
                    </pre>
                  </div>
                )}

                {tab === 'wells' && (
                  wells.length > 0
                    ? <WellsTable wells={wells} />
                    : <p className="text-zinc-500 text-sm">No wells in output.</p>
                )}

                {tab === 'json' && (
                  <div>
                    <div className="flex justify-end mb-3">
                      <CopyBtn text={JSON.stringify(result.output_json, null, 2)} />
                    </div>
                    <pre className="bg-zinc-950 border border-zinc-800 rounded-lg p-4 overflow-auto max-h-[420px] text-xs font-mono text-zinc-300 leading-relaxed">
                      {JSON.stringify(result.output_json, null, 2)}
                    </pre>
                  </div>
                )}
              </div>
            </div>

            <div className="text-center">
              <Link href="/parsers" className="inline-flex items-center gap-1 text-sm text-green-400 hover:underline">
                View Parser Library <ArrowRight className="w-4 h-4" />
              </Link>
            </div>
          </>
        )}
      </main>

      {/* Stage detail drawer */}
      <StageDrawer
        stage={drawerStageObj}
        logs={drawerStage ? (logsByStage[drawerStage] ?? []) : []}
        onClose={() => setDrawerStage(null)}
      />
    </div>
  )
}
