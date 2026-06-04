import Link from 'next/link'
import {
  Bot, Search, Globe, Code2, Save, Database, FileUp, FileText,
  ShieldCheck, Repeat, ArrowRight, Workflow, Lightbulb,
} from 'lucide-react'
import { Nav } from '@/components/Nav'

export const metadata = {
  title: 'Docs — InstrumentParser',
  description: 'How the instrument-parsing agent works: the problem it solves, its pipeline, and inputs and outputs.',
}

function Section({ id, icon: Icon, title, children }: {
  id: string; icon: typeof Bot; title: string; children: React.ReactNode
}) {
  return (
    <section id={id} className="scroll-mt-20">
      <h2 className="flex items-center gap-2 text-xl font-bold text-zinc-100">
        <Icon className="w-5 h-5 text-green-400" /> {title}
      </h2>
      <div className="mt-3 space-y-3 text-sm text-zinc-400 leading-relaxed">{children}</div>
    </section>
  )
}

const PIPELINE = [
  { Icon: Search,   name: 'Identify', text: 'The agent reads the file and works out which instrument and read type produced it — entirely from the data, with no hardcoded vendor list. If the file clearly is not a plate reader, it stops here and tells you.' },
  { Icon: Globe,    name: 'Research', text: 'It studies the format: reading the instrument documentation you uploaded, and web-searching for the export spec, delimiters, plate dimensions, and known quirks (multi-row blocks, negative blank-corrected values, value qualifiers like > and <).' },
  { Icon: Code2,    name: 'Generate', text: 'It writes a self-contained Python parser, runs it in a locked-down sandbox, validates the output against the schema, and — if anything fails — feeds the error back to itself and retries until it is correct.' },
  { Icon: Save,     name: 'Save',     text: 'The working parser is versioned in the library, keyed to that instrument and read type, so it can be reused instantly.' },
  { Icon: Database, name: 'Extract',  text: 'It returns clean, schema-validated JSON — instrument metadata, experiment settings, and every well with its raw value, blank-corrected value, and concentration.' },
]

export default function DocsPage() {
  return (
    <div className="min-h-screen bg-zinc-950">
      <Nav />

      <main className="max-w-3xl mx-auto px-4 py-10 space-y-12">
        {/* Intro */}
        <div>
          <span className="inline-flex items-center gap-1.5 text-xs font-medium px-3 py-1 rounded-full bg-green-500/10 text-green-400 border border-green-500/20">
            <Bot className="w-3.5 h-3.5" /> Documentation
          </span>
          <h1 className="mt-4 text-3xl font-bold text-zinc-50">What InstrumentParser is</h1>
          <p className="mt-3 text-zinc-400 leading-relaxed">
            InstrumentParser is an <span className="text-zinc-200 font-medium">AI agent</span> that converts raw
            lab-instrument exports into clean, structured data. It is not a fixed set of parsing rules — it reasons
            about each file: identifying the instrument, researching its export format, writing its own parser,
            testing that parser, and extracting the data. Today it handles <span className="text-zinc-200">plate readers</span>;
            the same agent is designed to extend to other instrument classes.
          </p>
        </div>

        <Section id="problem" icon={Repeat} title="The problem it solves">
          <p>
            Every instrument exports data in its own idiosyncratic layout — different delimiters, header blocks,
            multi-row well sections, and edge cases. Traditionally, getting that data into a usable shape means
            <span className="text-zinc-200"> outsourcing to an engineering team</span> to hand-write a custom parsing
            script for each instrument and each format.
          </p>
          <p>
            That is slow, expensive, and brittle. Every new instrument, firmware update, or export change means
            another ticket and another one-off script that someone has to maintain. Scientists wait on engineers
            to do something that isn&apos;t really science.
          </p>
          <p>
            With this agent there is <span className="text-green-400 font-medium">no script to commission</span>. You
            throw in the files — the instrument&apos;s documentation and a sample export — and the agent produces both
            the structured data and a reusable parser.
          </p>
        </Section>

        <Section id="inputs" icon={FileUp} title="What you provide, what you get">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 not-prose">
            <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-4">
              <FileUp className="w-5 h-5 text-green-400 mb-2" />
              <p className="font-semibold text-zinc-200">Sample export file</p>
              <p className="text-zinc-500 mt-1">The raw CSV/TXT your instrument produces. Required.</p>
            </div>
            <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-4">
              <FileText className="w-5 h-5 text-green-400 mb-2" />
              <p className="font-semibold text-zinc-200">Instrument documentation</p>
              <p className="text-zinc-500 mt-1">A manual or format spec PDF. Optional — without it, the agent web-searches the format.</p>
            </div>
          </div>
          <p className="flex items-center gap-2 text-zinc-300">
            <ArrowRight className="w-4 h-4 text-green-400" />
            You get back schema-validated JSON <span className="text-zinc-500">and</span> a saved, reusable parser.
          </p>
        </Section>

        <Section id="pipeline" icon={Workflow} title="How the agent works">
          <p>Every file runs through a five-stage pipeline. You can watch it live in the demo and click any stage for its summary and logs.</p>
          <div className="space-y-2 not-prose mt-2">
            {PIPELINE.map(({ Icon, name, text }, i) => (
              <div key={name} className="flex gap-3 bg-zinc-900 border border-zinc-800 rounded-xl p-4">
                <div className="w-9 h-9 rounded-lg bg-green-500/10 flex items-center justify-center flex-shrink-0">
                  <Icon className="w-4 h-4 text-green-400" />
                </div>
                <div>
                  <p className="font-semibold text-zinc-200">
                    <span className="text-zinc-600 font-mono text-xs mr-2">{String(i + 1).padStart(2, '0')}</span>
                    {name}
                  </p>
                  <p className="text-zinc-500 mt-0.5">{text}</p>
                </div>
              </div>
            ))}
          </div>
        </Section>

        <Section id="reuse" icon={Save} title="Generate once, reuse forever">
          <p>
            The first time the agent sees an instrument, it does the full research-and-generate work. The resulting
            parser is saved to the <Link href="/parsers" className="text-green-400 hover:underline">Parser Library</Link>,
            keyed to that instrument and read type.
          </p>
          <p>
            On every later file from the same instrument, the agent skips straight to running that saved parser —
            <span className="text-zinc-200"> deterministic, instant, and with zero AI cost</span>. The expensive
            reasoning happens once; the payoff repeats forever.
          </p>
        </Section>

        <Section id="privacy" icon={ShieldCheck} title="Privacy">
          <p>
            Inference runs on a <span className="text-zinc-200">privacy-focused private AI provider</span> — your
            instrument data is processed with private inference, not handed to a general public model API. The
            inference layer can be <span className="text-zinc-200">moved into a Trusted Execution Environment (TEE)
            on demand</span>, so sensitive lab data is processed inside hardware-isolated enclaves when required.
          </p>
        </Section>

        <Section id="safety" icon={ShieldCheck} title="Safety & correctness">
          <ul className="list-disc pl-5 space-y-1.5 marker:text-zinc-600">
            <li>Generated parsers run in a restricted sandbox — no network, no filesystem, no shell.</li>
            <li>Untrusted file content is fenced off so it can&apos;t be used to steer the agent.</li>
            <li>Output is validated against a strict schema, including a plate-consistency check (well counts and positions must match the declared plate format).</li>
            <li>If validation fails, the agent self-corrects and retries rather than returning bad data.</li>
          </ul>
        </Section>

        <Section id="scope" icon={Lightbulb} title="Current scope">
          <p>
            Today the agent is focused on <span className="text-zinc-200">plate readers</span> — any vendor, any
            format. It rejects files that clearly come from other instrument types rather than forcing them into a
            shape that doesn&apos;t fit. The architecture, however, is general: adding a new instrument class is a
            matter of giving the agent a new output schema to target.
          </p>
        </Section>

        {/* CTA */}
        <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-6 text-center">
          <p className="text-zinc-200 font-semibold">Ready to see it work?</p>
          <p className="text-sm text-zinc-500 mt-1">Upload a plate reader export and watch the agent build a parser live.</p>
          <Link
            href="/plate-reader"
            className="mt-4 inline-flex items-center gap-2 px-5 py-2.5 rounded-lg font-semibold text-sm bg-green-500 text-black hover:bg-green-400 transition-colors"
          >
            Open the Plate Reader demo <ArrowRight className="w-4 h-4" />
          </Link>
        </div>
      </main>
    </div>
  )
}
