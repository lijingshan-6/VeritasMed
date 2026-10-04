// The answer to one question: what was asked, the answer itself (one paragraph per
// requested part), the evidence behind each part, and how much of it has been checked.
import { useState } from 'react'
import type { ReactNode } from 'react'
import type { AnswerComponent, AnswerOut } from '../../types/ws'
import type { Revision } from '../../conversation/model'
import { AnnotatedParagraph, buildCiteMap } from '../answer/AnswerText'
import { useStore } from '../../store'

export type Tab = 'answer' | 'check' | 'sources'

const PART_STATE = {
  supported: { tone: 'ok', label: 'Answered' },
  partial: { tone: 'partial', label: 'Partly answered' },
  missing: { tone: 'gap', label: 'Not in the sources' },
} as const

// The self-check names components it was not satisfied with ("C2: …").
export function flaggedParts(result: AnswerOut): Record<string, string> {
  if (result.faithful) return {}
  const flagged: Record<string, string> = {}
  for (const m of result.faithfulness_issues.matchAll(/\b(C\d+):\s*([^]*?)(?=\s+C\d+:|$)/g)) flagged[m[1]] = m[2].trim()
  return flagged
}

export function latestAudit(revision: Revision | undefined) {
  const runs = revision?.audits.filter(a => !a.edited && a.record.audit.status !== 'transport_error') ?? []
  return runs.filter(a => a.record.audit.strategy === 'direct').at(-1) ?? runs.at(-1)
}

export function TurnHeader({ question, result, revision, tab, onTab, actions }: {
  question: string; result: AnswerOut | null; revision?: Revision; tab: Tab; onTab: (tab: Tab) => void
  actions: ReactNode
}) {
  const audit = latestAudit(revision)
  const claims = audit?.record.audit.claims.length
  const sources = new Set(result?.chunks.map(c => c.citation)).size
  const followUp = (result?.conversation_context?.context_turn_ids.length ?? 0) > 0
  return <header className="ws-turn-header">
    <h1 className="ws-question">{question}</h1>
    {result && <p className="ws-meta">
      {followUp && <span>Follow-up</span>}
      <span>{sources} {sources === 1 ? 'source' : 'sources'}</span>
      <span>{(result.latency_ms / 1000).toFixed(0)} s</span>
      {revision?.origin === 'authored_demo' && <span>Authored example</span>}
    </p>}
    {result && !result.conversation_context?.needs_clarification && <div className="ws-tabbar">
      <div role="tablist" className="ws-tabs">
        <button role="tab" aria-selected={tab === 'answer'} onClick={() => onTab('answer')}>Answer</button>
        <button role="tab" aria-selected={tab === 'check'} onClick={() => onTab('check')}>
          Claim check{claims != null && <span className="ws-count">{claims}</span>}</button>
        <button role="tab" className="ws-tab-sources" aria-selected={tab === 'sources'} onClick={() => onTab('sources')}>
          Sources<span className="ws-count">{result.chunks.length}</span></button>
      </div>
      <div className="ws-actions">{actions}</div>
    </div>}
  </header>
}

export function AnswerBody({ result, revision, onCiteClick, onOpenCheck }: {
  result: AnswerOut; revision?: Revision; onCiteClick: (citation: string) => void; onOpenCheck: () => void
}) {
  const [focus, setFocus] = useState('')
  const citeMap = buildCiteMap(result.citations)
  const parts = result.answer_components ?? []
  const flagged = flaggedParts(result)
  const context = result.conversation_context

  if (context?.needs_clarification) return <div className="ws-clarify">
    <h2>Which one do you mean?</h2>
    <p>{context.clarification}</p>
    <small>No evidence was searched. Reply with the study or treatment you mean.</small>
  </div>

  function jump(id: string) {
    setFocus(id)
    document.getElementById(`part-${id}`)?.scrollIntoView({ behavior: 'smooth', block: 'center' })
  }

  return <>
    {parts.length > 1 && <Coverage parts={parts} flagged={flagged} onJump={jump} />}

    <div className="ws-answer">
      {parts.length ? parts.map(part => <AnswerPart key={part.id} part={part} citeMap={citeMap} onCiteClick={onCiteClick}
        focused={focus === part.id} flagged={flagged[part.id]} single={parts.length === 1} />)
        : result.answer.split(/\n\n+/).filter(Boolean).map((text, i) =>
          <AnnotatedParagraph key={i} text={text} citeMap={citeMap} onCiteClick={onCiteClick} isFirst={false} />)}
    </div>

    <StatusFooter result={result} revision={revision} onOpenCheck={onOpenCheck} />
  </>
}

function Coverage({ parts, flagged, onJump }: {
  parts: AnswerComponent[]; flagged: Record<string, string>; onJump: (id: string) => void
}) {
  const answered = parts.filter(p => p.status === 'supported').length
  return <section className="ws-coverage" aria-label="What you asked">
    <header><h2>What you asked</h2><span>{answered} of {parts.length} answered from the sources</span></header>
    <ol>{parts.map(part => {
      const state = PART_STATE[part.status]
      return <li key={part.id}>
        <button onClick={() => onJump(part.id)}>
          <StateIcon tone={state.tone} />
          <span className="ws-coverage-text">{part.requirement}</span>
          <span className={`ws-coverage-state tone-${state.tone}`}>{state.label}{flagged[part.id] ? ' · flagged' : ''}</span>
        </button>
      </li>
    })}</ol>
    <p className="ws-footnote">Split into parts by the model. "Answered" means a source passage was bound to this part, not that the answer is correct — see Claim check.</p>
  </section>
}

function AnswerPart({ part, citeMap, onCiteClick, focused, flagged, single }: {
  part: AnswerComponent; citeMap: Record<string, number>; onCiteClick: (c: string) => void
  focused: boolean; flagged?: string; single: boolean
}) {
  const [open, setOpen] = useState(false)
  const setSelectedChunkId = useStore(s => s.setSelectedChunkId)
  const tone = PART_STATE[part.status].tone
  return <section id={`part-${part.id}`} className={`ws-part tone-${tone}${focused ? ' is-focused' : ''}`}>
    {!single && <h3 className="ws-part-label">{part.requirement}</h3>}
    {part.answer
      ? part.answer.split(/\n\n+/).filter(Boolean).map((text, i) => <AnnotatedParagraph key={i} text={text} citeMap={citeMap} onCiteClick={onCiteClick} isFirst={false} />)
      : null}
    {part.status !== 'supported' && part.gap && <p className="ws-gap"><StateIcon tone={tone} />{part.gap}</p>}
    {flagged && <p className="ws-flag">Self-check: {flagged}</p>}
    {part.evidence.length > 0 && <div className="ws-evidence">
      <button className="ws-evidence-toggle" aria-expanded={open} onClick={() => setOpen(v => !v)}>
        {open ? 'Hide' : 'Show'} evidence · {part.evidence.length} {part.evidence.length === 1 ? 'sentence' : 'sentences'}</button>
      {open && <ul>{part.evidence.map((span, i) => <li key={i}>
        <blockquote>{span.quote}</blockquote>
        <button onClick={() => { setSelectedChunkId(span.chunk_id); onCiteClick(span.citation) }}>
          <span className="ws-cite-chip">{(citeMap[span.citation] ?? 0) + 1}</span>{span.citation} · show in sources</button>
      </li>)}</ul>}
    </div>}
  </section>
}

function StatusFooter({ result, revision, onOpenCheck }: { result: AnswerOut; revision?: Revision; onOpenCheck: () => void }) {
  const audit = latestAudit(revision)?.record.audit
  const s = audit?.summary ?? {}
  const unsupported = (s.contradicted ?? 0) + (s.insufficient ?? 0)
  return <section className="ws-status" aria-label="Checks">
    <button className={`ws-status-item ${result.faithful ? 'tone-ok' : 'tone-partial'}`} title={result.faithfulness_issues || undefined}>
      <StateIcon tone={result.faithful ? 'ok' : 'partial'} />
      <span><strong>Self-check {result.faithful ? 'passed' : 'not satisfied'}</strong>
        <small>{result.regen_count ? `${result.regen_count} targeted ${result.regen_count === 1 ? 'repair' : 'repairs'}` : 'no repair needed'}{result.iterations ? ` · ${result.iterations} search rewrites` : ''}</small></span>
    </button>
    <button className={`ws-status-item ${!audit ? 'tone-idle' : unsupported ? 'tone-gap' : 'tone-ok'}`} onClick={onOpenCheck}>
      <StateIcon tone={!audit ? 'idle' : unsupported ? 'bad' : 'ok'} />
      <span><strong>{audit ? `Claim check: ${s.supported ?? 0} supported${unsupported ? `, ${unsupported} not supported` : ''}` : 'Claims not checked yet'}</strong>
        <small>{audit ? `${audit.strategy === 'atomic_v2' ? 'Atomic v2' : 'Direct'} · ${audit.claims.length} claims${s.failed_or_unchecked ? ` · ${s.failed_or_unchecked} unresolved` : ''}` : 'Open Claim check to verify each statement'}</small></span>
    </button>
  </section>
}

export function StateIcon({ tone }: { tone: string }) {
  const paths: Record<string, ReactNode> = {
    ok: <path d="m7.5 12.5 3 3 6-7" />,
    partial: <path d="M12 7v5m0 4h.01" />,
    gap: <path d="M8 12h8" />,
    bad: <path d="m9 9 6 6m0-6-6 6" />,
    idle: <circle cx="12" cy="12" r="1.5" fill="currentColor" />,
  }
  return <svg className={`ws-icon tone-${tone}`} viewBox="0 0 24 24" width="18" height="18" aria-hidden="true">
    <circle cx="12" cy="12" r="10" />{paths[tone] ?? paths.idle}
  </svg>
}
