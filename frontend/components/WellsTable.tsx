'use client'

import { useState } from 'react'
import type { Well } from '@/lib/api'

type SortKey = keyof Well
type SortDir = 'asc' | 'desc'

const ROLE_STYLES: Record<string, string> = {
  sample:  'bg-green-500/20 text-green-300',
  blank:   'bg-blue-500/20 text-blue-300',
  control: 'bg-yellow-500/20 text-yellow-300',
  unknown: 'bg-zinc-700/50 text-zinc-400',
}

export function WellsTable({ wells }: { wells: Well[] }) {
  const [sortKey, setSortKey] = useState<SortKey>('well_position')
  const [sortDir, setSortDir] = useState<SortDir>('asc')

  function toggleSort(key: SortKey) {
    if (sortKey === key) {
      setSortDir(d => (d === 'asc' ? 'desc' : 'asc'))
    } else {
      setSortKey(key)
      setSortDir('asc')
    }
  }

  const sorted = [...wells].sort((a, b) => {
    const av = a[sortKey] ?? ''
    const bv = b[sortKey] ?? ''
    const cmp = av < bv ? -1 : av > bv ? 1 : 0
    return sortDir === 'asc' ? cmp : -cmp
  })

  function Col({ label, k }: { label: string; k: SortKey }) {
    const active = sortKey === k
    return (
      <th
        onClick={() => toggleSort(k)}
        className="px-3 py-2 text-left text-xs font-semibold text-zinc-500 cursor-pointer hover:text-zinc-300 select-none whitespace-nowrap"
      >
        {label}{active ? (sortDir === 'asc' ? ' ↑' : ' ↓') : ''}
      </th>
    )
  }

  return (
    <div className="overflow-auto max-h-96 rounded-lg border border-zinc-800">
      <table className="w-full text-sm">
        <thead className="bg-zinc-900 sticky top-0 z-10">
          <tr>
            <Col label="Well" k="well_position" />
            <Col label="Row" k="row" />
            <Col label="Col" k="column" />
            <Col label="Value" k="raw_value" />
            <Col label="Unit" k="unit" />
            <Col label="Role" k="well_role" />
          </tr>
        </thead>
        <tbody>
          {sorted.map((w, i) => (
            <tr key={i} className="border-t border-zinc-800/60 hover:bg-zinc-800/30 transition-colors">
              <td className="px-3 py-1.5 font-mono font-bold text-green-400">{w.well_position}</td>
              <td className="px-3 py-1.5 font-mono text-zinc-300">{w.row}</td>
              <td className="px-3 py-1.5 font-mono text-zinc-300">{w.column}</td>
              <td className="px-3 py-1.5 font-mono text-zinc-100 tabular-nums">{w.raw_value}</td>
              <td className="px-3 py-1.5 text-zinc-400">{w.unit}</td>
              <td className="px-3 py-1.5">
                {w.well_role && (
                  <span className={`text-xs px-2 py-0.5 rounded-full ${ROLE_STYLES[w.well_role] ?? ROLE_STYLES.unknown}`}>
                    {w.well_role}
                  </span>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
