import type { AuditRecord } from '../../api/audit'
import { labels, qualifierLabels, fidelityLabels, BindingDetail, category } from './Presentation'

type Props = {
  record: AuditRecord
  selected: string
  onSelect: (id: string, scroll?: boolean) => void
  locateEvidence: (sourceId: string, start: number) => void
}

export function ClaimList({ record, selected, onSelect, locateEvidence }: Props) {
  return <div className="audit-claims">{record.audit.claims.map((claim, index) => <article key={claim.id} id={`audit-${claim.id}`} className={`audit-claim ${selected === claim.id ? 'active' : ''}`}>
            <button className="audit-claim-toggle" aria-expanded={selected === claim.id} onClick={() => onSelect(selected === claim.id ? '' : claim.id, false)}>
              <span className="audit-claim-number">{String(index + 1).padStart(2, '0')}</span><span><span className="audit-claim-quote">{claim.normalized_claim ?? claim.quote}</span>{claim.normalized_claim && <small className="audit-muted">Model-parsed fact · {claim.parent_claim_id}</small>}<span className={`audit-verdict ${category(claim)}`}>{labels[category(claim)] ?? claim.status}</span>{claim.checker_disagreement && <span className="audit-verdict insufficient">Checkers disagree</span>}</span><span aria-hidden="true">{selected === claim.id ? '−' : '+'}</span>
            </button>
            {selected === claim.id && <div className="audit-claim-body"><p>{claim.explanation || 'No usable judgment was returned.'}</p>
              {claim.fidelity_diagnostic && <div className="audit-notice">
                <strong>Model relation: {claim.relation ? labels[claim.relation] : 'Not judged'}</strong>
                <p>{claim.fidelity_diagnostic.flags.length ? 'Extraction needs review; this fact is not counted as a completed check.' : 'No mechanical extraction issue detected. Meaning and completeness are not guaranteed.'}</p>
                {claim.fidelity_diagnostic.flags.map(flag => <p key={flag}>{fidelityLabels[flag] ?? flag}</p>)}
                {!!claim.fidelity_diagnostic.numbers_absent_from_interpretation.length && <p>Original numeric tokens: {claim.fidelity_diagnostic.numbers_absent_from_interpretation.join(', ')}. A wording change or conversion can also trigger this check.</p>}
                {claim.duplicate_of && <p>Duplicate interpretation of {claim.duplicate_of}; not independent support.</p>}
              </div>}
              {claim.checker_disagreement && <div className="audit-notice">Checkers disagree on support. This is a reason to inspect the original text, not an automatic contradiction or a calibrated risk estimate. The original Flash judgment is retained.</div>}
              {claim.answer_spans && <details className="audit-context" open><summary>Original answer fragments · unchanged text</summary>{claim.answer_spans.map((s, i) => <blockquote key={i}>{s.text}<small> · {s.start}–{s.end}</small></blockquote>)}</details>}
              {claim.slots && <details className="audit-context"><summary>Explicit qualifications · model parsing</summary><dl>{Object.entries(claim.slots).map(([name, value]) => <div key={name}><dt>{name}</dt><dd>{value ?? 'Not explicitly extracted'}</dd></div>)}</dl><p>Parsing status: {claim.decomposition_status}. Recording population or conditions is not a clinical evidence grade.</p></details>}
              {claim.qualifier_anchors && <details className="audit-context" open><summary>Conditions in the original answer · {claim.qualifier_anchors.length} anchors</summary>
                {claim.qualifier_anchors.map((q, i) => <div key={i} className="audit-qualifier">
                  <strong>{qualifierLabels[q.kind] ?? q.kind}</strong><blockquote>{q.quote}</blockquote>
                  <BindingDetail binding={q.binding} label="Original condition" />
                  {q.binding.span && <button className="audit-button" onClick={() => document.querySelector('#audit-original-answer [data-span-start="' + q.binding.span!.start + '"]')?.scrollIntoView({ behavior: 'smooth', block: 'center' })}>Locate in answer · {q.binding.span.start}–{q.binding.span.end}</button>}
                  <details><summary>Original context for this condition</summary><blockquote>{q.parent_quote}</blockquote><BindingDetail binding={q.parent_binding} label="Context" /></details>
                </div>)}
                <p>These are exact answer quotes selected by the extractor. Their existence does not establish that every required condition was selected or interpreted correctly.</p>
              </details>}
              {claim.answer_bindings && <details className="audit-context" open={claim.status === 'invalid_reference'}><summary>Fragment and evidence locations</summary>{claim.parent_binding && <BindingDetail binding={claim.parent_binding} label="Parent answer passage" />}{claim.answer_bindings.map((b, i) => <BindingDetail key={i} binding={b} label={`Answer fragment ${i + 1}`} />)}{claim.evidence_bindings?.map((b, i) => <BindingDetail key={i} binding={b} label={`Source ${b.source_id}`} />)}</details>}
              {claim.numeric_diagnostic && claim.numeric_diagnostic.status !== 'not_applicable' && <details className="audit-context"><summary>Numeric diagnostic · {claim.numeric_diagnostic.status}</summary><p>{claim.numeric_diagnostic.reason ?? claim.numeric_diagnostic.scope} This does not override the judgment.</p></details>}
              {claim.checker_results && <details className="audit-context"><summary>Recorded checker outputs</summary><pre className="audit-checker-json">{JSON.stringify(claim.checker_results, null, 2)}</pre><p>Raw scores and model agreement are not probabilities of truth.</p></details>}
              {claim.bindings && <details className="audit-context" open={claim.status !== 'ok'}><summary>Original text locations</summary>
                <BindingDetail binding={claim.bindings.answer} label="Answer" />
                {claim.bindings.evidence.map((b, i) => <div key={i}><BindingDetail binding={b} label={`Source ${b.source_id}`} />{b.status !== 'unique' && <blockquote>{b.quote}</blockquote>}</div>)}
                <small>Only unique, unchanged quotations are linked. Ambiguous passages are not counted as completed checks.</small>
              </details>}
              {claim.context_span && <details className="audit-context"><summary>Answer context · not source evidence</summary><blockquote>{claim.context_span.text}</blockquote><small>Characters {claim.context_span.start}–{claim.context_span.end}. Exact binding preserves the paragraph; it does not prove the model interpreted it correctly.</small></details>}
              {claim.status !== 'ok' && <p className="audit-error-text">This claim is not counted as a completed check. A returned relation with an invalid quote is not a pass.</p>}
              {claim.answer_span && <div className="audit-muted">Answer characters {claim.answer_span.start}–{claim.answer_span.end} · end exclusive</div>}
              {claim.evidence.length === 0 ? <p className="audit-muted">No source passage was bound to this judgment. See the full provided texts on the right.</p> : claim.evidence.map((ref, i) => <button key={i} className="audit-evidence-quote" onClick={() => locateEvidence(ref.source_id, ref.start)}>
                <span className="vm-eyebrow">{record.input.sources.find(s => s.id === ref.source_id)?.title ?? ref.source_id} · {ref.start}–{ref.end}</span><q>{ref.text}</q><span className="audit-source-action">Locate in full source ↗</span>
              </button>)}
            </div>}
          </article>)}</div>
}
