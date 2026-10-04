import { ClaimList } from '../components/audit/ClaimList'
import { SourceList } from '../components/audit/SourceList'
import { useState } from 'react'
import type { FormEvent } from 'react'
import { inputProblem } from '../api/auditHandoff'
import type { AuditHandoff } from '../api/auditHandoff'
import { runAudit } from '../api/audit'
import type { AuditInput, AuditRecord, Strategy } from '../api/audit'
import type { SavedAudit } from '../conversation/model'
import { newId, now, sha256 } from '../conversation/model'
import { labels, methodLabels, newRunMethods, handoffLabel, BindingDetail, category, LinkedText } from '../components/audit/Presentation'
import './audit.css'
import { isReplayOnly } from '../demo'

function message(error: unknown) {
  const detail = (error as { response?: { data?: { detail?: unknown } } })?.response?.data?.detail
  return typeof detail === 'string' ? detail : 'Audit service unavailable or input rejected. Check the Flash configuration and the input limits.'
}

// The audit view of one Ask answer revision. It never rewrites the answer.
export function AuditPage({ context, onClose, saved = [], onRecord, variant }: { context: AuditHandoff; onClose: () => void; saved?: SavedAudit[]; onRecord?: (record: AuditRecord) => Promise<void>; variant?: 'tab' }) {
  const [handoff, setHandoff] = useState<AuditHandoff | null>(context)
  const initialSaved = saved.find(r => r.record.audit.strategy === 'direct' && !r.edited) ?? saved[0]
  const [record, setRecord] = useState<AuditRecord | null>(initialSaved?.record ?? null)
  const [selected, setSelected] = useState(initialSaved?.record.audit.claims[0]?.id ?? '')
  const [pending, setPending] = useState('')
  const [error, setError] = useState('')
  const [formOpen, setFormOpen] = useState(false)
  const [draft, setDraft] = useState<AuditInput>(() => context.input)

  function show(value: AuditRecord) {
    setRecord(value)
    setSelected(value.audit.claims[0]?.id ?? '')
    setError('')
  }

  async function submit(event?: FormEvent) {
    event?.preventDefault()
    if (isReplayOnly) { setError('Saved replay makes no model calls. Start the full Ask service for a new audit.'); return }
    const problem = inputProblem(draft)
    if (problem) { setError(problem); return }
    setPending('Auditing supplied texts…'); setRecord(null); setError('')
    const started = performance.now()
    let returnedRecord: AuditRecord | null = null
    try {
      const value = await runAudit(draft)
      returnedRecord = value
      if (handoff) value.provenance = { ...value.provenance, handoff,
        input_edited: draft.answer !== handoff.input.answer || JSON.stringify(draft.sources) !== JSON.stringify(handoff.input.sources) }
      await onRecord?.(value)
      show(value); setFormOpen(false)
    } catch (e) {
      // A transport failure is an attempted run, not a completed verifier judgment.
      // Preserve its exact input, while making no claim about server completion.
      if (onRecord && !returnedRecord) {
        const value: AuditRecord = { input: structuredClone(draft), mode: 'live', provenance: { note: 'Audit response unavailable. Server completion is unknown; no model judgment is inferred.', ...(handoff ? { handoff } : {}) },
          audit: { id: newId(), status: 'transport_error', created_utc: now(), strategy: draft.strategy,
            elapsed_seconds: (performance.now() - started) / 1000, claims: [], summary: {}, claims_at_cap: false,
            answer_sha256: await sha256(draft.answer), source_hashes: Object.fromEntries(await Promise.all(draft.sources.map(async s => [s.id, await sha256(s.text)]))),
            checked_coverage: { covered_nonspace_characters: 0, total_nonspace_characters: Array.from(draft.answer.replace(/\s/g, '')).length,
              uncovered: [{ start: 0, end: Array.from(draft.answer).length, text: draft.answer }] },
            calls: [{ stage: 'audit_transport', status: 'response_unavailable', elapsed_seconds: (performance.now() - started) / 1000, usage: null }] } }
        try { await onRecord(value); show(value) } catch { /* Keep the explicit failure notice if local persistence also fails. */ }
      }
      setError(returnedRecord ? 'The audit returned, but could not be attached to this answer. Export the audit before leaving.' : message(e))
      if (returnedRecord) { setRecord(returnedRecord); setSelected(returnedRecord.audit.claims[0]?.id ?? '') }
    }
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
  const validSpans = [...(audit?.claims.flatMap(c => [...(c.answer_spans ?? (c.answer_span ? [c.answer_span] : [])),
    ...(c.qualifier_anchors?.flatMap(q => q.binding.span ? [q.binding.span] : []) ?? [])].map(s => ({ ...s, claimId: c.id, category: category(c) }))) ?? []),
    ...(audit?.meta_text?.flatMap(m => m.answer_span ? [{ ...m.answer_span, claimId: m.id, category: m.status }] : []) ?? [])]
  const models = [...new Set(audit?.calls.flatMap(c => c.transport_metadata?.model_identifiers ?? []) ?? [])]
  const metaFailures = audit?.meta_text?.filter(m => m.status !== 'not_source_checked').length ?? 0

  return <div className={`audit-page audit-page-embedded${variant === 'tab' ? ' audit-page--tab' : ''}`}>
    {variant !== 'tab' && <div className="audit-heading">
      <div><div className="vm-eyebrow">Ask / Audit this answer</div><h1>Review the answer and its evidence.</h1>
        <p>{context.question}</p></div>
      <button className="audit-button" onClick={onClose}>Back to answer</button>
    </div>}
    <div className="audit-toolbar">
      {saved.length > 0 && <label>Run <select aria-label="Saved audit run" value={saved.find(r => r.record.audit.id === record?.audit.id)?.id ?? ''} onChange={e => { const run = saved.find(r => r.id === e.target.value); if (run) show(run.record) }}><option value="" disabled>Select run</option>{saved.map((r, i) => <option key={r.id} value={r.id}>{i + 1} · {methodLabels[r.record.audit.strategy] ?? r.record.audit.strategy}{r.edited ? ' · edited inputs' : ''}{r.record.audit.status === 'ok' ? '' : ' · ' + r.record.audit.status.replace('_', ' ')}</option>)}</select></label>}
      {!isReplayOnly && <label>Method <select aria-label="Answer audit method" disabled={!!pending} value={draft.strategy} onChange={e => setDraft({ ...draft, strategy: e.target.value as Strategy })}>{newRunMethods.map(value => <option key={value} value={value}>{methodLabels[value]}</option>)}</select></label>}
      {!isReplayOnly && <button className="audit-button primary" disabled={!!pending} onClick={() => void submit()}>{record ? 'Check again' : 'Check claims'}</button>}
      <span className="audit-toolbar-spacer" />
      <button className="audit-link" disabled={!!pending} onClick={() => setFormOpen(v => !v)}>{formOpen ? 'Close inputs' : 'Inputs'}</button>
      {record && <button className="audit-link" onClick={exportRecord}>Export JSON</button>}
    </div>
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
        <label>Method <select aria-label="New audit method" value={draft.strategy} onChange={e => setDraft({ ...draft, strategy: e.target.value as Strategy })}>{newRunMethods.map(value => <option key={value} value={value}>{methodLabels[value]}</option>)}</select></label>
        <button className="audit-button primary" disabled={!!pending || isReplayOnly}>{isReplayOnly ? 'Saved runs only' : 'Run new audit'}</button>
      </div>
      <p className="audit-muted">Sends these texts to the Flash endpoint configured in your local .env. Atomic v2 makes up to three calls. The server does not save this input. Up to 40 sources / 80,000 source characters; no automatic search. Direct remains the default.</p>
    </form>}
    {pending && <div className="audit-pending" role="status"><span className="audit-pulse" />{pending}<span className="audit-muted">The full result appears when the run finishes.</span></div>}
    {record && audit && <>
      <p className="audit-runline">{methodLabels[audit.strategy] ?? audit.strategy} · {audit.calls.length} model {audit.calls.length === 1 ? 'call' : 'calls'} · {audit.elapsed_seconds.toFixed(0)} s · {record.mode === 'saved' || saved.some(r => r.record.audit.id === record.audit.id) ? 'recorded' : 'new run'} {new Date(audit.created_utc).toLocaleDateString()}
        {' · '}{handoffLabel(context.kind).toLowerCase()} with {context.input.sources.length} source passages</p>
      <VerdictBar summary={audit.summary} total={audit.claims.length} status={audit.status} />
      {record.provenance.paper && /^https?:\/\//i.test(record.provenance.paper) && <p><a href={record.provenance.paper} target="_blank" rel="noreferrer">Open original paper ↗</a></p>}
      {audit.supplemental_checkers && <div className="audit-notice">Separate local checker: {audit.supplemental_checkers.judgments}/{audit.supplemental_checkers.attempts} standalone fact checks completed in {audit.supplemental_checkers.elapsed_seconds.toFixed(1)} s, in addition to the recorded Flash calls. Disagreements remain visible; no vote or combined confidence score is applied.</div>}
      {record.provenance.handoff && record.provenance.input_edited && <div className="audit-notice"><strong>{handoffLabel(record.provenance.handoff.kind)}</strong> · {record.provenance.input_edited ? 'Inputs edited after transfer; originals retained in export.' : 'Original answer and source passages preserved.'}<p>{record.provenance.handoff.question}</p></div>}
      <div className="audit-layout">
        <section className="audit-answer-column">
          <h2 className="audit-column-title">Answer <small>Underlined passages were checked. Click one to see its source.</small></h2>
          <div className="audit-answer-text" id="audit-original-answer"><LinkedText text={record.input.answer} spans={validSpans} selected={selected} onSelect={selectClaim} /></div>
          <details className="audit-summary">
            <summary>What this check covers</summary>
            {audit.strategy.startsWith('atomic_') && <p><strong>{audit.parent_count ?? 0} original passages → {audit.claims.length} parsed facts.</strong> These are model interpretations. All parsed facts passing does not establish that every assertion was extracted. {audit.extraction?.completeness_note}</p>}
            {metaFailures > 0 && <p className="audit-error-text">{metaFailures} invalid presentation ranges</p>}
            <p>{audit.checked_coverage.covered_nonspace_characters} / {audit.checked_coverage.total_nonspace_characters} non-space answer characters received a validly anchored judgment. Text coverage does not measure correctness or completeness of meaning.</p>
            <p>Run: <strong>{audit.status}</strong>{audit.claims_at_cap ? ' · Claim limit reached; additional assertions may be omitted.' : ''}. These are model judgments about the supplied texts, not confidence scores or clinical evidence grades.</p>
            <p>{record.provenance.note}</p>
          </details>
          <div className="audit-section-title"><h2>Claims</h2><span className="audit-muted">{audit.claims.length} checked statements</span></div>
          {!audit.claims.length && <div className="audit-notice">No claims were successfully extracted. The answer is unreviewed.</div>}
          <ClaimList record={record} selected={selected} onSelect={selectClaim} locateEvidence={locateEvidence} />
          {!!audit.meta_text?.length && <section className="audit-meta"><h2>Presentation text</h2><p className="audit-muted">These model-selected ranges describe the response itself. They are not counted as source-supported facts. Routing can be wrong; all ranges remain visible.</p>{audit.meta_text.map(m => <article key={m.id} id={`audit-${m.id}`} className={`audit-claim ${selected === m.id ? 'active' : ''}`}><button className="audit-claim-toggle" onClick={() => selectClaim(selected === m.id ? '' : m.id, false)} aria-expanded={selected === m.id}><span>↳</span><span className="audit-claim-quote">{m.quote}</span><span>{selected === m.id ? '−' : '+'}</span></button><div className="audit-claim-body"><span className="audit-verdict">{m.kind} · {labels[m.status] ?? m.status}</span>{selected === m.id && <><p>{m.explanation}{m.answer_span && ` (${m.answer_span.start}–${m.answer_span.end})`}</p>{m.binding && <BindingDetail binding={m.binding} label="Answer" />}</>}</div></article>)}{audit.presentation_counts && <p className="audit-muted">Full answer: {audit.presentation_counts.full_answer_whitespace_tokens} whitespace-separated tokens. Includes headings and presentation text; this is not a judgment that a claimed word limit was met.</p>}</section>}
          <details className="audit-details"><summary>Uncovered answer text ({audit.checked_coverage.uncovered.length} ranges)</summary><p>No completed claim judgment covers these characters. Some gaps may be punctuation or connective text; coverage alone cannot establish semantic completeness.</p>{audit.checked_coverage.uncovered.map(s => <blockquote key={s.start}><small>{s.start}–{s.end}</small> {s.text}</blockquote>)}</details>
          <details className="audit-details"><summary>Run provenance & execution</summary><p>{record.provenance.note} {record.provenance.run && `Run: ${record.provenance.run}.`}</p><p>Reported model identifiers: {models.join(', ') || 'unavailable'}. These are provider metadata.</p>{record.provenance.handoff && <p>Ask thread: {record.provenance.handoff.thread_id}. Original inputs and citation map are included in the JSON export.</p>}<code className="audit-hash">Answer SHA-256: {audit.answer_sha256}</code><ol>{audit.calls.map((c, i) => <li key={i}>{c.stage} · {c.status} · {c.elapsed_seconds.toFixed(1)} s · {c.usage?.total_tokens != null ? `${c.usage.total_tokens} reported tokens` : 'usage unavailable'}{c.error_type ? ` · ${c.error_type}` : ''}</li>)}</ol></details>
        </section>
        <SourceList record={record} selected={selected} onSelect={selectClaim} />
      </div>
    </>}
    {!record && !formOpen && <>
      {!pending && <p className="audit-muted">{isReplayOnly ? 'No audit is saved for this answer. Replay does not create a judgment. Return to the answer to inspect its recorded sources.' : 'Run audit to check this answer against its retrieved passages. Opening this view makes no model call. You can return to the answer or continue asking below.'}</p>}
      <div className="audit-layout"><section className="audit-answer-column"><div className="vm-eyebrow">Answer to audit · not yet checked</div><div className="audit-answer-text">{draft.answer}</div></section>
        <aside className="audit-sources-column"><h2>Answer sources</h2>{draft.sources.map(source => <article className="audit-source" key={source.id}><h3>{source.title}</h3><div className="audit-source-text">{source.text}</div></article>)}</aside></div>
    </>}
  </div>
}

// One proportional bar: how many statements the checker found supported, contradicted,
// insufficient or could not resolve. Model judgments, not a confidence score.
function VerdictBar({ summary, total, status }: { summary: Record<string, number>; total: number; status: string }) {
  const parts = [
    ['supported', summary.supported ?? 0, 'supported'],
    ['contradicted', summary.contradicted ?? 0, 'contradicted'],
    ['insufficient', summary.insufficient ?? 0, 'not supported by the sources'],
    ['unresolved', summary.failed_or_unchecked ?? 0, 'unresolved'],
  ] as const
  if (!total) return <div className="audit-verdictbar is-empty">{status === 'ok' || status === 'no_claims' ? 'No checkable statements were extracted.' : 'The check did not complete; no statement was judged.'}</div>
  return <div className="audit-verdictbar">
    <div className="audit-verdictbar-track" role="img" aria-label={parts.map(([, n, label]) => `${n} ${label}`).join(', ')}>
      {parts.map(([key, n]) => n > 0 && <span key={key} className={`seg-${key}`} style={{ flexGrow: n }} />)}
    </div>
    <p>{parts.filter(([, n]) => n > 0).map(([key, n, label]) => <span key={key} className={`legend-${key}`}><b>{n}</b> {label}</span>)}</p>
  </div>
}
