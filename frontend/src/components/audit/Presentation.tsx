// Shared audit wording and exact Unicode passage rendering; no inference or state.
import type { AuditClaim, QuoteBinding, Span, Strategy } from '../../api/audit'
import type { AuditHandoff } from '../../api/auditHandoff'

export const labels: Record<string, string> = {
  supported: 'Supported', contradicted: 'Contradicted', insufficient: 'Insufficient evidence',
  invalid_reference: 'Unresolved quote', invalid_output: 'Invalid model output',
  ambiguous_reference: 'Repeated quote · location unresolved',
  execution_error: 'Execution failed', not_checked: 'Not checked',
  needs_review: 'Needs review · parsing unresolved',
  not_source_checked: 'Presentation text · not source-checked',
}
export const methodLabels: Record<string, string> = { direct: 'Direct Flash', atomic_v2: 'Atomic v2 · qualifier anchors · experimental',
  // Labels for runs saved by retired methods, which can still appear in imported conversations.
  split: 'Extract → verify (retired)', context: 'Context + meta (retired)', quote_v2: 'Exact quotes v2 (retired)', atomic_v1: 'Atomic v1 (retired)' }
export const newRunMethods: Strategy[] = ['direct', 'atomic_v2']
export const qualifierLabels: Record<string, string> = {
  population: 'Population', group_comparison: 'Group / comparison', outcome: 'Outcome',
  value_unit: 'Quantity / unit', time_denominator: 'Time / denominator', negation_attribution: 'Negation / attribution',
}
export const fidelityLabels: Record<string, string> = {
  unresolved_qualifier_anchor: 'A condition could not be located exactly.',
  literal_number_absent_from_interpretation: 'An original numeric token is absent from the model interpretation.',
  no_qualifier_anchors_declared: 'The extractor did not provide original condition anchors.',
  duplicate_interpretation: 'This interpretation duplicates an earlier parsed fact.',
}
export function handoffLabel(kind: AuditHandoff['kind']) {
  return kind === 'live_ask' ? 'Actual Ask answer' : 'Authored demo · not a real Agent answer'
}
export function BindingDetail({ binding, label }: { binding: QuoteBinding; label: string }) {
  const description: Record<string, string> = { unique: 'Unique exact passage', ambiguous: 'Repeated passage; no location chosen',
    not_found: 'Quotation not found exactly', unknown_source: 'Source ID not provided', empty_quote: 'Empty quotation',
    unresolved_parent: 'Parent passage unresolved; no fallback location chosen' }
  return <div className={`audit-binding ${binding.status === 'unique' ? '' : 'audit-error-text'}`}>
    <strong>{label}: {description[binding.status] ?? binding.status}</strong>
    {binding.match_count > 0 && <span> · {binding.match_count} {binding.match_count === 1 ? 'match' : 'matches'} ({binding.candidates.map(s => `${s.start}–${s.end}`).join(', ')}{binding.candidates_truncated ? ', …' : ''})</span>}
  </div>
}
export function category(claim: AuditClaim) { return claim.status === 'ok' ? claim.relation ?? 'not_checked' : claim.status }
// Python offsets count Unicode code points, including astral symbols as one character.
export function LinkedText({ text, spans, selected, onSelect }: {
  text: string; spans: (Span & { claimId: string; category: string })[]; selected: string
  onSelect: (id: string) => void
}) {
  const chars = Array.from(text)
  const points = [...new Set([0, chars.length, ...spans.flatMap(s => [s.start, s.end])])].sort((a, b) => a - b)
  return <>{points.slice(0, -1).map((start, i) => {
    const end = points[i + 1]
    const matches = spans.filter(s => s.start <= start && s.end >= end)
    const hit = matches.find(s => s.claimId === selected) ?? matches[0]
    const part = chars.slice(start, end).join('')
    return hit ? <button key={start} data-span-start={start} className={`audit-text-link ${hit.category} ${hit.claimId === selected ? 'selected' : ''}`}
      title={`${labels[hit.category] ?? 'Not checked'} · select claim`} onClick={() => onSelect(hit.claimId)}>{part}</button>
      : <span key={start} className="audit-unlinked">{part}</span>
  })}</>
}
