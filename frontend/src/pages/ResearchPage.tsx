import { useEffect, useState } from 'react'
import { api } from '../api/client'
import { useNavigate } from 'react-router-dom'
import { inputProblem } from '../api/auditHandoff'
import type { AuditHandoff } from '../api/auditHandoff'
import './audit.css'

type Method = 'direct_reader' | 'autonomous_tools' | 'structured_workflow'
type Step = { kind: string; stage?: string; name?: string; status: string; arguments?: unknown; result?: unknown; output?: unknown; action_adapter?: { kind: string }[] }
type Result = { method: Method; status: string; answer: unknown
  model_calls: number; tool_calls: number; elapsed_seconds: number; trace: Step[]
  evidence: { text: string; document_id: string; sentence_id: number }[]
  calls: { usage?: { total_tokens?: number } | null }[]; review_reason?: string }
type Example = { input: { question: string; claim: string; target_title: string; documents: { document_id: string; title: string; sentences: string[] }[] }; results: Record<Method, Result>; provenance: { note: string }; reference: { document_id: string; relation: string; origin: string } }
type StudyReport = { status: string; planned_queries?: number; scope?: string; note?: string; methods?: Record<Method, {
  accepted: { counts: { completed: number; total: number; correct: number; false_accept: number; nonsupport: number; true_accept: number; support: number } }
  workflow_counts: { model_calls: number; reported_tokens: number; sum_elapsed_seconds: number; needs_review: number }
}> }
const methods: Record<Method, string> = { direct_reader: 'Read all documents', autonomous_tools: 'Autonomous tools', structured_workflow: 'Structured workflow' }
function answerField(result: Result | undefined, field: string) {
  const value = result?.answer
  if (!value || typeof value !== 'object' || Array.isArray(value)) return null
  const fieldValue = (value as Record<string, unknown>)[field]
  return typeof fieldValue === 'string' ? fieldValue : null
}

export function ResearchPage() {
  const navigate = useNavigate()
  const [examples, setExamples] = useState<{ id: string; label: string }[]>([])
  const [selected, setSelected] = useState('')
  const [example, setExample] = useState<Example | null>(null)
  const [method, setMethod] = useState<Method>('autonomous_tools')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const [report, setReport] = useState<StudyReport | null>(null)
  async function load(id: string) {
    setSelected(id); setLoading(true); setError(''); setExample(null)
    try { setExample((await api.get(`/api/research/examples/${encodeURIComponent(id)}`)).data) }
    catch { setError('The saved comparison could not be loaded.') }
    finally { setLoading(false) }
  }
  useEffect(() => {
    api.get('/api/research/examples').then(r => {
      setExamples(r.data.examples)
      if (r.data.examples.length) void load(r.data.examples[0].id)
    }).catch(() => setError('Start the local audit service to read the saved research.'))
    api.get('/api/research/results').then(r => setReport(r.data)).catch(() => {})
  }, [])
  const active = example?.results[method]
  const answerText = answerField(active, 'answer')
  function transfer() {
    if (!example || !answerText?.trim()) return
    const docs = example.input.documents
    const handoff: AuditHandoff = { kind: 'research_workflow', question: example.input.question,
      thread_id: `${selected}-${method}`, citations: [], input: { answer: answerText, strategy: 'direct',
        sources: docs.map(d => ({ id: d.document_id, title: d.title, text: d.sentences.join('\n') })) },
      source_map: docs.map(d => ({ id: d.document_id, chunk_id: d.document_id, citation: d.title, external_url: '' })) }
    const problem = inputProblem(handoff.input)
    if (problem) { setError(problem); return }
    navigate('/audit', { state: { handoff } })
  }
  async function download() {
    try {
      // Preserve the verified server JSON, including numeric representation used by its fingerprint.
      const response = await api.get(`/api/research/examples/${encodeURIComponent(selected)}`, { responseType: 'blob' })
      const url = URL.createObjectURL(response.data)
      const a = document.createElement('a'); a.href = url; a.download = `${selected}-comparison.json`; a.click()
      setTimeout(() => URL.revokeObjectURL(url), 1000)
    } catch { setError('The verified comparison could not be exported. Please try again.') }
  }
  return <div className="audit-page">
    <div className="audit-heading"><div><div className="vm-eyebrow">VeritasMed / Controlled research</div>
      <h1>Does the workflow help?</h1><p>One model. The same documents and tools. Every call visible.</p></div>
      <a className="audit-button" href="/audit">Inspect answer claims ↗</a></div>
    <div className="audit-notice">This experiment asks whether a named paper supports a supplied claim. It does not measure clinical correctness or the historical Ask pipeline on open research questions. Saved inference only; loading this page makes no model call.</div>
    <div className="audit-toolbar"><label>Saved comparison <select aria-label="Research example" value={selected} disabled={loading || !examples.length} onChange={e => void load(e.target.value)}>{examples.map(e => <option key={e.id} value={e.id}>{e.label}</option>)}</select></label>
      {example && <button className="audit-button" onClick={download}>Export all traces</button>}</div>
    {error && <div role="alert" className="audit-notice error">{error}</div>}
    {loading && <p role="status">Loading saved calls…</p>}
    {!examples.length && !error && <p>No completed comparison has been published yet.</p>}
    {example && <><div className="audit-source"><div className="vm-eyebrow">Research question</div><h2>{example.input.question}</h2><p className="audit-muted">{example.provenance.note}</p></div>
      <div className="audit-notice"><strong>Public reference: {example.reference.relation}</strong> · document {example.reference.document_id}. {example.reference.origin}. This reference is shown only after inference.</div>
      <div className="research-methods">{(Object.keys(methods) as Method[]).map(key => {
        const r = example.results[key]
        return <button key={key} className={`audit-source research-method ${method === key ? 'active' : ''}`} onClick={() => setMethod(key)}>
          <h3>{methods[key]}</h3><p><strong>{r?.status ?? 'Not run'}</strong> · {answerField(r, 'relation') ?? 'No judgment'}</p>
          {r && <p>{r.model_calls} model calls · {r.tool_calls} tool calls<br />{r.elapsed_seconds.toFixed(1)} s · {r.calls.reduce((sum, c) => sum + (c.usage?.total_tokens ?? 0), 0).toLocaleString()} reported tokens</p>}
        </button>
      })}</div>
      {active && <div className="audit-layout research-layout"><section>
        <div className="audit-section-title"><h2>{methods[method]}</h2><span className="audit-muted">Recorded output</span></div>
        <div className="audit-answer-text">{answerText ?? 'No usable answer was returned.'}</div>
        {!!answerText?.trim() && <button className="audit-button" onClick={transfer}>Audit this answer with the candidate sources ↗</button>}
        <p>{answerField(active, 'explanation')}</p>
        {active.review_reason && <div className="audit-notice">{active.review_reason}</div>}
        {active.status !== 'ok' && <p className="audit-error-text">This result is not counted as a completed accepted judgment. The original draft is retained.</p>}
        <h3>Bound source sentences</h3>{active.evidence.map((s, i) => <blockquote className="audit-evidence-quote" key={i}><small>Document {s.document_id} · sentence {s.sentence_id}</small><p>{s.text}</p></blockquote>)}
        <p className="audit-muted">A bound quotation establishes text location. The public benchmark label, not the system's own verifier, supplies the comparison outcome.</p>
      </section><aside><h2>Execution trace</h2><p className="audit-muted">Tool verification consumes the same six-call model budget. Inspect the actual actions and returned text below.</p>
        {active.trace.some(step => step.action_adapter?.length) && <p className="audit-notice">Some action replies needed format normalization. Their original parsing status is retained below and in the export. Generated tool text after the JSON was discarded; only real tool results supply evidence.</p>}
        {active.trace.map((step, i) => <details className="audit-source" key={i}><summary><b>{i + 1}. {step.name ?? step.stage}</b> · {step.kind} · {step.action_adapter?.length ? `format normalized (raw parse: ${step.status})` : step.status}</summary><pre className="audit-checker-json">{JSON.stringify(step, null, 2)}</pre></details>)}
      </aside></div>}
    </>}
    {report?.status === 'completed' && report.methods && <section className="research-results">
      <div className="vm-eyebrow">Frozen final comparison · {report.planned_queries} source groups</div>
      <h2>What did the experiment find?</h2><p>{report.scope}</p>
      <div className="research-table-wrap"><table className="research-table"><thead><tr><th>Method</th><th>Completed</th><th>Correct binary decisions</th><th>Non-support accepted</th><th>Supported recalled</th><th>Calls / query</th><th>Tokens / query</th></tr></thead><tbody>
        {(Object.keys(methods) as Method[]).map(key => {
          const r = report.methods![key]; const c = r.accepted.counts; const w = r.workflow_counts
          return <tr key={key}><th>{methods[key]}</th><td>{c.completed}/{c.total}</td><td>{c.correct}/{c.total}</td><td>{c.false_accept}/{c.nonsupport}</td><td>{c.true_accept}/{c.support}</td><td>{(w.model_calls / c.total).toFixed(1)}</td><td>{Math.round(w.reported_tokens / c.total).toLocaleString()}</td></tr>
        })}
      </tbody></table></div>
      <p className="audit-muted">{report.note} Counts measure the public text-support task, not clinical reliability. Inspect paired uncertainty intervals and original drafts in the full report below.</p>
    </section>}
    {report != null && <details className="audit-details"><summary>Study results and limits · offline report</summary><pre className="audit-checker-json">{JSON.stringify(report, null, 2)}</pre></details>}
  </div>
}
