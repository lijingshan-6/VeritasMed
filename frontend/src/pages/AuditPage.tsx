import { useEffect, useState } from 'react'
import type { FormEvent } from 'react'
import { auditExamples, replayAudit, runAudit } from '../api/audit'
import type { AuditClaim, AuditInput, AuditRecord, Catalogue, Span, Strategy } from '../api/audit'
import './audit.css'

const labels: Record<string, string> = {
  supported: 'Supported', contradicted: 'Contradicted', insufficient: 'Insufficient evidence',
  invalid_reference: 'Unresolved quote', invalid_output: 'Invalid model output',
  execution_error: 'Execution failed', not_checked: 'Not checked',
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

export function AuditPage() {
  const [catalogue, setCatalogue] = useState<Catalogue | null>(null)
  const [example, setExample] = useState('')
  const [strategy, setStrategy] = useState<Strategy>('direct')
  const [record, setRecord] = useState<AuditRecord | null>(null)
  const [selected, setSelected] = useState('')
  const [pending, setPending] = useState('')
  const [error, setError] = useState('')
  const [formOpen, setFormOpen] = useState(false)
  const [draft, setDraft] = useState<AuditInput>(emptyInput)

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
    let alive = true
    auditExamples().then(async data => {
      if (!alive) return
      setCatalogue(data)
      const first = data.examples.find(e => e.strategies.direct)
      if (first && data.sources_downloaded) {
        setExample(first.id); setPending('Loading saved audit…')
        try { const value = await replayAudit(first.id, 'direct'); if (alive) show(value) }
        catch (e) { if (alive) setError(message(e)) }
        finally { if (alive) setPending('') }
      }
    }).catch(e => { if (alive) setError(message(e)) })
    return () => { alive = false }
  }, [])

  async function submit(event: FormEvent) {
    event.preventDefault(); setPending('Auditing supplied texts…'); setRecord(null); setError('')
    try { show(await runAudit(draft)); setFormOpen(false) } catch (e) { setError(message(e)) }
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
  const validSpans = audit?.claims.flatMap(c => c.answer_span ? [{ ...c.answer_span, claimId: c.id, category: category(c) }] : []) ?? []
  const models = [...new Set(audit?.calls.flatMap(c => c.transport_metadata?.model_identifiers ?? []) ?? [])]
  const available = catalogue?.examples.filter(e => e.strategies[strategy]) ?? []

  return <div className="audit-page">
    <div className="audit-heading">
      <div><div className="vm-eyebrow">VeritasMed / Textual evidence</div><h1>Inspect the answer. Follow the evidence.</h1>
        <p>Every judgment belongs to a passage. Unchecked text remains visible.</p></div>
      <button className="audit-button primary" disabled={!!pending} onClick={() => setFormOpen(v => !v)}>{formOpen ? 'Close input' : 'Audit your own answer'}</button>
    </div>
    <div className="audit-toolbar">
      <span className="vm-eyebrow">Real saved runs</span>
      <label>Method <select aria-label="Audit method" disabled={!!pending} value={strategy} onChange={e => {
        const value = e.target.value as Strategy; setStrategy(value)
        const next = catalogue?.examples.find(c => c.id === example && c.strategies[value]) ?? catalogue?.examples.find(c => c.strategies[value])
        setExample(next?.id ?? ''); setRecord(null)
        if (next) void load(next.id, value)
      }}><option value="direct">Direct Flash</option><option value="split">Extract → verify each claim</option></select></label>
      <label>Answer <select aria-label="Saved answer" disabled={!!pending || !available.length} value={example} onChange={e => {
        setExample(e.target.value); void load(e.target.value, strategy)
      }}><option value="" disabled>Select a saved answer</option>{available.map(e => <option key={e.id} value={e.id}>RAGTruth #{e.id} · {e.strategies[strategy]}</option>)}</select></label>
      <span className="audit-muted">Public, nonmedical training data · no new API call</span>
    </div>
    {catalogue && !catalogue.sources_downloaded && <div className="audit-notice">Download original texts once to replay: <code>python scripts/verification/answer_benchmark.py download</code>. Then reload this page.</div>}
    {catalogue && !catalogue.examples.length && <div className="audit-notice">No saved run is available yet. You can audit supplied texts using the input below.</div>}
    {error && <div role="alert" className="audit-notice error">{error}</div>}
    {formOpen && <form className="audit-form" onSubmit={submit}>
      <div className="audit-section-title"><h2>Answer + supplied sources</h2>{record && <button type="button" className="audit-button" onClick={() => setDraft(record.input)}>Use the displayed texts</button>}</div>
      <label>Answer to audit <textarea aria-label="Answer to audit" required maxLength={12000} rows={5} value={draft.answer} onChange={e => setDraft({ ...draft, answer: e.target.value })} /></label>
      {draft.sources.map((source, index) => <fieldset key={source.id}><legend>{source.id}</legend>
        <label>Source title <input aria-label={`Source ${index + 1} title`} required maxLength={500} value={source.title} onChange={e => setDraft({ ...draft, sources: draft.sources.map((s, i) => i === index ? { ...s, title: e.target.value } : s) })} /></label>
        <label>Original source text <textarea aria-label={`Source ${index + 1} text`} required maxLength={50000} rows={5} value={source.text} onChange={e => setDraft({ ...draft, sources: draft.sources.map((s, i) => i === index ? { ...s, text: e.target.value } : s) })} /></label>
        {draft.sources.length > 1 && <button type="button" className="audit-button" onClick={() => setDraft({ ...draft, sources: draft.sources.filter((_, i) => i !== index) })}>Remove source</button>}
      </fieldset>)}
      <div className="audit-toolbar">
        <button type="button" className="audit-button" disabled={draft.sources.length >= 4 || !!pending} onClick={() => setDraft({ ...draft, sources: [...draft.sources, { id: `source-${Date.now()}`, title: `Source ${draft.sources.length + 1}`, text: '' }] })}>+ Add source</button>
        <label>Method <select aria-label="New audit method" value={draft.strategy} onChange={e => setDraft({ ...draft, strategy: e.target.value as Strategy })}><option value="direct">Direct Flash</option><option value="split">Extract → verify each claim</option></select></label>
        <button className="audit-button primary" disabled={!!pending}>Run new audit</button>
      </div>
      <p className="audit-muted">Sends these texts to the Flash endpoint configured in your local .env. Split mode makes one extraction call plus a call per claim and can take several minutes. The server does not save this input. Up to 4 sources / 80,000 source characters; no automatic search.</p>
    </form>}
    {pending && <div className="audit-pending" role="status"><span className="audit-pulse" />{pending}<span className="audit-muted">The full result appears when the run finishes.</span></div>}
    {record && audit && <>
      <div className="audit-runline">
        <span className="audit-mode">{record.mode === 'saved' ? 'SAVED INFERENCE' : 'NEW INFERENCE'}</span>
        <span>{audit.strategy === 'direct' ? 'Direct audit' : 'Extract → per-claim verification'}</span>
        <span>{audit.calls.length} {audit.calls.length === 1 ? 'call' : 'calls'} · {audit.elapsed_seconds.toFixed(1)} s recorded</span>
        <span className="audit-muted">{new Date(audit.created_utc).toLocaleString()}</span>
        <button className="audit-button" onClick={exportRecord}>Export audit JSON</button>
      </div>
      <div className="audit-layout">
        <section className="audit-answer-column">
          <div className="vm-eyebrow">Original answer · click an underlined passage</div>
          <div className="audit-answer-text"><LinkedText text={record.input.answer} spans={validSpans} selected={selected} onSelect={selectClaim} /></div>
          <div className="audit-summary">
            <div className="audit-summary-counts">{(['supported', 'contradicted', 'insufficient'] as const).map(k => <span key={k} className={k}><b>{audit.summary[k] ?? 0}</b> {labels[k]}</span>)}<span><b>{audit.summary.failed_or_unchecked ?? 0}</b> failed / unchecked</span></div>
            <p>{audit.checked_coverage.covered_nonspace_characters} / {audit.checked_coverage.total_nonspace_characters} non-space answer characters received a validly anchored judgment. Text coverage does not measure correctness or completeness of meaning.</p>
            <p>Run: <strong>{audit.status}</strong>{audit.claims_at_cap ? ' · Claim limit reached; additional assertions may be omitted.' : ''}. These are model judgments about the supplied texts, not confidence scores or clinical evidence grades.</p>
          </div>
          <div className="audit-section-title"><h2>Claim audit</h2><span className="audit-muted">{audit.claims.length} extracted claims</span></div>
          {!audit.claims.length && <div className="audit-notice">No claims were successfully extracted. The answer is unreviewed.</div>}
          <div className="audit-claims">{audit.claims.map((claim, index) => <article key={claim.id} id={`audit-${claim.id}`} className={`audit-claim ${selected === claim.id ? 'active' : ''}`}>
            <button className="audit-claim-toggle" aria-expanded={selected === claim.id} onClick={() => selectClaim(selected === claim.id ? '' : claim.id, false)}>
              <span className="audit-claim-number">{String(index + 1).padStart(2, '0')}</span><span><span className="audit-claim-quote">{claim.quote}</span><span className={`audit-verdict ${category(claim)}`}>{labels[category(claim)] ?? claim.status}</span></span><span aria-hidden="true">{selected === claim.id ? '−' : '+'}</span>
            </button>
            {selected === claim.id && <div className="audit-claim-body"><p>{claim.explanation || 'No usable judgment was returned.'}</p>
              {claim.status !== 'ok' && <p className="audit-error-text">This claim is not counted as a completed check. A returned relation with an invalid quote is not a pass.</p>}
              {claim.answer_span && <div className="audit-muted">Answer characters {claim.answer_span.start}–{claim.answer_span.end} · end exclusive</div>}
              {claim.evidence.length === 0 ? <p className="audit-muted">No source passage was bound to this judgment. See the full provided texts on the right.</p> : claim.evidence.map((ref, i) => <button key={i} className="audit-evidence-quote" onClick={() => locateEvidence(ref.source_id, ref.start)}>
                <span className="vm-eyebrow">{record.input.sources.find(s => s.id === ref.source_id)?.title ?? ref.source_id} · {ref.start}–{ref.end}</span><q>{ref.text}</q><span className="audit-source-action">Locate in full source ↗</span>
              </button>)}
            </div>}
          </article>)}</div>
          <details className="audit-details"><summary>Uncovered answer text ({audit.checked_coverage.uncovered.length} ranges)</summary><p>No completed claim judgment covers these characters. Some gaps may be punctuation or connective text; coverage alone cannot establish semantic completeness.</p>{audit.checked_coverage.uncovered.map(s => <blockquote key={s.start}><small>{s.start}–{s.end}</small> {s.text}</blockquote>)}</details>
          <details className="audit-details"><summary>Run provenance & execution</summary><p>{record.provenance.note}</p><p>Reported model identifiers: {models.join(', ') || 'unavailable'}. These are provider metadata.</p><code className="audit-hash">Answer SHA-256: {audit.answer_sha256}</code><ol>{audit.calls.map((c, i) => <li key={i}>{c.stage} · {c.status} · {c.elapsed_seconds.toFixed(1)} s · {c.usage?.total_tokens != null ? `${c.usage.total_tokens} reported tokens` : 'usage unavailable'}{c.error_type ? ` · ${c.error_type}` : ''}</li>)}</ol></details>
        </section>
        <aside className="audit-sources-column">
          <div className="audit-section-title"><h2>Provided sources</h2><span className="audit-muted">{record.input.sources.length} {record.input.sources.length === 1 ? 'text' : 'texts'}</span></div>
          <p className="audit-muted">Highlights follow claim {active ? audit.claims.indexOf(active) + 1 : '—'}. Click a marked source passage to select its claim. A reference proves text location, not semantic correctness.</p>
          {record.input.sources.map(source => {
            const refs = audit.claims.flatMap(c => c.status === 'ok' ? c.evidence.filter(r => r.source_id === source.id).map(r => ({ ...r, claimId: c.id, category: category(c) })) : [])
            return <article className="audit-source" id={`audit-source-${source.id}`} key={source.id}>
              <header><span className="vm-eyebrow">{source.id} / supplied text</span><h3>{source.title}</h3></header>
              <div className="audit-source-text"><LinkedText text={source.text} spans={refs} selected={selected} onSelect={selectClaim} /></div>
              <details><summary>Source fingerprint</summary><code className="audit-hash">SHA-256 {audit.source_hashes[source.id]}</code><p>Positions use Unicode code points, with an exclusive end.</p></details>
            </article>
          })}
        </aside>
      </div>
    </>}
    {!record && !pending && <div className="audit-empty"><div className="vm-eyebrow">A traceable judgment starts with the text</div><h2>Bring an answer and its sources.</h2><p>Load a real saved run above, or audit a new answer. Each claim links to exact passages; missing evidence and unfinished checks stay visible.</p></div>}
  </div>
}
