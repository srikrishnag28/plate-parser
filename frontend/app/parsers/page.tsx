'use client'

import { useState, useEffect } from 'react'
import Link from 'next/link'
import { Nav } from '@/components/Nav'
import { DropZone } from '@/components/DropZone'
import { WellsTable } from '@/components/WellsTable'
import { listParsers, runParser, type Parser, type RunResult } from '@/lib/api'

type OutputTab = 'summary' | 'wells' | 'json'

export default function ParsersPage() {
  const [parsers, setParsers] = useState<Parser[]>([])
  const [loading, setLoading] = useState(true)
  const [loadError, setLoadError] = useState<string | null>(null)
  const [selected, setSelected] = useState<Parser | null>(null)
  const [runFile, setRunFile] = useState<File | null>(null)
  const [running, setRunning] = useState(false)
  const [runResult, setRunResult] = useState<RunResult | null>(null)
  const [runError, setRunError] = useState<string | null>(null)
  const [tab, setTab] = useState<OutputTab>('summary')

  useEffect(() => { load() }, [])

  async function load() {
    setLoading(true)
    setLoadError(null)
    try {
      const data = await listParsers()
      setParsers(data)
      if (data.length > 0 && !selected) setSelected(data[0])
    } catch (e) {
      setLoadError(e instanceof Error ? e.message : 'Failed to load parsers')
    } finally {
      setLoading(false)
    }
  }

  async function handleRun() {
    if (!selected || !runFile) return
    setRunning(true)
    setRunError(null)
    setRunResult(null)
    try {
      const result = await runParser(selected.id, runFile)
      setRunResult(result)
      setTab('summary')
    } catch (e) {
      setRunError(e instanceof Error ? e.message : 'Run failed')
    } finally {
      setRunning(false)
    }
  }

  function downloadJson(data: object) {
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = 'plate_output.json'
    a.click()
    URL.revokeObjectURL(url)
  }

  const prd = runResult?.output_json?.plate_reader_document
  const wells = prd?.wells ?? []

  return (
    <div className="min-h-screen bg-zinc-950">
      <Nav />

      <main className="max-w-2xl mx-auto px-4 py-8 space-y-5">

        {/* Parser library */}
        <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="font-semibold text-zinc-100">Parser Library</h2>
            <button
              onClick={load}
              className="text-xs text-zinc-500 hover:text-zinc-300 border border-zinc-700 hover:border-zinc-500 rounded px-2 py-1 transition-colors"
            >
              ↻ Refresh
            </button>
          </div>

          {loading && <p className="text-zinc-500 text-sm">Loading...</p>}
          {loadError && <p className="text-red-400 text-sm">{loadError}</p>}

          {!loading && !loadError && parsers.length === 0 && (
            <div className="text-center py-8 space-y-2">
              <p className="text-zinc-500 text-sm">No approved parsers yet.</p>
              <Link href="/plate-reader" className="text-green-400 text-sm hover:underline">
                Upload a file to generate one →
              </Link>
            </div>
          )}

          <div className="space-y-2">
            {parsers.map(p => (
              <button
                key={p.id}
                onClick={() => { setSelected(p); setRunResult(null); setRunFile(null) }}
                className={`w-full text-left p-3 rounded-lg border transition-colors flex items-center gap-3 ${
                  selected?.id === p.id
                    ? 'border-green-500 bg-green-500/5'
                    : 'border-zinc-800 hover:border-zinc-700'
                }`}
              >
                <div className={`w-2 h-2 rounded-full flex-shrink-0 ${
                  selected?.id === p.id ? 'bg-green-400' : 'bg-zinc-600'
                }`} />
                <div className="flex-1 min-w-0">
                  <div className="font-medium text-sm text-zinc-100">{p.name}</div>
                  <div className="text-xs text-zinc-500 font-mono mt-0.5">
                    {p.instrument} · v{p.version} · {new Date(p.created_at).toLocaleDateString()}
                  </div>
                </div>
                <div className="text-xs text-zinc-700 font-mono flex-shrink-0">{p.id.slice(0, 8)}…</div>
              </button>
            ))}
          </div>
        </div>

        {/* Run section */}
        {selected && (
          <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-6 space-y-4">
            <h2 className="font-semibold text-zinc-100">
              Run: <span className="text-green-400">{selected.name}</span>
            </h2>
            <DropZone
              label="Plate Reader File"
              hint="CSV or TXT"
              accept=".csv,.txt"
              file={runFile}
              onFile={f => { setRunFile(f); setRunResult(null) }}
              onClear={() => { setRunFile(null); setRunResult(null) }}
              icon="📄"
            />
            {runError && <p className="text-red-400 text-sm">⚠ {runError}</p>}
            <button
              onClick={handleRun}
              disabled={!runFile || running}
              className="w-full py-2.5 rounded-lg font-semibold text-sm bg-green-500 text-black hover:bg-green-400 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
            >
              {running ? '⠋ Running...' : '▶ Run Parser'}
            </button>
            <p className="text-xs text-zinc-600 text-center">
              No AI — runs the saved deterministic Python parser
            </p>
          </div>
        )}

        {/* Output */}
        {runResult && (
          <div className="bg-zinc-900 border border-zinc-800 rounded-xl overflow-hidden">
            <div className="flex items-center justify-between px-5 py-3 border-b border-zinc-800">
              <div className="flex gap-2">
                <span className="text-xs px-2 py-1 rounded-full bg-green-500/20 text-green-400 font-medium">✓ success</span>
                <span className="text-xs px-2 py-1 rounded-full bg-zinc-800 text-zinc-400 font-mono">
                  {wells.length} wells
                </span>
              </div>
              <button
                onClick={() => downloadJson(runResult.output_json)}
                className="text-xs px-3 py-1 rounded border border-zinc-700 text-zinc-400 hover:text-zinc-200 hover:border-zinc-500 transition-colors"
              >
                ⬇ Download JSON
              </button>
            </div>

            <div className="flex border-b border-zinc-800">
              {(['summary', 'wells', 'json'] as OutputTab[]).map(t => (
                <button
                  key={t}
                  onClick={() => setTab(t)}
                  className={`px-4 py-2.5 text-sm font-medium transition-colors ${
                    tab === t
                      ? 'text-green-400 border-b-2 border-green-400 bg-zinc-800/50'
                      : 'text-zinc-500 hover:text-zinc-300'
                  }`}
                >
                  {t === 'summary' && '📊 Summary'}
                  {t === 'wells'   && '🔬 Wells'}
                  {t === 'json'    && '{ } Raw JSON'}
                </button>
              ))}
            </div>

            <div className="p-5">
              {tab === 'summary' && prd && (
                <div className="grid grid-cols-2 gap-6 text-sm">
                  <div className="space-y-2.5">
                    <p className="text-xs font-semibold uppercase tracking-wider text-zinc-600">Instrument</p>
                    {([
                      ['Manufacturer', prd.instrument?.manufacturer],
                      ['Model',        prd.instrument?.model],
                      ['Software',     prd.instrument?.software],
                    ] as [string, string | null | undefined][]).filter(([, v]) => v).map(([k, v]) => (
                      <div key={k} className="flex justify-between gap-4">
                        <span className="text-zinc-500">{k}</span>
                        <span className="font-mono text-zinc-100">{v}</span>
                      </div>
                    ))}
                  </div>
                  <div className="space-y-2.5">
                    <p className="text-xs font-semibold uppercase tracking-wider text-zinc-600">Experiment</p>
                    {([
                      ['Detection',  prd.experiment?.detection_method],
                      ['Wavelength', prd.measurement_settings?.measurement_wavelength_nm ? `${prd.measurement_settings.measurement_wavelength_nm} nm` : null],
                      ['Date',       prd.experiment?.read_date],
                      ['Wells',      String(wells.length)],
                    ] as [string, string | null | undefined][]).filter(([, v]) => v).map(([k, v]) => (
                      <div key={k} className="flex justify-between gap-4">
                        <span className="text-zinc-500">{k}</span>
                        <span className="font-mono text-zinc-100">{v}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {tab === 'wells' && (
                wells.length > 0
                  ? <WellsTable wells={wells} />
                  : <p className="text-zinc-500 text-sm">No wells in output.</p>
              )}

              {tab === 'json' && (
                <pre className="bg-zinc-950 border border-zinc-800 rounded-lg p-4 overflow-auto max-h-[420px] text-xs font-mono text-zinc-300 leading-relaxed">
                  {JSON.stringify(runResult.output_json, null, 2)}
                </pre>
              )}
            </div>
          </div>
        )}
      </main>
    </div>
  )
}
