import { StreamingCaret, buildCiteMap, AnnotatedParagraph } from './answer/AnswerText'
import { EvidenceCoverage, VerificationMark, SourcesStrip } from './answer/AnswerEvidence'
import { FollowUps, EmptyState } from './answer/Suggestions'
import { IconCheck, IconCopy, IconBookmark, IconRefresh } from './answer/Icons'
import { isReplayOnly } from '../demo'
import React from 'react'
import { makeAuditHandoff } from '../api/auditHandoff'
import type { AuditHandoff } from '../api/auditHandoff'
import { useStore } from '../store'

function ToolbarButton({ children, label, onClick }: { children: React.ReactNode; label: string; onClick: () => void }) {
  return (
    <button onClick={onClick}
      style={{
        display: 'inline-flex', alignItems: 'center', gap: 5,
        padding: '5px 9px', borderRadius: 6,
        background: 'transparent', color: 'var(--muted)',
        border: '1px solid transparent',
        fontSize: 11, fontWeight: 500,
        transition: 'all 120ms',
      }}
      onMouseEnter={(e) => {
        e.currentTarget.style.background = 'var(--panel-2)'
        e.currentTarget.style.borderColor = 'var(--rule)'
        e.currentTarget.style.color = 'var(--ink-soft)'
      }}
      onMouseLeave={(e) => {
        e.currentTarget.style.background = 'transparent'
        e.currentTarget.style.borderColor = 'transparent'
        e.currentTarget.style.color = 'var(--muted)'
      }}
    >
      {children} {label}
    </button>
  )
}

// Evidence coverage describes the retrieved material, not clinical certainty.

export function AnswerPanel({
  query,
  suggestedQueries,
  onCiteClick,
  onPickQuery,
  onAudit,
  onRegenerate,
  guided,
}: {
  query: string
  suggestedQueries: string[]
  onCiteClick: (c: string) => void
  onPickQuery: (q: string) => void
  onAudit: (handoff: AuditHandoff) => void
  onRegenerate?: () => void
  guided: boolean
}) {
  const { result, isStreaming, errorMessage } = useStore()
  const [copyLabel, setCopyLabel] = React.useState('Copy')
  const [auditError, setAuditError] = React.useState('')
  function openAudit() {
    if (!result || isStreaming) return
    try {
      const handoff = makeAuditHandoff(result, query, guided)
      onAudit(handoff)
    } catch (e) { setAuditError(e instanceof Error ? e.message : 'Could not transfer this answer.') }
  }
  function downloadAnswer() {
    if (!result) return
    const text = `${guided ? 'GUIDED DEMO — authored fixed example; no live model.\n\n' : ''}# ${query}\n\n${result.answer}\n\nResearch demonstration; not clinical advice.\n`
    const url = URL.createObjectURL(new Blob([text], { type: 'text/markdown;charset=utf-8' }))
    const link = document.createElement('a')
    link.href = url
    link.download = 'veritasmed-answer.md'
    link.click()
    setTimeout(() => URL.revokeObjectURL(url), 1000)
  }

  if (!result && !isStreaming && !errorMessage) {
    if (isReplayOnly) return <div className="vm-replay-empty"><h2>Explore a recorded medical conversation</h2><p>Choose one of the saved conversations above. Follow each question, inspect its original sources, and open the attached claim audit.</p><p>These are actual model outputs, including incomplete judgments. Loading them makes no model call.</p></div>
    return <EmptyState suggestedQueries={suggestedQueries} onPickQuery={onPickQuery} />
  }

  if (errorMessage) {
    return (
      <div style={{ height: '100%', display: 'grid', placeItems: 'center', padding: 32 }}>
        <div style={{
          maxWidth: 480, padding: '18px 22px',
          border: '1px solid var(--error)', borderRadius: 8,
          background: 'var(--error-soft)',
        }}>
          <div style={{
            fontFamily: 'var(--serif)', fontSize: 20, fontStyle: 'italic',
            color: 'var(--error)', marginBottom: 4,
          }}>
            Something went wrong
          </div>
          <p className="vm-mono" style={{ margin: 0, fontSize: 12, color: 'var(--ink-soft)' }}>
            {errorMessage}
          </p>
        </div>
      </div>
    )
  }

  const displayText = result?.answer ?? ''
  const citations   = result?.citations ?? []
  const citeMap     = buildCiteMap(citations)
  const paragraphs  = displayText.split(/\n\n+/).filter(Boolean)

  return (
    <div>
      <div style={{
        maxWidth: 720, margin: '0 auto',
        padding: '28px clamp(24px, 3vw, 44px) 60px',
      }}>
        {/* Question echo */}
        {query && (
          <div style={{ marginBottom: 24 }} className="vm-fadeup">
            <div className="vm-eyebrow" style={{ marginBottom: 8 }}>Question</div>
            <div style={{
              fontFamily: 'var(--serif)', fontStyle: 'italic',
              fontSize: 22, lineHeight: 1.35, color: 'var(--ink-soft)',
              letterSpacing: '-0.005em',
            }}>
              {query}
            </div>
          </div>
        )}

        {/* Toolbar */}
        {result && (
          <div style={{
            display: 'flex', flexWrap: 'wrap', alignItems: 'center', gap: 12, marginBottom: 24,
            paddingBottom: 12, borderBottom: '1px solid var(--rule)',
          }}>
            <span className="vm-eyebrow">Answer</span>
            <span style={{ flex: 1 }} />
            {!isStreaming && !result.conversation_context?.needs_clarification && <ToolbarButton label="Audit" onClick={openAudit}><IconCheck size={13} sw={2} /></ToolbarButton>}
            <ToolbarButton label={copyLabel} onClick={() => { navigator.clipboard.writeText(result.answer).then(() => setCopyLabel("Copied")).catch(() => setCopyLabel("Copy failed")) }}><IconCopy size={13} sw={2} /></ToolbarButton>
            <ToolbarButton label="Download" onClick={downloadAnswer}><IconBookmark size={13} sw={2} /></ToolbarButton>
            {onRegenerate && <ToolbarButton label="Re-run" onClick={onRegenerate}><IconRefresh size={13} sw={2} /></ToolbarButton>}
          </div>
        )}

        {auditError && <p role="alert" style={{ color: 'var(--error)', fontSize: 13 }}>{auditError}</p>}
        {result?.conversation_context && <details className="vm-context-details"><summary>{result.conversation_context.needs_clarification ? 'Clarification needed' : 'Question interpretation'} · {result.conversation_context.context_turn_ids.length} prior turns used</summary>
          <p>{result.conversation_context.resolved_query || result.conversation_context.clarification}</p>
          <p>Supplied: {result.conversation_context.supplied_turn_ids.length} turns · omitted: {result.conversation_context.omitted_context} · resolver: {(result.conversation_context.elapsed_ms / 1000).toFixed(1)}s</p>
          <p>Prior answers help interpret the question. This answer requires newly retrieved evidence.</p>
          <details><summary>Resolution record</summary><pre>{JSON.stringify(result.conversation_context, null, 2)}</pre></details>
        </details>}

        {/* Streaming placeholder */}
        {isStreaming && !displayText && (
          <div style={{
            color: 'var(--muted)', fontFamily: 'var(--serif)',
            fontSize: 21, fontStyle: 'italic',
          }}>
            <span className="vm-pulse">Composing answer</span>
            <StreamingCaret />
          </div>
        )}

        {result && !result.conversation_context?.needs_clarification && <EvidenceCoverage result={result} guided={guided} onCiteClick={onCiteClick} />}

        {/* Prose body */}
        <div className="vm-prose">
          {paragraphs.map((para, i) => (
            <AnnotatedParagraph
              key={i}
              text={para}
              citeMap={citeMap}
              onCiteClick={onCiteClick}
              isFirst={i === 0}
            />
          ))}
          {isStreaming && displayText && <StreamingCaret />}
        </div>

        {result && !result.conversation_context?.needs_clarification && <VerificationMark result={result} guided={guided} />}
        {result && <SourcesStrip result={result} onCiteClick={onCiteClick} />}
        {result && suggestedQueries.length > 0 && <FollowUps items={suggestedQueries} onPick={onPickQuery} />}
      </div>
    </div>
  )
}
