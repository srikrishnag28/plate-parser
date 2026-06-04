'use client'

import { useCallback, useState, useRef } from 'react'

interface DropZoneProps {
  label: string
  hint: string
  accept: string
  file: File | null
  onFile: (f: File) => void
  onClear: () => void
  icon?: string
}

export function DropZone({ label, hint, accept, file, onFile, onClear, icon = '📄' }: DropZoneProps) {
  const [dragging, setDragging] = useState(false)
  const inputRef = useRef<HTMLInputElement>(null)
  const pickerOpen = useRef(false)

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault()
      setDragging(false)
      const f = e.dataTransfer.files[0]
      if (f) onFile(f)
    },
    [onFile],
  )

  if (file) {
    return (
      <div className="border-2 border-green-500 rounded-xl p-5 text-center bg-green-500/5 flex flex-col items-center gap-2">
        <span className="text-green-400 text-xl">✓</span>
        <p className="text-green-300 font-mono text-xs break-all max-w-full px-2">{file.name}</p>
        <button
          onClick={onClear}
          className="text-xs text-zinc-500 hover:text-red-400 border border-zinc-700 hover:border-red-500 rounded px-2 py-0.5 transition-colors"
        >
          Remove
        </button>
      </div>
    )
  }

  return (
    <div
      onClick={() => {
        if (pickerOpen.current) return
        pickerOpen.current = true
        inputRef.current?.click()
      }}
      onDragOver={(e) => { e.preventDefault(); setDragging(true) }}
      onDragLeave={() => setDragging(false)}
      onDrop={handleDrop}
      className={`border-2 border-dashed rounded-xl p-5 text-center cursor-pointer transition-colors min-h-[110px] flex flex-col items-center justify-center gap-2 ${
        dragging
          ? 'border-green-400 bg-green-400/5'
          : 'border-zinc-700 hover:border-zinc-500'
      }`}
    >
      <span className="text-2xl">{icon}</span>
      <p className="font-medium text-zinc-200 text-sm">{label}</p>
      <p className="text-xs text-zinc-500">{hint}</p>
      <input
        ref={inputRef}
        type="file"
        accept={accept}
        className="hidden"
        onChange={(e) => {
          pickerOpen.current = false
          const f = e.target.files?.[0]
          if (f) onFile(f)
          e.target.value = ''
        }}
        onClick={(e) => e.stopPropagation()}
      />
    </div>
  )
}
