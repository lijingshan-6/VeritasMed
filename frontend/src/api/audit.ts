import { api } from './client'

export type Strategy = 'direct' | 'split' | 'context'
export type Span = { start: number; end: number; text: string }
export type Source = { id: string; title: string; text: string }
export type AuditInput = { answer: string; sources: Source[]; strategy: Strategy }
export type AuditClaim = {
  id: string; quote: string; relation: 'supported' | 'contradicted' | 'insufficient' | null
  status: string; explanation: string; answer_span: Span | null
  context_span?: Span | null
  evidence: (Span & { source_id: string; source_sha256: string })[]
}
export type AuditRecord = {
  input: AuditInput; mode: 'saved' | 'live'; provenance: { note: string; response_id?: string; run?: string; handoff?: import('./auditHandoff').AuditHandoff; input_edited?: boolean }
  audit: {
    id: string; status: string; created_utc: string; strategy: Strategy; elapsed_seconds: number
    claims: AuditClaim[]; summary: Record<string, number>; claims_at_cap: boolean
    meta_text?: { id: string; quote: string; kind: string; status: string; explanation: string; answer_span: Span | null }[]
    presentation_counts?: { full_answer_whitespace_tokens: number; rule: string }
    answer_sha256: string; source_hashes: Record<string, string>
    checked_coverage: { covered_nonspace_characters: number; total_nonspace_characters: number; uncovered: Span[] }
    calls: { stage: string; status: string; elapsed_seconds: number; usage: { total_tokens?: number } | null
      transport_metadata?: { model_identifiers?: string[] }; error_type?: string }[]
  }
}
export type Catalogue = { examples: { id: string; strategies: Partial<Record<Strategy, string>> }[]; sources_downloaded: boolean }
export async function auditExamples(): Promise<Catalogue> { return (await api.get('/api/audit/examples')).data }
export async function replayAudit(id: string, strategy: Strategy): Promise<AuditRecord> {
  return (await api.get(`/api/audit/examples/${encodeURIComponent(id)}`, { params: { strategy } })).data
}
export async function runAudit(input: AuditInput): Promise<AuditRecord> { return (await api.post('/api/audit', input)).data }
