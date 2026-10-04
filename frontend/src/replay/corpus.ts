// Read-only replay without a backend: the bundled corpus and recorded conversations are
// static JSON (see scripts/prepare-replay.mjs). These helpers mirror the live API responses.
import type { ChunkContextResponse, DocumentResponse } from '../types'

export type CorpusRow = {
  chunk_id: string; doc_id: string; pmid?: string; source: string; title: string; section?: string
  chunk_idx: number; total_chunks: number; text: string; source_url: string
}
export type CatalogueEntry = { id: string; label: string; file: string; turns: number; description: string }

const slim = (row: CorpusRow | undefined) => row ? { chunk_id: row.chunk_id, text: row.text, score: null } : null

export function chunkContext(rows: CorpusRow[], chunkId: string, contextWindow = 1): ChunkContextResponse {
  const byId = new Map(rows.map(r => [r.chunk_id, r]))
  const row = byId.get(chunkId)
  if (!row) throw new Error('This passage is not in the bundled corpus.')
  const key = chunkId.slice(0, chunkId.lastIndexOf(':'))
  const neighbour = (index: number) => contextWindow ? slim(byId.get(`${key}:${index}`)) : null
  return {
    chunk: slim(row)!,
    prev_chunk: neighbour(row.chunk_idx - 1),
    next_chunk: neighbour(row.chunk_idx + 1),
    document: { title: row.title, citation: `PMC:${row.doc_id}`, external_url: row.source_url },
  }
}

export function documentFor(rows: CorpusRow[], citation: string): DocumentResponse {
  const docId = citation.replace(/^PMC:/, '')
  const chunks = rows.filter(r => r.doc_id === docId).sort((a, b) => a.chunk_idx - b.chunk_idx)
  if (!chunks.length) throw new Error('This document is not in the bundled corpus.')
  return {
    citation: `PMC:${docId}`, source: chunks[0].source, doc_id: docId, title: chunks[0].title,
    pmid: chunks[0].pmid ?? null, external_url: chunks[0].source_url, total_chunks: chunks.length,
    chunks: chunks.map(r => ({ chunk_id: r.chunk_id, chunk_idx: r.chunk_idx, section: r.section ?? null, text: r.text })),
  }
}

async function json<T>(path: string): Promise<T> {
  const response = await fetch(import.meta.env.BASE_URL + 'replay/' + path)
  if (!response.ok) throw new Error(`Saved replay file unavailable: ${path}`)
  return response.json()
}
let corpus: Promise<CorpusRow[]> | undefined
const rows = () => corpus ??= json<CorpusRow[]>('corpus.json')

export const replayCatalogue = () => json<CatalogueEntry[]>('catalogue.json')
export const replayConversation = (entry: CatalogueEntry) => json<unknown>(entry.file)
export const replayChunk = async (chunkId: string, contextWindow = 1) => chunkContext(await rows(), chunkId, contextWindow)
export const replayDocument = async (citation: string) => documentFor(await rows(), citation)
