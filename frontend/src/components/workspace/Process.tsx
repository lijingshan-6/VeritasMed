// How an answer was produced: a live step indicator while running, and a compact
// record afterwards. Timings come from the recorded event stream.
import type { TimelineNode } from '../../types/ws'
import type { AnswerOut } from '../../types/ws'

const STEP_LABELS: Record<string, string> = {
  resolve_context: 'Understand follow-up', route: 'Plan', retrieve: 'Search', rerank: 'Rank & match study',
  grade: 'Bind evidence', rewrite: 'Rewrite search', generate: 'Write answer', check: 'Self-check',
  append_history: 'Save', summarize: 'Summarize',
}
const label = (node: TimelineNode) => STEP_LABELS[node.name] ?? node.label
const seconds = (ms: number) => ms < 1000 ? `${ms} ms` : `${(ms / 1000).toFixed(1)} s`

function detail(node: TimelineNode): string {
  const d = node.detail ?? {}
  if (node.name === 'retrieve' || node.name === 'rerank') return d.count != null ? `${d.count} passages` : ''
  if (node.name === 'grade') return d.relevance_score != null ? `evidence score ${d.relevance_score.toFixed(2)}` : ''
  if (node.name === 'rewrite') return d.new_query ? `“${d.new_query}”` : ''
  if (node.name === 'check') return d.faithful == null ? '' : d.faithful ? 'passed' : 'asked for a repair'
  if (node.name === 'resolve_context') return d.reason === 'follow_up' ? 'reference resolved' : d.reason ?? ''
  return ''
}

export function LiveProgress({ timeline }: { timeline: TimelineNode[] }) {
  const running = [...timeline].reverse().find(n => n.status === 'running')
  return <div className="ws-live" role="status" aria-live="polite">
    <div className="ws-live-steps">
      {timeline.filter(n => n.name !== 'append_history').map((node, i) =>
        <span key={i} className={`ws-live-step is-${node.status}`}>{label(node)}</span>)}
    </div>
    <p className="ws-live-now"><span className="ws-pulse" aria-hidden="true" />{running ? `${label(running)}…` : 'Starting…'}</p>
  </div>
}

export function ProcessDetails({ timeline, result }: { timeline: TimelineNode[]; result: AnswerOut }) {
  const steps = timeline.filter(n => n.name !== 'append_history')
  const total = steps.reduce((sum, n) => sum + (n.elapsed_ms ?? 0), 0)
  const context = result.conversation_context
  return <details className="ws-process">
    <summary>How this answer was produced <span>{steps.length} steps · {seconds(Math.round(result.latency_ms || total))}</span></summary>
    {context && context.context_turn_ids.length > 0 && <div className="ws-process-context">
      <strong>Follow-up interpreted as</strong>
      <p>{context.resolved_query}</p>
      <small>Earlier answers were used only to understand the question; new evidence was retrieved.</small>
    </div>}
    <ol className="ws-steps">{steps.map((node, i) => <li key={i} className={`is-${node.status}`}>
      <span className="ws-step-name">{label(node)}</span>
      <span className="ws-step-detail">{detail(node)}</span>
      <span className="ws-step-time">{node.elapsed_ms != null ? seconds(node.elapsed_ms) : ''}</span>
    </li>)}</ol>
    {result.rewritten_queries.length > 0 && <p className="ws-process-note">Search rewritten {result.rewritten_queries.length}×: {result.rewritten_queries.map(q => `“${q}”`).join(', ')}</p>}
  </details>
}
