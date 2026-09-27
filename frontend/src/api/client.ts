import { isGuidedDemo, demoChunks } from '../demo'
import axios from 'axios'
import type { ChunkContextResponse, CorpusStats, DocumentResponse, SearchResponse } from '../types'

// Dev options (pick one):
//   A) frontend/.env.local  →  VITE_API_URL=http://localhost:8000  (direct to FastAPI)
//   B) leave unset          →  Vite proxies /api to :8000 (see vite.config.ts)
const BASE = (import.meta.env.VITE_API_URL as string) ?? ''

export const api = axios.create({ baseURL: BASE })

export async function fetchSearch(
  q: string,
  k = 5,
  pipeline: 'p2' | 'p3' = 'p2',
  highlight = true,
): Promise<SearchResponse> {
  if (isGuidedDemo) return { query: q, pipeline: 'preset', latency_ms: 0, chunks: demoChunks.filter(c => q.toLowerCase().split(/\s+/).some(word => c.text.toLowerCase().includes(word))).slice(0, k) }
  const r = await api.get('/api/search', { params: { q, k, pipeline, highlight } })
  return r.data
}

export async function fetchDocument(citation: string): Promise<DocumentResponse> {
  if (isGuidedDemo) {
    const chunks = demoChunks.filter(c => c.citation === citation)
    if (!chunks.length) throw new Error('Document is not part of the guided demo.')
    return { ...chunks[0], pmid: chunks[0].pmid ?? null, total_chunks: chunks.length, chunks }
  }
  const r = await api.get(`/api/document/${encodeURIComponent(citation)}`)
  return r.data
}

export async function fetchChunk(
  chunkId: string,
  contextWindow = 1,
): Promise<ChunkContextResponse> {
  if (isGuidedDemo) {
    const chunk = demoChunks.find(c => c.chunk_id === chunkId)
    if (!chunk) throw new Error('Passage is not part of the guided demo.')
    return { chunk, prev_chunk: null, next_chunk: null, document: { title: chunk.title, citation: chunk.citation, external_url: chunk.external_url } }
  }
  const r = await api.get(`/api/chunk/${encodeURIComponent(chunkId)}`, {
    params: { context_window: contextWindow },
  })
  return r.data
}

export async function fetchCorpusStats(): Promise<CorpusStats> {
  if (isGuidedDemo) return { total_chunks: 3, pubmed_chunks: 0, pmc_chunks: 3, collection: 'guided_demo', embedding_model: 'fixed examples' }
  const r = await api.get('/api/corpus/stats')
  return r.data
}

export async function fetchHealth(): Promise<{ status: string; qdrant: string; llm: string }> {
  if (isGuidedDemo) return { status: 'demo', qdrant: 'not used', llm: 'not used' }
  const r = await api.get('/api/health')
  return r.data
}

// ── WebSocket URL helper ──────────────────────────────────────────────────

export function wsAskUrl(): string {
  const apiBase = (import.meta.env.VITE_API_URL as string) ?? ''
  if (apiBase) {
    // Convert http(s):// to ws(s)://
    return apiBase.replace(/^http/, 'ws') + '/api/ask'
  }
  // Production: derive from current page origin
  const proto = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  return `${proto}//${window.location.host}/api/ask`
}
