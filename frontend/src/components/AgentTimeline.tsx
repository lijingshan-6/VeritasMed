import React from 'react'
import { useStore } from '../store'
import type { TimelineNode } from '../types/ws'

// ── SVG icon helpers ────────────────────────────────────────────────────────
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
const IconCheck   = (p: { size?: number; sw?: number; style?: React.CSSProperties }) => <I {...p}><path d="m5 12 4 4L19 7"/></I>
const IconAlert   = (p: { size?: number; sw?: number; style?: React.CSSProperties }) => <I {...p}><path d="M12 9v4M12 17h.01"/><path d="M10.3 3.86 1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0Z"/></I>
const IconRefresh = (p: { size?: number; sw?: number; style?: React.CSSProperties }) => <I {...p}><path d="M3 12a9 9 0 0 1 15.5-6.3L21 8M21 3v5h-5M21 12a9 9 0 0 1-15.5 6.3L3 16M3 21v-5h5"/></I>
const IconSpinner = (p: { size?: number; sw?: number; style?: React.CSSProperties }) => <I {...p}><path d="M12 3a9 9 0 1 0 9 9"/></I>
const IconQuote   = (p: { size?: number; sw?: number; style?: React.CSSProperties }) => <I {...p}><path d="M3 21V13c0-4 2-6 6-6M13 21V13c0-4 2-6 6-6"/></I>

function StatusDot({ status }: { status: string }) {
  const base: React.CSSProperties = {
    width: 22, height: 22, borderRadius: 6,
    display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
    flexShrink: 0,
  }
  if (status === 'done') {
    return (
      <div style={{ ...base, background: 'var(--verified-soft)', color: 'var(--verified)' }}>
        <IconCheck size={12} sw={2.4} />
      </div>
    )
  }
  if (status === 'running') {
    return (
      <div style={{ ...base, background: 'var(--accent-soft)', color: 'var(--accent)' }}>
        <span className="vm-spin" style={{ display: 'inline-flex' }}>
          <IconSpinner size={12} sw={2.4} />
        </span>
      </div>
    )
  }
  if (status === 'rewrite') {
    return (
      <div style={{ ...base, background: 'var(--warn-soft)', color: 'var(--warn)' }}>
        <IconRefresh size={12} sw={2.4} />
      </div>
    )
  }
  if (status === 'error') {
    return (
      <div style={{ ...base, background: 'var(--error-soft)', color: 'var(--error)' }}>
        <IconAlert size={12} sw={2.4} />
      </div>
    )
  }
  return (
    <div style={{ ...base, background: 'var(--panel-2)', color: 'var(--faint)', border: '1px solid var(--rule)' }}>
      <span style={{ width: 6, height: 6, borderRadius: '50%', background: 'currentColor' }} />
    </div>
  )
}

function fmtMs(ms: number) {
  if (ms < 1000) return `${ms}ms`
  return `${(ms / 1000).toFixed(2)}s`
}

function TraceNode({ node, isLast, isActive, cumMs }: {
  node: TimelineNode; isLast: boolean; isActive: boolean; cumMs: number
}) {
  const gradeDetail   = node.name === 'grade'   ? (node.detail as { relevance_score?: number } | null) : null
  const rewriteDetail = node.name === 'rewrite'  ? (node.detail as { original?: string; new_query?: string } | null) : null
  const checkDetail   = node.name === 'check'    ? (node.detail as { faithful?: boolean } | null) : null

  return (
    <div style={{ display: 'flex', gap: 12, position: 'relative' }} className="vm-fadeup">
      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', flexShrink: 0 }}>
        <StatusDot status={node.status} />
        {!isLast && (
          <div style={{
            width: 1, flex: 1, marginTop: 4, marginBottom: -4, minHeight: 12,
            background: node.status === 'done' ? 'var(--rule)' : 'var(--rule-soft)',
          }} />
        )}
      </div>

      <div style={{ paddingBottom: 16, flex: 1, minWidth: 0 }}>
        <div style={{ display: 'flex', alignItems: 'baseline', gap: 8, justifyContent: 'space-between' }}>
          <span style={{
            fontSize: 13, fontWeight: 600,
            color: isActive ? 'var(--ink)' : 'var(--ink-soft)',
            letterSpacing: '-0.005em',
            whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis',
            flex: '1 1 auto', minWidth: 0,
          }}>
            {node.label}
          </span>
          {cumMs > 0 && (
            <span className="vm-mono" style={{ fontSize: 10, color: 'var(--faint)', flexShrink: 0 }}>
              +{fmtMs(cumMs)}
            </span>
          )}
        </div>

        {node.summary && (
          <p style={{ margin: '3px 0 0 0', fontSize: 12, lineHeight: 1.5, color: 'var(--muted)' }}>
            {node.summary}
          </p>
        )}

        {/* Relevance bar */}
        {node.name === 'grade' && node.status === 'done' && gradeDetail?.relevance_score != null && (
          <div style={{ marginTop: 8, display: 'flex', alignItems: 'center', gap: 8 }}>
            <div style={{ flex: 1, height: 3, borderRadius: 2, background: 'var(--rule-soft)', overflow: 'hidden' }}>
              <div style={{
                width: `${gradeDetail.relevance_score * 100}%`, height: '100%',
                background: gradeDetail.relevance_score >= 0.6 ? 'var(--verified)' : 'var(--warn)',
              }} />
            </div>
            <span className="vm-mono" style={{ fontSize: 10, color: 'var(--ink-soft)', fontWeight: 600 }}>
              {gradeDetail.relevance_score.toFixed(2)}
            </span>
          </div>
        )}

        {/* Rewrite diff */}
        {node.name === 'rewrite' && node.status !== 'waiting' && rewriteDetail?.new_query && (
          <div style={{ marginTop: 8, fontSize: 11, lineHeight: 1.5, fontFamily: 'var(--mono)' }}>
            {rewriteDetail.original && (
              <div style={{
                padding: '5px 8px', borderRadius: 4,
                background: 'var(--panel-2)', border: '1px solid var(--rule-soft)',
                color: 'var(--muted)', textDecoration: 'line-through',
                textDecorationColor: 'var(--faint)', marginBottom: 4,
              }}>
                {rewriteDetail.original}
              </div>
            )}
            <div style={{
              padding: '5px 8px', borderRadius: 4,
              background: 'var(--accent-soft)', border: '1px solid var(--accent-soft)',
              color: 'var(--accent-ink)',
            }}>
              {rewriteDetail.new_query}
            </div>
          </div>
        )}

        {/* Check result */}
        {node.name === 'check' && node.status === 'done' && checkDetail && (
          <div style={{
            marginTop: 8, padding: '6px 8px', borderRadius: 6,
            background: checkDetail.faithful ? 'var(--verified-soft)' : 'var(--warn-soft)',
            color: checkDetail.faithful ? 'var(--verified)' : 'var(--warn)',
            fontSize: 11, fontWeight: 600, letterSpacing: '0.01em',
            display: 'inline-flex', alignItems: 'center', gap: 6,
          }}>
            {checkDetail.faithful ? <IconCheck size={11} sw={2.4} /> : <IconAlert size={11} sw={2.4} />}
            {checkDetail.faithful ? 'Model self-check passed' : 'Model self-check found issues'}
          </div>
        )}
      </div>
    </div>
  )
}

export function AgentTimeline() {
  const { timeline, isStreaming, activeQuery, result } = useStore()

  const activeIdx  = timeline.findIndex((n) => n.status === 'running')
  const empty      = timeline.length === 0 && !isStreaming
  const threadTitle = activeQuery || (result ? 'Latest answer' : '')
  const totalMs     = timeline.reduce((s, n) => s + (n.elapsed_ms ?? 0), 0)

  // Cumulative elapsed time after each node
  const cumStamps = timeline.reduce<number[]>((acc, n) => {
    acc.push((acc[acc.length - 1] ?? 0) + (n.elapsed_ms ?? 0))
    return acc
  }, [])

  return (
    <aside style={{
      height: '100%', overflowY: 'auto',
      borderRight: '1px solid var(--rule)',
      background: 'var(--canvas)',
      display: 'flex', flexDirection: 'column',
    }}>
      <div style={{
        padding: '18px 20px 14px', borderBottom: '1px solid var(--rule-soft)',
        flexShrink: 0,
      }}>
        <div className="vm-eyebrow" style={{ marginBottom: 4 }}>Reasoning trace</div>
        <div style={{
          fontFamily: 'var(--serif)', fontSize: 17, lineHeight: 1.25,
          color: 'var(--ink)', letterSpacing: '-0.01em',
        }}>
          {threadTitle || 'No active thread'}
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginTop: 8, fontSize: 11 }}>
          <span className="vm-mono" style={{ color: 'var(--faint)' }}>
            {timeline.filter((n) => n.status === 'done').length}/{timeline.length || 7} steps
          </span>
          {totalMs > 0 && (
            <span className="vm-mono" style={{ color: 'var(--faint)' }}>
              · {(totalMs / 1000).toFixed(2)}s total
            </span>
          )}
        </div>
      </div>

      <div style={{ padding: '18px 20px', flex: 1 }}>
        {empty && (
          <div style={{ padding: '32px 8px', textAlign: 'center', color: 'var(--faint)', fontSize: 13 }}>
            <IconQuote size={20} style={{ opacity: 0.4, marginBottom: 10 }} />
            <p style={{ margin: 0, lineHeight: 1.55 }}>
              Each step of the agent's reasoning — query rewriting, retrieval, grading,
              drafting, verification — appears here as it runs.
            </p>
          </div>
        )}

        {timeline.map((node, i) => (
          <TraceNode
            key={`${node.name}-${i}`}
            node={node}
            isLast={i === timeline.length - 1 && !isStreaming}
            isActive={i === activeIdx || (activeIdx === -1 && i === timeline.length - 1)}
            cumMs={cumStamps[i] ?? 0}
          />
        ))}

        {isStreaming && activeIdx === -1 && timeline.length === 0 && (
          <div style={{ display: 'flex', gap: 12 }}>
            <StatusDot status="running" />
            <div style={{ paddingTop: 3, fontSize: 12, color: 'var(--muted)' }} className="vm-pulse">
              Initialising pipeline…
            </div>
          </div>
        )}
      </div>
    </aside>
  )
}
