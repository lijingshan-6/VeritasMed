import { useEffect, useState } from 'react'
import type { FormEvent } from 'react'
import { useLocation } from 'react-router-dom'
import { inputProblem } from '../api/auditHandoff'
import type { AuditHandoff } from '../api/auditHandoff'
import { auditExamples, replayAudit, runAudit } from '../api/audit'
import type { AuditClaim, AuditInput, AuditRecord, Catalogue, QuoteBinding, Span, Strategy } from '../api/audit'
import './audit.css'

const labels: Record<string, string> = {
  supported: 'Supported', contradicted: 'Contradicted', insufficient: 'Insufficient evidence',
  invalid_reference: 'Unresolved quote', invalid_output: 'Invalid model output',
  ambiguous_reference: 'Repeated quote · location unresolved',
  execution_error: 'Execution failed', not_checked: 'Not checked',
  needs_review: 'Needs review · parsing unresolved',
  not_source_checked: 'Presentation text · not source-checked',
}
const methodLabels: Record<Strategy, string> = { direct: 'Direct Flash', split: 'Extract → verify each claim', context: 'Context + meta · experimental', quote_v2: 'Exact quotes v2 · experimental', atomic_v1: 'Atomic facts · experimental' }
function handoffLabel(kind: AuditHandoff['kind']) {
  return kind === 'live_ask' ? 'Actual Ask answer' : kind === 'research_workflow' ? 'Actual controlled research answer' : 'Authored demo · not a real Agent answer'
}
function BindingDetail({ binding, label }: { binding: QuoteBinding; label: string }) {
  const description: Record<string, string> = { unique: 'Unique exact passage', ambiguous: 'Repeated passage; no location chosen',
    not_found: 'Quotation not found exactly', unknown_source: 'Source ID not provided', empty_quote: 'Empty quotation' }
  return <div className={`audit-binding ${binding.status === 'unique' ? '' : 'audit-error-text'}`}>
    <strong>{label}: {description[binding.status] ?? binding.status}</strong>
    {binding.match_count > 0 && <span> · {binding.match_count} {binding.match_count === 1 ? 'match' : 'matches'} ({binding.candidates.map(s => `${s.start}–${s.end}`).join(', ')}{binding.candidates_truncated ? ', …' : ''})</span>}
  </div>
}
function category(claim: AuditClaim) { return claim.status === 'ok' ? claim.relation ?? 'not_checked' : claim.status }
function message(error: unknown) {
  const detail = (error as { response?: { data?: { detail?: unknown } } })?.response?.data?.detail
  return typeof detail === 'string' ? detail : 'Audit service unavailable or input rejected. Start python scripts/run_audit_demo.py and check the input limits.'
}

// Python offsets count Unicode code points, including astral symbols as one character.
function LinkedText({ text, spans, selected, onSelect }: {
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

const emptyInput = (): AuditInput => ({ answer: '', strategy: 'direct', sources: [{ id: 'source-1', title: 'Source 1', text: '' }] })

export function AuditPage({ context, onClose }: { context?: AuditHandoff; onClose?: () => void } = {}) {
  const location = useLocation()
  const incoming = context ?? (location.state as { handoff?: AuditHandoff } | null)?.handoff
  const embedded = !!context
  const [handoff, setHandoff] = useState<AuditHandoff | null>(incoming ?? null)
  const [catalogue, setCatalogue] = useState<Catalogue | null>(null)
  const [example, setExample] = useState('')
  const [strategy, setStrategy] = useState<Strategy>('direct')
  const [record, setRecord] = useState<AuditRecord | null>(null)
  const [selected, setSelected] = useState('')
  const [pending, setPending] = useState('')
  const [error, setError] = useState('')
  const [formOpen, setFormOpen] = useState(!!incoming && !embedded)
  const [draft, setDraft] = useState<AuditInput>(() => incoming?.input ?? emptyInput())

  function show(value: AuditRecord) {
    setRecord(value)
    setSelected(value.audit.claims[0]?.id ?? '')
    setError('')
  }
  async function load(id: string, mode: Strategy) {
    setPending('Loading saved audit…'); setRecord(null); setError('')
    try { show(await replayAudit(id, mode)) } catch (e) { setError(message(e)) }
    finally { setPending('') }
  }
  useEffect(() => {
    if (embedded) return
    let alive = true
    auditExamples().then(async data => {
      if (!alive) return
      setCatalogue(data)
      const first = data.examples.find(e => e.strategies.direct && (!e.requires_download || data.sources_downloaded))
      if (!incoming && first) {
        setExample(first.id); setPending('Loading saved audit…')
        try { const value = await replayAudit(first.id, 'direct'); if (alive) show(value) }
        catch (e) { if (alive) setError(message(e)) }
        finally { if (alive) setPending('') }
      }
    }).catch(e => { if (alive) setError(message(e)) })
    return () => { alive = false }
  }, [])

  async function submit(event?: FormEvent) {
    event?.preventDefault()
    const problem = inputProblem(draft)
    if (problem) { setError(problem); return }
    setPending('Auditing supplied texts…'); setRecord(null); setError('')
    try {
      const value = await runAudit(draft)
      if (handoff) value.provenance = { ...value.provenance, handoff,
        input_edited: draft.answer !== handoff.input.answer || JSON.stringify(draft.sources) !== JSON.stringify(handoff.input.sources) }
      show(value); setFormOpen(false)
    } catch (e) { setError(message(e)) }
    finally { setPending('') }
  }
  function selectClaim(id: string, scroll = true) {
    setSelected(id)
    if (scroll) document.getElementById(`audit-${id}`)?.scrollIntoView({ behavior: 'smooth', block: 'nearest' })
  }
  function locateEvidence(sourceId: string, start: number) {
    const source = document.getElementById(`audit-source-${sourceId}`)
    const passage = source?.querySelector(`[data-span-start="${start}"]`)
    ;(passage ?? source)?.scrollIntoView({ behavior: 'smooth', block: 'nearest' })
  }
  function exportRecord() {
    if (!record) return
    const url = URL.createObjectURL(new Blob([JSON.stringify(record, null, 2)], { type: 'application/json' }))
    const link = document.createElement('a'); link.href = url; link.download = `veritasmed-audit-${record.audit.id}.json`
    link.click(); setTimeout(() => URL.revokeObjectURL(url), 1000)
  }
  const audit = record?.audit
  const active = audit?.claims.find(c => c.id === selected)
  const validSpans = [...(audit?.claims.flatMap(c => (c.answer_spans ?? (c.answer_span ? [c.answer_span] : [])).map(s => ({ ...s, claimId: c.id, category: category(c) }))) ?? []),
    ...(audit?.meta_text?.flatMap(m => m.answer_span ? [{ ...m.answer_span, claimId: m.id, category: m.status }] : []) ?? [])]
  const models = [...new Set(audit?.calls.flatMap(c => c.transport_metadata?.model_identifiers ?? []) ?? [])]
  const metaFailures = audit?.meta_text?.filter(m => m.status !== 'not_source_checked').length ?? 0
  const available = catalogue?.examples.filter(e => e.strategies[strategy]) ?? []

  return <div className={`audit-page${embedded ? ' audit-page-embedded' : ''}`}>
    <div className="audit-heading">
      <div><div className="vm-eyebrow">{embedded ? 'Ask / Audit this answer' : 'VeritasMed / Textual evidence'}</div><h1>{embedded ? 'Review the answer and its evidence.' : 'Inspect the answer. Follow the evidence.'}</h1>
        <p>{embedded ? context.question : 'Every judgment belongs to a passage. Unchecked text remains visible.'}</p></div>
      {embedded ? <button className="audit-button" onClick={onClose}>Back to answer</button>
        : <button className="audit-button primary" disabled={!!pending} onClick={() => setFormOpen(v => !v)}>{formOpen ? 'Close input' : 'Audit your own answer'}</button>}
    </div>
    {embedded && <div className="audit-toolbar">
      <label>Method <select aria-label="Answer audit method" disabled={!!pending} value={draft.strategy} onChange={e => setDraft({ ...draft, strategy: e.target.value as Strategy })}>{Object.entries(methodLabels).map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></label>
      <button className="audit-button primary" disabled={!!pending} onClick={() => void submit()}>{record ? 'Run audit again' : 'Run audit'}</button>
      <button className="audit-button" disabled={!!pending} onClick={() => setFormOpen(v => !v)}>{formOpen ? 'Close inputs' : 'Inspect inputs'}</button>
      <span className="audit-muted">{handoffLabel(context.kind)} · {context.input.sources.length} source passages · original answer retained</span>
    </div>}
    {!embedded && <div className="audit-toolbar">
      <span className="vm-eyebrow">Real saved runs</span>
      <label>Method <select aria-label="Audit method" disabled={!!pending} value={strategy} onChange={e => {
        const value = e.target.value as Strategy; setStrategy(value)
        const ready = catalogue?.examples.filter(c => !c.requires_download || catalogue.sources_downloaded)
        const next = ready?.find(c => c.id === example && c.strategies[value]) ?? ready?.find(c => c.strategies[value])
        setExample(next?.id ?? ''); setRecord(null)
        if (next) void load(next.id, value)
      }}>{Object.entries(methodLabels).map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></label>
      <label>Answer <select aria-label="Saved answer" disabled={!!pending || !available.length} value={example} onChange={e => {
        setExample(e.target.value); void load(e.target.value, strategy)
      }}><option value="" disabled>Select a saved answer</option>{available.map(e => <option key={e.id} value={e.id} disabled={e.requires_download && !catalogue?.sources_downloaded}>{e.label} · {e.strategies[strategy]}</option>)}</select></label>
      <span className="audit-muted">Real saved inference · no new API call</span>
    </div>}
    {catalogue && !catalogue.sources_downloaded && <div className="audit-notice">The medical demo is bundled and ready to replay. Optional nonmedical RAGTruth research examples require <code>python scripts/verification/answer_benchmark.py download</code>, then reload.</div>}
    {catalogue && !catalogue.examples.length && <div className="audit-notice">No saved run is available yet. You can audit supplied texts using the input below.</div>}
    {error && <div role="alert" className="audit-notice error">{error}</div>}
    {handoff && formOpen && <div className="audit-notice">
      <strong>{handoffLabel(handoff.kind)}</strong>
      <p>{handoff.question}</p><p>{handoff.input.sources.length} complete source passages copied with their original text. Review the inputs below; no audit call has been made by this transfer. The original answer stays unchanged.</p>
    </div>}
    {formOpen && <form className="audit-form" onSubmit={submit}>
      <div className="audit-section-title"><h2>Answer + supplied sources</h2>{record && <button type="button" className="audit-button" onClick={() => { setDraft(record.input); setHandoff(null) }}>Use the displayed texts</button>}</div>
      <label>Answer to audit <textarea aria-label="Answer to audit" required maxLength={12000} rows={5} value={draft.answer} onChange={e => setDraft({ ...draft, answer: e.target.value })} /></label>
      {draft.sources.map((source, index) => <fieldset key={source.id}><legend>{source.id}</legend>
        <label>Source title <input aria-label={`Source ${index + 1} title`} required maxLength={500} value={source.title} onChange={e => setDraft({ ...draft, sources: draft.sources.map((s, i) => i === index ? { ...s, title: e.target.value } : s) })} /></label>
        <label>Original source text <textarea aria-label={`Source ${index + 1} text`} required maxLength={50000} rows={5} value={source.text} onChange={e => setDraft({ ...draft, sources: draft.sources.map((s, i) => i === index ? { ...s, text: e.target.value } : s) })} /></label>
        {draft.sources.length > 1 && <button type="button" className="audit-button" onClick={() => setDraft({ ...draft, sources: draft.sources.filter((_, i) => i !== index) })}>Remove source</button>}
      </fieldset>)}
      <div className="audit-toolbar">
        <button type="button" className="audit-button" disabled={draft.sources.length >= 40 || !!pending} onClick={() => setDraft({ ...draft, sources: [...draft.sources, { id: `source-${Date.now()}`, title: `Source ${draft.sources.length + 1}`, text: '' }] })}>+ Add source</button>
        <label>Method <select aria-label="New audit method" value={draft.strategy} onChange={e => setDraft({ ...draft, strategy: e.target.value as Strategy })}>{Object.entries(methodLabels).map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></label>
        <button className="audit-button primary" disabled={!!pending}>Run new audit</button>
      </div>
      <p className="audit-muted">Sends these texts to the Flash endpoint configured in your local .env. Split mode makes one extraction call plus a call per claim and can take several minutes. The server does not save this input. Up to 40 sources / 80,000 source characters; no automatic search. Exact quotes v2 binds only unique original passages and exposes repeated or missing quotations. Direct remains the baseline.</p>
    </form>}
    {pending && <div className="audit-pending" role="status"><span className="audit-pulse" />{pending}<span className="audit-muted">The full result appears when the run finishes.</span></div>}
    {record && audit && <>
      <div className="audit-runline">
        <span className="audit-mode">{record.mode === 'saved' ? 'SAVED INFERENCE' : 'NEW INFERENCE'}</span>
        <span>{methodLabels[audit.strategy]}</span>
        <span>{audit.calls.length} {audit.calls.length === 1 ? 'call' : 'calls'} · {audit.elapsed_seconds.toFixed(1)} s recorded</span>
        <span className="audit-muted">{new Date(audit.created_utc).toLocaleString()}</span>
        <button className="audit-button" onClick={exportRecord}>Export audit JSON</button>
      </div>
      <p className="audit-muted">{record.provenance.note}</p>
      {record.provenance.paper && /^https?:\/\//i.test(record.provenance.paper) && <p><a href={record.provenance.paper} target="_blank" rel="noreferrer">Open original paper ↗</a></p>}
      {audit.supplemental_checkers && <div className="audit-notice">Separate local checker: {audit.supplemental_checkers.judgments}/{audit.supplemental_checkers.attempts} standalone fact checks completed in {audit.supplemental_checkers.elapsed_seconds.toFixed(1)} s, in addition to the recorded Flash calls. Disagreements remain visible; no vote or combined confidence score is applied.</div>}
      {record.provenance.handoff && <div className="audit-notice"><strong>{handoffLabel(record.provenance.handoff.kind)}</strong> · {record.provenance.input_edited ? 'Inputs edited after transfer; originals retained in export.' : 'Original answer and source passages preserved.'}<p>{record.provenance.handoff.question}</p></div>}
      <div className="audit-layout">
        <section className="audit-answer-column">
          <div className="vm-eyebrow">Original answer · click an underlined passage</div>
          <div className="audit-answer-text"><LinkedText text={record.input.answer} spans={validSpans} selected={selected} onSelect={selectClaim} /></div>
          <div className="audit-summary">
            {audit.strategy === 'atomic_v1' && <p><strong>{audit.parent_count ?? 0} original passages → {audit.claims.length} parsed facts.</strong> These are model interpretations. All parsed facts passing does not establish that every assertion was extracted. {audit.extraction?.completeness_note}</p>}
            <div className="audit-summary-counts">{(['supported', 'contradicted', 'insufficient'] as const).map(k => <span key={k} className={k}><b>{audit.summary[k] ?? 0}</b> {labels[k]}</span>)}{!!audit.summary.needs_review && <span><b>{audit.summary.needs_review}</b> parsing needs review</span>}<span><b>{(audit.summary.failed_or_unchecked ?? 0) - (audit.summary.needs_review ?? 0)}</b> failed / unchecked claims</span>{metaFailures > 0 && <span className="audit-error-text"><b>{metaFailures}</b> invalid presentation ranges</span>}</div>
            <p>{audit.checked_coverage.covered_nonspace_characters} / {audit.checked_coverage.total_nonspace_characters} non-space answer characters received a validly anchored judgment. Text coverage does not measure correctness or completeness of meaning.</p>
            <p>Run: <strong>{audit.status}</strong>{audit.claims_at_cap ? ' · Claim limit reached; additional assertions may be omitted.' : ''}. These are model judgments about the supplied texts, not confidence scores or clinical evidence grades.</p>
          </div>
          <div className="audit-section-title"><h2>Claim audit</h2><span className="audit-muted">{audit.claims.length} extracted claims</span></div>
          {!audit.claims.length && <div className="audit-notice">No claims were successfully extracted. The answer is unreviewed.</div>}
          <div className="audit-claims">{audit.claims.map((claim, index) => <article key={claim.id} id={`audit-${claim.id}`} className={`audit-claim ${selected === claim.id ? 'active' : ''}`}>
            <button className="audit-claim-toggle" aria-expanded={selected === claim.id} onClick={() => selectClaim(selected === claim.id ? '' : claim.id, false)}>
              <span className="audit-claim-number">{String(index + 1).padStart(2, '0')}</span><span><span className="audit-claim-quote">{claim.normalized_claim ?? claim.quote}</span>{claim.normalized_claim && <small className="audit-muted">Model-parsed fact · {claim.parent_claim_id}</small>}<span className={`audit-verdict ${category(claim)}`}>{labels[category(claim)] ?? claim.status}</span>{claim.checker_disagreement && <span className="audit-verdict insufficient">Checkers disagree</span>}</span><span aria-hidden="true">{selected === claim.id ? '−' : '+'}</span>
            </button>
            {selected === claim.id && <div className="audit-claim-body"><p>{claim.explanation || 'No usable judgment was returned.'}</p>
              {claim.checker_disagreement && <div className="audit-notice">Checkers disagree on support. This is a reason to inspect the original text, not an automatic contradiction or a calibrated risk estimate. The original Flash judgment is retained.</div>}
              {claim.answer_spans && <details className="audit-context" open><summary>Original answer fragments · unchanged text</summary>{claim.answer_spans.map((s, i) => <blockquote key={i}>{s.text}<small> · {s.start}–{s.end}</small></blockquote>)}</details>}
              {claim.slots && <details className="audit-context"><summary>Explicit qualifications · model parsing</summary><dl>{Object.entries(claim.slots).map(([name, value]) => <div key={name}><dt>{name}</dt><dd>{value ?? 'Not explicitly extracted'}</dd></div>)}</dl><p>Parsing status: {claim.decomposition_status}. Recording population or conditions is not a clinical evidence grade.</p></details>}
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
          {!!audit.meta_text?.length && <section className="audit-meta"><h2>Presentation text</h2><p className="audit-muted">These model-selected ranges describe the response itself. They are not counted as source-supported facts. Routing can be wrong; all ranges remain visible.</p>{audit.meta_text.map(m => <article key={m.id} id={`audit-${m.id}`} className={`audit-claim ${selected === m.id ? 'active' : ''}`}><button className="audit-claim-toggle" onClick={() => selectClaim(selected === m.id ? '' : m.id, false)} aria-expanded={selected === m.id}><span>↳</span><span className="audit-claim-quote">{m.quote}</span><span>{selected === m.id ? '−' : '+'}</span></button><div className="audit-claim-body"><span className="audit-verdict">{m.kind} · {labels[m.status] ?? m.status}</span>{selected === m.id && <><p>{m.explanation}{m.answer_span && ` (${m.answer_span.start}–${m.answer_span.end})`}</p>{m.binding && <BindingDetail binding={m.binding} label="Answer" />}</>}</div></article>)}{audit.presentation_counts && <p className="audit-muted">Full answer: {audit.presentation_counts.full_answer_whitespace_tokens} whitespace-separated tokens. Includes headings and presentation text; this is not a judgment that a claimed word limit was met.</p>}</section>}
          <details className="audit-details"><summary>Uncovered answer text ({audit.checked_coverage.uncovered.length} ranges)</summary><p>No completed claim judgment covers these characters. Some gaps may be punctuation or connective text; coverage alone cannot establish semantic completeness.</p>{audit.checked_coverage.uncovered.map(s => <blockquote key={s.start}><small>{s.start}–{s.end}</small> {s.text}</blockquote>)}</details>
          <details className="audit-details"><summary>Run provenance & execution</summary><p>{record.provenance.note} {record.provenance.run && `Run: ${record.provenance.run}.`}</p><p>Reported model identifiers: {models.join(', ') || 'unavailable'}. These are provider metadata.</p>{record.provenance.handoff && <p>Ask thread: {record.provenance.handoff.thread_id}. Original inputs and citation map are included in the JSON export.</p>}<code className="audit-hash">Answer SHA-256: {audit.answer_sha256}</code><ol>{audit.calls.map((c, i) => <li key={i}>{c.stage} · {c.status} · {c.elapsed_seconds.toFixed(1)} s · {c.usage?.total_tokens != null ? `${c.usage.total_tokens} reported tokens` : 'usage unavailable'}{c.error_type ? ` · ${c.error_type}` : ''}</li>)}</ol></details>
        </section>
        <aside className="audit-sources-column">
          <div className="audit-section-title"><h2>Provided sources</h2><span className="audit-muted">{record.input.sources.length} {record.input.sources.length === 1 ? 'text' : 'texts'}</span></div>
          <p className="audit-muted">Highlights follow claim {active ? audit.claims.indexOf(active) + 1 : '—'}. Click a marked source passage to select its claim. A reference proves text location, not semantic correctness.</p>
          {record.input.sources.map(source => {
            const refs = audit.claims.flatMap(c => c.status === 'ok' ? c.evidence.filter(r => r.source_id === source.id).map(r => ({ ...r, claimId: c.id, category: category(c) })) : [])
            const origin = record.provenance.handoff?.source_map.find(s => s.id === source.id)
            return <article className="audit-source" id={`audit-source-${source.id}`} key={source.id}>
              <header><span className="vm-eyebrow">{source.id} / supplied text</span><h3>{source.title}</h3></header>
              {origin && <p className="audit-muted">Original source passage: {origin.chunk_id}{origin.section ? ` · ${origin.section}` : ''}{/^https?:\/\//i.test(origin.external_url) && <> · <a href={origin.external_url} target="_blank" rel="noreferrer">Open source ↗</a></>}</p>}
              <div className="audit-source-text"><LinkedText text={source.text} spans={refs} selected={selected} onSelect={selectClaim} /></div>
              <details><summary>Source fingerprint</summary><code className="audit-hash">SHA-256 {audit.source_hashes[source.id]}</code><p>Positions use Unicode code points, with an exclusive end.</p></details>
            </article>
          })}
        </aside>
      </div>
    </>}
    {embedded && !record && !formOpen && <>
      {!pending && <p className="audit-muted">Run audit to check this answer against its retrieved passages. Opening this view makes no model call. You can return to the answer or continue asking below.</p>}
      <div className="audit-layout"><section className="audit-answer-column"><div className="vm-eyebrow">Answer to audit · not yet checked</div><div className="audit-answer-text">{draft.answer}</div></section>
        <aside className="audit-sources-column"><h2>Answer sources</h2>{draft.sources.map(source => <article className="audit-source" key={source.id}><h3>{source.title}</h3><div className="audit-source-text">{source.text}</div></article>)}</aside></div>
    </>}
    {!embedded && !record && !pending && <div className="audit-empty"><div className="vm-eyebrow">A traceable judgment starts with the text</div><h2>Bring an answer and its sources.</h2><p>Load a real saved run above, or audit a new answer. Each claim links to exact passages; missing evidence and unfinished checks stay visible.</p></div>}
  </div>
}
