'use client'

import Link from 'next/link'
import {
  ArrowRight, Bot, FileUp, FileText, Search, Globe, Code2, Database,
  Microscope, Atom, Dna, Activity, FlaskConical, Clock, Wrench, Repeat,
  BookOpen,
} from 'lucide-react'
import { Nav } from '@/components/Nav'

const AGENT_STEPS = [
  { Icon: Search, title: 'Identify',  desc: 'Reads the file and recognises the instrument and read type.' },
  { Icon: Globe,  title: 'Research',  desc: 'Searches the web and your uploaded docs for the exact export format.' },
  { Icon: Code2,  title: 'Generate',  desc: 'Writes a Python parser, runs it in a sandbox, and self-corrects on failure.' },
  { Icon: Database, title: 'Extract', desc: 'Returns clean structured JSON and saves the parser for instant reuse.' },
]

const INSTRUMENTS = [
  { Icon: Microscope, name: 'Plate Readers',     status: 'live', href: '/plate-reader', desc: 'Any vendor, any format — BioTek, Molecular Devices, Tecan, PerkinElmer & more.' },
  { Icon: Atom,       name: 'Mass Spectrometry', status: 'soon', href: null, desc: 'Spectra, peak lists, and quantitation exports.' },
  { Icon: Dna,        name: 'qPCR',              status: 'soon', href: null, desc: 'Amplification curves, Ct values, and plate layouts.' },
  { Icon: Activity,   name: 'Chromatography',    status: 'soon', href: null, desc: 'HPLC / GC traces, retention times, and areas.' },
]

export default function Landing() {
  return (
    <div className="min-h-screen bg-zinc-950">
      <Nav />

      {/* Hero */}
      <section className="relative overflow-hidden">
        <div className="absolute inset-0 bg-[radial-gradient(60%_50%_at_50%_0%,rgba(34,197,94,0.12),transparent)]" />
        <div className="relative max-w-4xl mx-auto px-4 pt-20 pb-16 text-center">
          <span className="inline-flex items-center gap-1.5 text-xs font-medium px-3 py-1 rounded-full bg-green-500/10 text-green-400 border border-green-500/20">
            <Bot className="w-3.5 h-3.5" /> An AI agent for instrument data
          </span>
          <h1 className="mt-6 text-4xl sm:text-5xl font-bold tracking-tight text-zinc-50 leading-[1.1]">
            An agent that turns <span className="text-green-400">any instrument&apos;s data</span><br className="hidden sm:block" />
            into structured, usable format.
          </h1>
          <p className="mt-5 text-lg text-zinc-400 max-w-2xl mx-auto">
            Not a fixed set of rules — a reasoning agent. Hand it a sample export and the instrument&apos;s
            documentation; it researches the format, writes its own parser, tests it, and gives you clean data.
          </p>
          <div className="mt-8 flex items-center justify-center gap-3 flex-wrap">
            <Link
              href="/plate-reader"
              className="inline-flex items-center gap-2 px-5 py-2.5 rounded-lg font-semibold text-sm bg-green-500 text-black hover:bg-green-400 transition-colors"
            >
              Try the Plate Reader demo <ArrowRight className="w-4 h-4" />
            </Link>
            <Link
              href="/docs"
              className="inline-flex items-center gap-2 px-5 py-2.5 rounded-lg font-semibold text-sm border border-zinc-700 text-zinc-200 hover:bg-zinc-800 transition-colors"
            >
              <BookOpen className="w-4 h-4" /> Read the docs
            </Link>
          </div>
        </div>
      </section>

      {/* The problem */}
      <section className="max-w-5xl mx-auto px-4 py-12">
        <div className="text-center mb-8">
          <h2 className="text-2xl font-bold text-zinc-100">The problem today</h2>
          <p className="text-sm text-zinc-500 mt-1 max-w-2xl mx-auto">
            Every lab instrument exports data in its own quirky layout. Getting it into a usable
            shape is a recurring engineering tax.
          </p>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          {[
            { Icon: Wrench, title: 'Outsourced to engineering', desc: 'Scientists hand files to a dev team to hand-write a custom parsing script for each instrument and format.' },
            { Icon: Clock,  title: 'Slow and expensive',        desc: 'Every new instrument, firmware update, or export tweak means another ticket, another sprint, another script.' },
            { Icon: Repeat, title: 'Brittle and one-off',       desc: 'Scripts break on edge cases — negative values, multi-row blocks, odd delimiters — and nobody owns them long-term.' },
          ].map(({ Icon, title, desc }) => (
            <div key={title} className="bg-zinc-900 border border-zinc-800 rounded-xl p-5">
              <div className="w-10 h-10 rounded-lg bg-red-500/10 flex items-center justify-center mb-3">
                <Icon className="w-5 h-5 text-red-400" />
              </div>
              <p className="font-semibold text-zinc-200">{title}</p>
              <p className="text-sm text-zinc-500 mt-1 leading-relaxed">{desc}</p>
            </div>
          ))}
        </div>
        <p className="text-center text-zinc-300 mt-8 max-w-2xl mx-auto">
          With this agent, there&apos;s no script to commission. You just <span className="text-green-400 font-medium">throw in
          the files</span> — the instrument&apos;s docs and a sample export — and the agent does the rest.
        </p>
      </section>

      {/* What you give it / what it does */}
      <section className="max-w-5xl mx-auto px-4 py-12">
        <div className="text-center mb-8">
          <h2 className="text-2xl font-bold text-zinc-100">What you give it</h2>
          <p className="text-sm text-zinc-500 mt-1">Two inputs in, structured data out.</p>
        </div>
        <div className="flex flex-col sm:flex-row items-stretch justify-center gap-3">
          <div className="flex-1 bg-zinc-900 border border-zinc-800 rounded-xl p-5">
            <FileUp className="w-5 h-5 text-green-400 mb-2" />
            <p className="font-semibold text-zinc-200">A sample export file</p>
            <p className="text-sm text-zinc-500 mt-1">The raw CSV/TXT your instrument produces.</p>
          </div>
          <div className="flex-1 bg-zinc-900 border border-zinc-800 rounded-xl p-5">
            <FileText className="w-5 h-5 text-green-400 mb-2" />
            <p className="font-semibold text-zinc-200">Instrument docs <span className="text-zinc-600 font-normal">(optional)</span></p>
            <p className="text-sm text-zinc-500 mt-1">A manual or format spec PDF. No docs? The agent web-searches instead.</p>
          </div>
          <div className="flex items-center justify-center text-zinc-600">
            <ArrowRight className="w-6 h-6 rotate-90 sm:rotate-0" />
          </div>
          <div className="flex-1 bg-green-500/5 border border-green-500/30 rounded-xl p-5">
            <Database className="w-5 h-5 text-green-400 mb-2" />
            <p className="font-semibold text-zinc-100">Structured JSON</p>
            <p className="text-sm text-zinc-400 mt-1">Clean, schema-validated data — plus a reusable parser.</p>
          </div>
        </div>

        {/* Agent workflow */}
        <div className="mt-10">
          <p className="text-center text-xs font-semibold uppercase tracking-wider text-zinc-600 mb-4">
            What the agent does, autonomously
          </p>
          <div className="grid grid-cols-1 sm:grid-cols-4 gap-3">
            {AGENT_STEPS.map(({ Icon, title, desc }, i) => (
              <div key={title} className="bg-zinc-900 border border-zinc-800 rounded-xl p-4">
                <div className="flex items-center gap-2 mb-2">
                  <div className="w-8 h-8 rounded-lg bg-green-500/10 flex items-center justify-center">
                    <Icon className="w-4 h-4 text-green-400" />
                  </div>
                  <span className="text-[10px] font-mono text-zinc-600">{String(i + 1).padStart(2, '0')}</span>
                </div>
                <p className="text-sm font-semibold text-zinc-200">{title}</p>
                <p className="text-xs text-zinc-500 mt-1 leading-relaxed">{desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Instruments */}
      <section className="max-w-5xl mx-auto px-4 py-12">
        <div className="text-center mb-8">
          <h2 className="text-2xl font-bold text-zinc-100">Supported instruments</h2>
          <p className="text-sm text-zinc-500 mt-1">
            Plate readers are live today. The same agent extends to more instrument classes next.
          </p>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          {INSTRUMENTS.map(({ Icon, name, status, href, desc }) => {
            const live = status === 'live'
            const inner = (
              <div className={`h-full bg-zinc-900 border rounded-xl p-5 transition-colors ${
                live ? 'border-green-500/30 hover:border-green-500/60' : 'border-zinc-800 opacity-70'
              }`}>
                <div className="flex items-start justify-between">
                  <div className={`w-11 h-11 rounded-xl flex items-center justify-center ${live ? 'bg-green-500/10' : 'bg-zinc-800'}`}>
                    <Icon className={`w-5 h-5 ${live ? 'text-green-400' : 'text-zinc-500'}`} />
                  </div>
                  <span className={`text-[10px] font-semibold uppercase tracking-wider px-2 py-1 rounded-full ${
                    live ? 'bg-green-500/15 text-green-400' : 'bg-zinc-800 text-zinc-500'
                  }`}>
                    {live ? 'Live' : 'Coming soon'}
                  </span>
                </div>
                <h3 className="mt-4 font-semibold text-zinc-100 flex items-center gap-1.5">
                  {name}
                  {live && <ArrowRight className="w-4 h-4 text-green-400" />}
                </h3>
                <p className="text-sm text-zinc-500 mt-1 leading-relaxed">{desc}</p>
              </div>
            )
            return href ? (
              <Link key={name} href={href} className="block">{inner}</Link>
            ) : (
              <div key={name}>{inner}</div>
            )
          })}
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-zinc-800 mt-8">
        <div className="max-w-5xl mx-auto px-4 py-8 flex items-center justify-between text-sm text-zinc-500 flex-wrap gap-3">
          <span className="flex items-center gap-2">
            <FlaskConical className="w-4 h-4 text-green-400" />
            InstrumentParser
          </span>
          <div className="flex items-center gap-4">
            <Link href="/docs" className="hover:text-zinc-300 transition-colors">Docs</Link>
            <Link href="/plate-reader" className="hover:text-zinc-300 transition-colors">Demo</Link>
            <span className="text-zinc-600">Dynamic AI parsing · more instruments coming</span>
          </div>
        </div>
      </footer>
    </div>
  )
}
