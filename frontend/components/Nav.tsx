'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { FlaskConical, Microscope, Library, BookOpen } from 'lucide-react'

const LINKS = [
  { href: '/plate-reader', label: 'Plate Reader', icon: Microscope },
  { href: '/parsers',      label: 'Parser Library', icon: Library },
  { href: '/docs',         label: 'Docs', icon: BookOpen },
]

export function Nav() {
  const pathname = usePathname()

  return (
    <header className="sticky top-0 z-40 bg-zinc-900/80 backdrop-blur border-b border-zinc-800">
      <div className="max-w-6xl mx-auto px-4 h-14 flex items-center gap-6">
        <Link href="/" className="flex items-center gap-2 font-bold tracking-tight text-zinc-100 hover:text-white transition-colors">
          <FlaskConical className="w-5 h-5 text-green-400" />
          <span>Instrument<span className="text-green-400">Parser</span></span>
        </Link>
        <nav className="flex gap-1">
          {LINKS.map(({ href, label, icon: Icon }) => {
            const active = pathname === href || pathname.startsWith(href + '/')
            return (
              <Link
                key={href}
                href={href}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-sm font-medium transition-colors ${
                  active
                    ? 'bg-zinc-800 text-zinc-100'
                    : 'text-zinc-500 hover:text-zinc-200 hover:bg-zinc-800/60'
                }`}
              >
                <Icon className="w-4 h-4" />
                {label}
              </Link>
            )
          })}
        </nav>
      </div>
    </header>
  )
}
