// Retrieved source passages for the selected answer, numbered in citation order.
import React, { useState } from 'react'
import { useStore } from '../store'
import { fetchChunk } from '../api/client'
import type { ChunkOut, ChunkContextResponse } from '../types'

const CITE_VARS = ['--c0', '--c1', '--c2', '--c3', '--c4', '--c5', '--c6', '--c7']

function HighlightedText({ text, ranges }: { text: string; ranges: [number, number][] }) {
  if (!ranges?.length) return <>{text}</>
  const out: React.ReactNode[] = []
  let cur = 0
  for (const [a, b] of [...ranges].sort((x, y) => x[0] - y[0])) {
    if (a > cur) out.push(<span key={cur}>{text.slice(cur, a)}</span>)
    out.push(<mark key={`m${a}`} className="vm-highlight">{text.slice(a, b)}</mark>)
    cur = b
  }
  if (cur < text.length) out.push(<span key={cur}>{text.slice(cur)}</span>)
  return <>{out}</>
}

function Context({ chunkId }: { chunkId: string }) {
  const [open, setOpen] = useState(false)
  const [ctx, setCtx] = useState<ChunkContextResponse | null>(null)
  const [loading, setLoading] = useState(false)
  async function toggle(e: React.MouseEvent) {
    e.stopPropagation()
    if (!open && !ctx) {
      setLoading(true)
      try { setCtx(await fetchChunk(chunkId, 1)) } catch { /* shown as unavailable */ } finally { setLoading(false) }
    }
    setOpen(v => !v)
  }
  return <>
    <button className="ws-source-link" onClick={toggle}>{loading ? 'Loading…' : open ? 'Hide surrounding text' : 'Surrounding text'}</button>
    {open && <div className="ws-source-context">
      {ctx?.prev_chunk && <p><span>Before</span>{ctx.prev_chunk.text.slice(0, 320)}…</p>}
      {ctx?.next_chunk && <p><span>After</span>{ctx.next_chunk.text.slice(0, 320)}…</p>}
      {(!ctx || (!ctx.prev_chunk && !ctx.next_chunk)) && <p>No neighbouring passage.</p>}
    </div>}
  </>
}

function SourceCard({ chunk, idx, cited, isSelected, onSelect }: {
  chunk: ChunkOut; idx: number; cited: boolean; isSelected: boolean; onSelect: (id: string) => void
}) {
  const colorVar = CITE_VARS[idx % CITE_VARS.length]
  const ref = React.useRef<HTMLElement>(null)
  React.useEffect(() => { if (isSelected) ref.current?.scrollIntoView({ behavior: 'smooth', block: 'nearest' }) }, [isSelected])
  const meta = chunk as ChunkOut & { journal?: string; year?: number }
  return <article ref={ref} id={`chunk-${chunk.chunk_id}`} onClick={() => onSelect(chunk.chunk_id)}
    className={`ws-source${isSelected ? ' is-selected' : ''}${cited ? '' : ' is-uncited'}`} style={{ '--cite-color': `var(${colorVar})` } as React.CSSProperties}>
    <header>
      <span className="ws-source-num">{cited ? idx + 1 : '–'}</span>
      <div>
        <h3>{chunk.title}</h3>
        <p className="ws-source-meta">{[chunk.citation, meta.journal, meta.year, chunk.section].filter(Boolean).join(' · ')}</p>
      </div>
    </header>
    <p className="ws-source-text"><HighlightedText text={chunk.text} ranges={chunk.highlight_ranges ?? []} /></p>
    <footer>
      <Context chunkId={chunk.chunk_id} />
      {chunk.external_url && <a className="ws-source-link" href={chunk.external_url} target="_blank" rel="noopener noreferrer" onClick={e => e.stopPropagation()}>Open paper ↗</a>}
    </footer>
  </article>
}

export function EvidencePanel() {
  const { result, liveChunks, selectedChunkId, setSelectedChunkId, isStreaming } = useStore()
  const rawChunks = result?.chunks?.length ? result.chunks : liveChunks
  const chunks = Array.from(new Map(rawChunks.map(c => [c.chunk_id, c])).values())
  const cited = result?.citations ?? []
  const order = [...cited]
  for (const chunk of chunks) if (!order.includes(chunk.citation)) order.push(chunk.citation)
  const papers = new Set(chunks.map(c => c.citation)).size

  return <aside className="ws-sources">
    <header className="ws-sources-head">
      <h2>Sources</h2>
      {chunks.length > 0 && <span>{chunks.length} passages from {papers} {papers === 1 ? 'paper' : 'papers'}</span>}
    </header>
    {!chunks.length && !isStreaming && <p className="ws-sources-empty">Passages retrieved for an answer appear here, numbered as they are cited.</p>}
    <div className="ws-sources-list">
      {chunks.map(chunk => <SourceCard key={chunk.chunk_id} chunk={chunk} idx={order.indexOf(chunk.citation)}
        cited={cited.length === 0 || cited.includes(chunk.citation)} isSelected={selectedChunkId === chunk.chunk_id}
        onSelect={id => setSelectedChunkId(selectedChunkId === id ? null : id)} />)}
      {isStreaming && <p className="ws-sources-empty">Retrieving passages…</p>}
    </div>
  </aside>
}
