import type React from 'react'
import { CITE_VARS } from './Icons'

export function StreamingCaret() {
  return (
    <span style={{
      display: 'inline-block', width: 8, height: '0.95em',
      verticalAlign: '-0.1em',
      background: 'var(--accent)',
      animation: 'vmCaret 1s steps(2) infinite',
      marginLeft: 2, borderRadius: 1,
    }} />
  )
}

export function buildCiteMap(citations: string[]): Record<string, number> {
  const map: Record<string, number> = {}
  citations.forEach((c, i) => { map[c] = i })
  return map
}

export function AnnotatedParagraph({ text, citeMap, onCiteClick, isFirst }: {
  text: string
  citeMap: Record<string, number>
  onCiteClick: (c: string) => void
  isFirst: boolean
}) {
  const CITE_RE = /\[(PMID:[^\]]+|PMC:[^\]]+|DOI:[^\]]+)\]/g
  const parts: React.ReactNode[] = []
  let last = 0
  let m: RegExpExecArray | null
  while ((m = CITE_RE.exec(text)) !== null) {
    if (m.index > last) parts.push(text.slice(last, m.index))
    const citeStr = m[1]
    const idx = citeMap[citeStr]
    const colorVar = idx != null ? CITE_VARS[idx % CITE_VARS.length] : '--accent'
    parts.push(
      <span
        key={m.index}
        className="vm-cite"
        style={{ '--cite-color': `var(${colorVar})` } as React.CSSProperties}
        onClick={(e) => { e.stopPropagation(); onCiteClick(citeStr) }}
        title={citeStr}
        role="button"
        tabIndex={0}
      >
        {idx != null ? idx + 1 : '?'}
      </span>
    )
    last = m.index + m[0].length
  }
  if (last < text.length) parts.push(text.slice(last))
  return (
    <p className={isFirst ? 'vm-dropcap' : undefined}>
      {parts}
    </p>
  )
}
