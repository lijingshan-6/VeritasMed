import React, { useEffect, useRef, useState } from 'react'
import { useStore } from '../store'
import { useAgentStream } from '../hooks/useAgentStream'
import { fetchCorpusStats } from '../api/client'
import type { CorpusStats } from '../types'
import { contextFor } from '../conversation/model'
import { isReplayOnly } from '../demo'

// ── SVG icons ─────────────────────────────────────────────────────────────
function I({ size = 16, sw = 1.6, children }: { size?: number; sw?: number; children: React.ReactNode }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none"
      stroke="currentColor" strokeWidth={sw} strokeLinecap="round"
      strokeLinejoin="round" aria-hidden="true">
      {children}
    </svg>
  )
}
const IconArrowUp  = (p: { size?: number; sw?: number }) => <I {...p}><path d="M12 19V5M6 11l6-6 6 6"/></I>
const IconStop     = (p: { size?: number; sw?: number }) => <I {...p}><rect x="6" y="6" width="12" height="12" rx="1.5"/></I>
const IconDatabase = (p: { size?: number; sw?: number }) => <I {...p}><ellipse cx="12" cy="5" rx="8" ry="3"/><path d="M4 5v6c0 1.66 3.58 3 8 3s8-1.34 8-3V5M4 11v6c0 1.66 3.58 3 8 3s8-1.34 8-3v-6"/></I>

// ── QueryInput ─────────────────────────────────────────────────────────────
export function QueryInput() {
  const { query, setQuery, activeRequest, useContext, setUseContext, hydrated, conversations, threadId, selectedTurnId, selectedRevisionId } = useStore()
  const { send, cancel } = useAgentStream()
  const isStreaming = !!activeRequest
  const conversation = conversations.find(c => c.id === threadId)
  const history = conversation ? contextFor(conversation, selectedTurnId, selectedRevisionId) : { context: [], omitted: 0 }
  const [stats, setStats] = useState<CorpusStats | null>(null)
  const [focused, setFocused] = useState(false)
  const taRef = useRef<HTMLTextAreaElement>(null)

  useEffect(() => {
    if (!isReplayOnly) fetchCorpusStats().then(setStats).catch(() => null)
  }, [])

  // Auto-grow textarea
  useEffect(() => {
    const ta = taRef.current
    if (!ta) return
    ta.style.height = 'auto'
    ta.style.height = Math.min(160, Math.max(24, ta.scrollHeight)) + 'px'
  }, [query])

  function handleKey(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      if (hydrated && !isStreaming && query.trim()) {
        send()
      }
    }
  }

  const canSend = hydrated && query.trim().length > 0 && !isStreaming

  if (isReplayOnly) return <div className="vm-replay-composer">
    <strong>Saved conversation replay</strong>
    <span>Select a recorded question above. Answers, sources and audits belong to that original run.</span>
    <a href="https://github.com/lijingshan-6/medrag-agent#ask-your-own-questions" target="_blank" rel="noreferrer">Set up live questions and follow-ups ↗</a>
  </div>

  return (
    <div style={{
      padding: '14px 32px 20px',
      background: 'var(--canvas)',
      flexShrink: 0,
    }}>
      <div style={{
        maxWidth: 1200, margin: '0 auto',
        background: 'var(--panel)',
        border: `1px solid ${focused ? 'var(--accent)' : 'var(--rule)'}`,
        borderRadius: 12,
        transition: 'border-color 160ms, box-shadow 160ms',
        boxShadow: focused
          ? '0 0 0 4px var(--accent-soft), var(--shadow-float)'
          : 'var(--shadow-float)',
      }}>
        {/* Textarea */}
        <div style={{ padding: '14px 18px 6px' }}>
          <textarea
            ref={taRef}
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={handleKey}
            onFocus={() => setFocused(true)}
            onBlur={() => setFocused(false)}
            disabled={isStreaming || !hydrated}
            rows={1}
            placeholder="Ask a literature question — enter to send, shift+enter for a new line"
            style={{
              width: '100%', resize: 'none',
              border: 'none', outline: 'none', background: 'transparent',
              fontFamily: 'var(--serif)',
              fontSize: 18, lineHeight: 1.4,
              color: 'var(--ink)',
              letterSpacing: '-0.005em',
              minHeight: 24, maxHeight: 160,
            }}
          />
        </div>

        {/* Controls strip */}
        <div style={{
          display: 'flex', alignItems: 'center', gap: 10,
          padding: '8px 12px 10px 14px',
          borderTop: '1px solid var(--rule-soft)',
        }}>
          <span className="vm-mono" style={{ fontSize: 11, color: "var(--muted)" }}>Evidence + self-check</span>
          {<label className="vm-context-toggle"><input type="checkbox" checked={useContext} onChange={e => setUseContext(e.target.checked)} /> Use selected history ({history.context.length} turns)</label>}
          {useContext && history.omitted > 0 && <span role="note">{history.omitted} older turns omitted; no partial turns</span>}

          {stats && (
            <span className="vm-mono" style={{
              marginLeft: 'auto',
              fontSize: 10.5, color: 'var(--faint)',
              display: 'inline-flex', alignItems: 'center', gap: 6,
            }}>
              <IconDatabase size={11} sw={2} />
              {stats.total_chunks.toLocaleString()} chunks · {stats.embedding_model}
            </span>
          )}

          <button
            onClick={isStreaming ? cancel : () => { if (canSend) { send() } }}
            disabled={!isStreaming && !canSend}
            style={{
              display: 'inline-flex', alignItems: 'center', gap: 6,
              padding: '7px 12px 7px 14px',
              borderRadius: 8, border: '1px solid transparent',
              background: isStreaming ? 'var(--error)' : canSend ? 'var(--ink)' : 'var(--rule)',
              color: isStreaming ? 'white' : canSend ? 'var(--canvas)' : 'var(--faint)',
              fontSize: 12, fontWeight: 600, letterSpacing: '0.01em',
              cursor: isStreaming || canSend ? 'pointer' : 'not-allowed',
              transition: 'all 120ms',
              marginLeft: stats ? 0 : 'auto',
            }}
          >
            {isStreaming
              ? <><IconStop size={11} sw={2.2} /> Stop</>
              : <>Send <IconArrowUp size={11} sw={2.4} /></>}
          </button>
        </div>
      </div>
    </div>
  )
}
