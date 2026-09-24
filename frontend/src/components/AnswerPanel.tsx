import { isGuidedDemo } from '../demo'
import React from 'react'
import { useNavigate } from 'react-router-dom'
import { makeAuditHandoff } from '../api/auditHandoff'
import { useStore } from '../store'
import type { AnswerOut } from '../types/ws'

// ── SVG icons ─────────────────────────────────────────────────────────────
function I({ size = 16, sw = 1.6, children, style }: {
  size?: number; sw?: number; children: React.ReactNode; style?: React.CSSProperties
}) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none"
      stroke="currentColor" strokeWidth={sw} strokeLinecap="round"
      strokeLinejoin="round" aria-hidden="true" style={style}>
      {children}
    </svg>
  )
}
const IconCheck     = (p: { size?: number; sw?: number }) => <I {...p}><path d="m5 12 4 4L19 7"/></I>
const IconAlert     = (p: { size?: number; sw?: number }) => <I {...p}><path d="M12 9v4M12 17h.01"/><path d="M10.3 3.86 1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0Z"/></I>
const IconRefresh   = (p: { size?: number; sw?: number }) => <I {...p}><path d="M3 12a9 9 0 0 1 15.5-6.3L21 8M21 3v5h-5M21 12a9 9 0 0 1-15.5 6.3L3 16M3 21v-5h5"/></I>
const IconCopy      = (p: { size?: number; sw?: number }) => <I {...p}><rect x="9" y="9" width="11" height="11" rx="2"/><path d="M5 15V5a2 2 0 0 1 2-2h10"/></I>
const IconBookmark  = (p: { size?: number; sw?: number }) => <I {...p}><path d="M19 21 12 16.5 5 21V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2v16Z"/></I>
const IconSparkle   = (p: { size?: number; sw?: number }) => <I {...p}><path d="M12 3v3M12 18v3M3 12h3M18 12h3M5.6 5.6l2.1 2.1M16.3 16.3l2.1 2.1M5.6 18.4l2.1-2.1M16.3 7.7l2.1-2.1"/></I>
const IconArrowUp   = (p: { size?: number; sw?: number; style?: React.CSSProperties }) => <I {...p}><path d="M12 19V5M6 11l6-6 6 6"/></I>
const IconChevRight = (p: { size?: number; sw?: number; style?: React.CSSProperties }) => <I {...p}><path d="m9 18 6-6-6-6"/></I>

const CITE_VARS = ['--c0','--c1','--c2','--c3','--c4','--c5','--c6','--c7']

// ── Streaming caret ────────────────────────────────────────────────────────
function StreamingCaret() {
  return (
    <span style={{
      display: 'inline-block', width: 8, height: '0.95em',
      verticalAlign: '-0.1em',
      background: 'var(--accent)',
      animation: 'vmCaret 1s steps(2) infinite',
      marginLeft: 2, borderRadius: 1,
    }} />
  )
}

// ── Citation index map ─────────────────────────────────────────────────────
function buildCiteMap(citations: string[]): Record<string, number> {
  const map: Record<string, number> = {}
  citations.forEach((c, i) => { map[c] = i })
  return map
}

// ── Annotated paragraph ────────────────────────────────────────────────────
function AnnotatedParagraph({ text, citeMap, onCiteClick, isFirst }: {
  text: string
  citeMap: Record<string, number>
  onCiteClick: (c: string) => void
  isFirst: boolean
}) {
  const CITE_RE = /\[(PMID:[^\]]+|PMC:[^\]]+|DOI:[^\]]+)\]/g
  const parts: React.ReactNode[] = []
  let last = 0
  let m: RegExpExecArray | null
  while ((m = CITE_RE.exec(text)) !== null) {
    if (m.index > last) parts.push(text.slice(last, m.index))
    const citeStr = m[1]
    const idx = citeMap[citeStr]
    const colorVar = idx != null ? CITE_VARS[idx % CITE_VARS.length] : '--accent'
    parts.push(
      <span
        key={m.index}
        className="vm-cite"
        style={{ '--cite-color': `var(${colorVar})` } as React.CSSProperties}
        onClick={(e) => { e.stopPropagation(); onCiteClick(citeStr) }}
        title={citeStr}
        role="button"
        tabIndex={0}
      >
        {idx != null ? idx + 1 : '?'}
      </span>
    )
    last = m.index + m[0].length
  }
  if (last < text.length) parts.push(text.slice(last))
  return (
    <p className={isFirst ? 'vm-dropcap' : undefined}>
      {parts}
    </p>
  )
}

// ── Toolbar button ─────────────────────────────────────────────────────────
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
function EvidenceCoverage({ result, onCiteClick }: { result: AnswerOut; onCiteClick: (c: string) => void }) {
  const setSelectedChunkId = useStore((state) => state.setSelectedChunkId)
  if (!result.evidence_status) return null
  const labels = { complete: 'Evidence covers the question', partial: 'Partially covered', insufficient: 'Insufficient evidence' }
  const componentLabels = { supported: 'Source identified', partial: 'Partial support', missing: 'Evidence gap' }
  return (
    <section aria-label="Evidence coverage" style={{ margin: '0 0 26px', padding: '16px 18px', border: '1px solid var(--rule)', borderRadius: 8, background: 'var(--panel-2)' }}>
      <div className="vm-eyebrow" style={{ color: result.evidence_status === 'complete' ? 'var(--verified)' : 'var(--warn)' }}>
        {isGuidedDemo ? 'Illustrative coverage · ' : ''}{labels[result.evidence_status]}
      </div>
      <p style={{ margin: '8px 0', fontSize: 12, lineHeight: 1.6, color: 'var(--muted)' }}>
        Coverage reflects the retrieved passages and model assessment; it is not a correctness score.
      </p>
      {result.evidence_gap && <p style={{ fontSize: 13, lineHeight: 1.6, color: 'var(--ink-soft)' }}>{result.evidence_gap}</p>}
      {result.answer_components?.map((component) => (
        <details key={component.id} style={{ borderTop: '1px solid var(--rule)', padding: '10px 0 4px' }}>
          <summary style={{ cursor: 'pointer', fontSize: 13, lineHeight: 1.6, color: 'var(--ink-soft)' }}>
            {component.requirement}
            <span style={{ display: 'block', fontSize: 10, marginLeft: 16, color: 'var(--muted)' }}>{componentLabels[component.status]}</span>
          </summary>
          {component.gap && <p style={{ fontSize: 12, lineHeight: 1.6 }}>{component.gap}</p>}
          {component.evidence.map((span, i) => (
            <blockquote key={`${span.chunk_id}-${i}`} style={{ margin: '12px 0 8px', paddingLeft: 12, borderLeft: '2px solid var(--accent)', fontSize: 12, lineHeight: 1.65, color: 'var(--ink-soft)' }}>
              {span.quote}
              <button onClick={() => { onCiteClick(span.citation); setSelectedChunkId(span.chunk_id) }}
                style={{ display: 'block', padding: '8px 0', background: 'transparent', color: 'var(--accent)', fontSize: 11 }}>
                View source · {span.citation}
              </button>
            </blockquote>
          ))}
        </details>
      ))}
    </section>
  )
}

// ── Verification mark ──────────────────────────────────────────────────────
function VerificationMark({ result }: { result: AnswerOut }) {
  const ok = result.faithful
  return (
    <div style={{
      marginTop: 36, padding: '18px 22px',
      border: `1px solid ${ok ? 'var(--verified)' : 'var(--warn)'}`,
      borderRadius: 4,
      background: ok ? 'var(--verified-soft)' : 'var(--warn-soft)',
      position: 'relative',
    }}>
      <div style={{
        position: 'absolute', top: -1, left: -1,
        width: 28, height: 28,
        background: ok ? 'var(--verified)' : 'var(--warn)',
        color: 'var(--panel)',
        display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
        borderRadius: '3px 0 8px 0',
      }}>
        {ok ? <IconCheck size={14} sw={2.6} /> : <IconAlert size={14} sw={2.4} />}
      </div>

      <div style={{ marginLeft: 36 }}>
        <div style={{
          fontFamily: 'var(--serif)', fontStyle: 'italic',
          fontSize: 18, lineHeight: 1.2,
          color: ok ? 'var(--verified)' : 'var(--warn)',
        }}>
          {isGuidedDemo ? 'Illustrative evidence-check result' : ok ? 'Model evidence check passed' : 'Evidence check did not pass'}
        </div>

        {!ok && result.faithfulness_issues && (
          <p style={{ margin: '6px 0 0 0', fontSize: 13, color: 'var(--ink-soft)', lineHeight: 1.5 }}>
            {result.faithfulness_issues}
          </p>
        )}

        <div style={{ marginTop: 12, display: 'flex', flexWrap: 'wrap', gap: '4px 22px', fontSize: 11, color: 'var(--muted)' }}>
          <Metric label="rewrites"      value={String(result.iterations)} />
          <Metric label="regenerations" value={String(result.regen_count)} />
          <Metric label="elapsed"       value={isGuidedDemo ? "illustrative" : `${(result.latency_ms / 1000).toFixed(2)}s`} />
          <Metric label="verifier"      value={isGuidedDemo ? "preset example" : "configured LLM"} />
        </div>
      </div>
    </div>
  )
}

function Metric({ label, value }: { label: string; value: string }) {
  if (!value) return null
  return (
    <div style={{ display: 'inline-flex', flexDirection: 'column', gap: 0 }}>
      <span className="vm-eyebrow" style={{ fontSize: 9, letterSpacing: '0.16em', color: 'var(--faint)' }}>
        {label}
      </span>
      <span className="vm-mono" style={{ fontSize: 12, color: 'var(--ink-soft)', fontWeight: 600 }}>
        {value}
      </span>
    </div>
  )
}

// ── Sources strip ──────────────────────────────────────────────────────────
function SourcesStrip({
  result,
  onCiteClick,
}: {
  result: AnswerOut
  onCiteClick: (c: string) => void
}) {
  return (
    <div style={{ marginTop: 32 }}>
      <div className="vm-eyebrow" style={{ marginBottom: 10 }}>
        Sources cited · {result.citations.length}
      </div>
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
        {result.citations.map((c: string, i: number) => {
          const chunk = result.chunks.find((ch: AnswerOut['chunks'][0]) => ch.citation === c)
          const colorVar = CITE_VARS[i % CITE_VARS.length]
          const ext = chunk as typeof chunk & { journal?: string; year?: number }
          return (
            <button
              key={c}
              onClick={() => onCiteClick(c)}
              style={{
                display: 'inline-flex', alignItems: 'center', gap: 8,
                padding: '6px 11px 6px 8px',
                border: '1px solid var(--rule)',
                borderRadius: 6,
                background: 'var(--panel)',
                color: 'var(--ink-soft)',
                fontSize: 11, textAlign: 'left',
                maxWidth: 320, transition: 'all 120ms',
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.background = 'var(--panel-2)'
                e.currentTarget.style.borderColor = `var(${colorVar})`
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.background = 'var(--panel)'
                e.currentTarget.style.borderColor = 'var(--rule)'
              }}
            >
              <span style={{
                fontFamily: 'var(--serif)', fontStyle: 'italic',
                color: `var(${colorVar})`, fontSize: 13, lineHeight: 1,
                width: 16, textAlign: 'center', fontWeight: 500,
              }}>
                {i + 1}
              </span>
              <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                <span className="vm-mono" style={{ color: 'var(--faint)', fontSize: 10 }}>{c}</span>
                {ext && (ext.journal || ext.year) && (
                  <span style={{ marginLeft: 6, color: 'var(--ink-soft)' }}>
                    {ext.journal}{ext.year ? ` · ${ext.year}` : ''}
                  </span>
                )}
              </span>
            </button>
          )
        })}
      </div>
    </div>
  )
}

// ── Follow-ups ─────────────────────────────────────────────────────────────
function FollowUps({ items, onPick }: { items: string[]; onPick: (q: string) => void }) {
  return (
    <div style={{ marginTop: 36 }}>
      <div className="vm-eyebrow" style={{ marginBottom: 10 }}>
        <span style={{ display: 'inline-flex', alignItems: 'center', gap: 6 }}>
          <IconSparkle size={11} sw={2} /> Example questions (independent)
        </span>
      </div>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
        {items.map((q, i) => (
          <button
            key={i}
            onClick={() => onPick(q)}
            style={{
              display: 'flex', alignItems: 'center', gap: 10,
              padding: '11px 4px',
              borderTop: i === 0 ? '1px solid var(--rule)' : 'none',
              borderBottom: '1px solid var(--rule)',
              background: 'transparent',
              color: 'var(--ink-soft)',
              fontSize: 14, fontFamily: 'var(--serif)',
              letterSpacing: '-0.005em',
              textAlign: 'left', lineHeight: 1.4,
              transition: 'color 120ms',
            }}
            onMouseEnter={(e) => e.currentTarget.style.color = 'var(--accent)'}
            onMouseLeave={(e) => e.currentTarget.style.color = 'var(--ink-soft)'}
          >
            <IconArrowUp size={13} sw={2} style={{ transform: 'rotate(45deg)', color: 'var(--faint)', flexShrink: 0 }} />
            <span style={{ flex: 1 }}>{q}</span>
            <IconChevRight size={13} sw={2} style={{ color: 'var(--faint)', flexShrink: 0 }} />
          </button>
        ))}
      </div>
    </div>
  )
}

// ── Empty state ────────────────────────────────────────────────────────────
function EmptyState({ suggestedQueries, onPickQuery }: {
  suggestedQueries: string[]
  onPickQuery: (q: string) => void
}) {
  return (
    <div style={{
      height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center',
      padding: 40,
    }}>
      <div style={{ maxWidth: 560, textAlign: 'center' }}>
        <div style={{
          fontFamily: 'var(--serif)', fontSize: 56, lineHeight: 1, marginBottom: 4,
          color: 'var(--ink)', letterSpacing: '-0.03em',
        }}>
          <span style={{ fontStyle: 'italic' }}>Veritas</span>
          <span style={{ color: 'var(--accent)' }}>Med</span>
        </div>
        <div className="vm-eyebrow" style={{ marginBottom: 24 }}>Evidence-grounded literature Q&amp;A</div>

        <p style={{
          fontFamily: 'var(--serif)', fontSize: 19, lineHeight: 1.5,
          color: 'var(--ink-soft)', maxWidth: 480, margin: '0 auto 36px',
          letterSpacing: '-0.005em',
        }}>
          Ask a standalone literature question. Inspect retrieved passages,
          follow citations to their sources, and review the model’s evidence check.
          The bundled examples use labelled summaries, not original article text.
        </p>

        <div className="vm-eyebrow" style={{ marginBottom: 12 }}>Try a query</div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 6, textAlign: 'left' }}>
          {suggestedQueries.slice(0, 4).map((q, i) => (
            <button
              key={i}
              onClick={() => onPickQuery(q)}
              style={{
                display: 'flex', alignItems: 'center', gap: 12,
                padding: '12px 14px',
                background: 'var(--panel)', border: '1px solid var(--rule)',
                borderRadius: 8,
                color: 'var(--ink-soft)',
                fontSize: 14, fontFamily: 'var(--serif)',
                lineHeight: 1.4, letterSpacing: '-0.005em',
                transition: 'all 120ms', textAlign: 'left',
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.borderColor = 'var(--accent)'
                e.currentTarget.style.color = 'var(--ink)'
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.borderColor = 'var(--rule)'
                e.currentTarget.style.color = 'var(--ink-soft)'
              }}
            >
              <span className="vm-mono" style={{ fontSize: 10, color: 'var(--faint)', width: 16 }}>
                0{i + 1}
              </span>
              <span style={{ flex: 1 }}>{q}</span>
              <IconChevRight size={14} sw={2} style={{ color: 'var(--faint)' }} />
            </button>
          ))}
        </div>
      </div>
    </div>
  )
}

// ── AnswerPanel ────────────────────────────────────────────────────────────
export function AnswerPanel({
  query,
  suggestedQueries,
  onCiteClick,
  onPickQuery,
}: {
  query: string
  suggestedQueries: string[]
  onCiteClick: (c: string) => void
  onPickQuery: (q: string) => void
}) {
  const { result, isStreaming, errorMessage } = useStore()
  const [copyLabel, setCopyLabel] = React.useState('Copy')
  const [auditError, setAuditError] = React.useState('')
  const navigate = useNavigate()
  function openAudit() {
    if (!result || isStreaming) return
    try {
      const handoff = makeAuditHandoff(result, query, isGuidedDemo)
      navigate('/audit', { state: { handoff } })
    } catch (e) { setAuditError(e instanceof Error ? e.message : 'Could not transfer this answer.') }
  }
  function downloadAnswer() {
    if (!result) return
    const text = `${isGuidedDemo ? 'GUIDED DEMO — authored fixed example; no live model.\n\n' : ''}# ${query}\n\n${result.answer}\n\nResearch demonstration; not clinical advice.\n`
    const url = URL.createObjectURL(new Blob([text], { type: 'text/markdown;charset=utf-8' }))
    const link = document.createElement('a')
    link.href = url
    link.download = 'veritasmed-answer.md'
    link.click()
    setTimeout(() => URL.revokeObjectURL(url), 1000)
  }

  if (!result && !isStreaming && !errorMessage) {
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
    <div style={{ height: '100%', overflowY: 'auto' }}>
      <div style={{
        maxWidth: 720, margin: '0 auto',
        padding: 'clamp(28px, 4vw, 56px) clamp(24px, 4vw, 56px) 80px',
      }}>
        {/* Question echo */}
        {query && (
          <div style={{ marginBottom: 36 }} className="vm-fadeup">
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
            display: 'flex', alignItems: 'center', gap: 12, marginBottom: 24,
            paddingBottom: 12, borderBottom: '1px solid var(--rule)',
          }}>
            <span className="vm-eyebrow">Answer</span>
            <span style={{ flex: 1 }} />
            {!isStreaming && <ToolbarButton label="Audit" onClick={openAudit}><IconCheck size={13} sw={2} /></ToolbarButton>}
            <ToolbarButton label={copyLabel} onClick={() => { navigator.clipboard.writeText(result.answer).then(() => setCopyLabel("Copied")).catch(() => setCopyLabel("Copy failed")) }}><IconCopy size={13} sw={2} /></ToolbarButton>
            <ToolbarButton label="Download" onClick={downloadAnswer}><IconBookmark size={13} sw={2} /></ToolbarButton>
            <ToolbarButton label="Re-run" onClick={() => onPickQuery(query)}><IconRefresh size={13} sw={2} /></ToolbarButton>
          </div>
        )}

        {auditError && <p role="alert" style={{ color: 'var(--error)', fontSize: 13 }}>{auditError}</p>}

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

        {result && <EvidenceCoverage result={result} onCiteClick={onCiteClick} />}

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

        {result && <VerificationMark result={result} />}
        {result && <SourcesStrip result={result} onCiteClick={onCiteClick} />}
        {result && <FollowUps items={suggestedQueries} onPick={onPickQuery} />}
      </div>
    </div>
  )
}
