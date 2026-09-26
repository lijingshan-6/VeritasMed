import { api } from './client'

export type Strategy = 'direct' | 'split' | 'context' | 'quote_v2' | 'atomic_v1'
export type Span = { start: number; end: number; text: string }
export type QuoteBinding = { status: string; match_count: number; span: Span | null; candidates: Span[]; candidates_truncated?: boolean }
export type Source = { id: string; title: string; text: string }
export type AuditInput = { answer: string; sources: Source[]; strategy: Strategy }
export type AuditClaim = {
  id: string; quote: string; relation: 'supported' | 'contradicted' | 'insufficient' | null
  status: string; explanation: string; answer_span: Span | null
  context_span?: Span | null
  context_spans?: Span[]
  answer_spans?: Span[]
  parent_claim_id?: string
  normalized_claim?: string
  decomposition_status?: string
  slots?: Record<string, string | null>
  answer_bindings?: QuoteBinding[]
  parent_binding?: QuoteBinding
  evidence_bindings?: (QuoteBinding & { source_id: string; quote: string })[]
  numeric_diagnostic?: { status: string; reason?: string; scope: string; overrides_relation: boolean }
  checker_results?: Record<string, unknown>
  checker_disagreement?: boolean
  bindings?: { answer: QuoteBinding; evidence: (QuoteBinding & { source_id: string; quote: string })[] }
  evidence: (Span & { source_id: string; source_sha256: string })[]
}
export type AuditRecord = {
  input: AuditInput; mode: 'saved' | 'live'; provenance: { note: string; paper?: string; response_id?: string; run?: string; handoff?: import('./auditHandoff').AuditHandoff; input_edited?: boolean }
  audit: {
    id: string; status: string; created_utc: string; strategy: Strategy; elapsed_seconds: number
    claims: AuditClaim[]; summary: Record<string, number>; claims_at_cap: boolean
    parent_count?: number
    extraction?: { completeness_note: string } | null
    supplemental_checkers?: { judgments: number; attempts: number; elapsed_seconds: number; scope: string }
    meta_text?: { id: string; quote: string; kind: string; status: string; explanation: string; answer_span: Span | null; binding?: QuoteBinding }[]
    presentation_counts?: { full_answer_whitespace_tokens: number; rule: string }
    answer_sha256: string; source_hashes: Record<string, string>
    checked_coverage: { covered_nonspace_characters: number; total_nonspace_characters: number; uncovered: Span[] }
    calls: { stage: string; status: string; elapsed_seconds: number; usage: { total_tokens?: number } | null
      transport_metadata?: { model_identifiers?: string[] }; error_type?: string }[]
  }
}
export type Catalogue = { examples: { id: string; label: string; requires_download: boolean; strategies: Partial<Record<Strategy, string>> }[]; sources_downloaded: boolean }
export async function auditExamples(): Promise<Catalogue> { return (await api.get('/api/audit/examples')).data }
export async function replayAudit(id: string, strategy: Strategy): Promise<AuditRecord> {
  return (await api.get(`/api/audit/examples/${encodeURIComponent(id)}`, { params: { strategy } })).data
}
export async function runAudit(input: AuditInput): Promise<AuditRecord> { return (await api.post('/api/audit', input)).data }
