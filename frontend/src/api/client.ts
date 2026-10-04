import axios from 'axios'
import { isReplayOnly } from '../demo'
import { replayChunk, replayDocument } from '../replay/corpus'
import type { ChunkContextResponse, CorpusStats, DocumentResponse } from '../types'

// Dev options (pick one):
//   A) frontend/.env.local  →  VITE_API_URL=http://localhost:8000  (direct to FastAPI)
//   B) leave unset          →  Vite proxies /api to :8000 (see vite.config.ts)
const BASE = (import.meta.env.VITE_API_URL as string) ?? ''

export const api = axios.create({ baseURL: BASE })

export async function fetchDocument(citation: string): Promise<DocumentResponse> {
  if (isReplayOnly) return replayDocument(citation)
  const r = await api.get(`/api/document/${encodeURIComponent(citation)}`)
  return r.data
}

export async function fetchChunk(
  chunkId: string,
  contextWindow = 1,
): Promise<ChunkContextResponse> {
  if (isReplayOnly) return replayChunk(chunkId, contextWindow)
  const r = await api.get(`/api/chunk/${encodeURIComponent(chunkId)}`, {
    params: { context_window: contextWindow },
  })
  return r.data
}

export async function fetchCorpusStats(): Promise<CorpusStats> {
  const r = await api.get('/api/corpus/stats')
  return r.data
}

export async function fetchHealth(): Promise<{ status: string; qdrant: string; llm: string }> {
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
