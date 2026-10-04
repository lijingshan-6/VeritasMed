import React, { useEffect, useRef } from 'react'
import { useStore } from '../store'
import { useAgentStream } from '../hooks/useAgentStream'
import { contextFor } from '../conversation/model'
import { isReplayOnly } from '../demo'

export function QueryInput() {
  const { query, setQuery, activeRequest, useContext, setUseContext, hydrated, conversations, threadId, selectedTurnId, selectedRevisionId } = useStore()
  const { send, cancel } = useAgentStream()
  const isStreaming = !!activeRequest
  const conversation = conversations.find(c => c.id === threadId)
  const history = conversation ? contextFor(conversation, selectedTurnId, selectedRevisionId) : { context: [], omitted: 0 }
  const taRef = useRef<HTMLTextAreaElement>(null)

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
      if (hydrated && !isStreaming && query.trim()) send()
    }
  }

  const canSend = hydrated && query.trim().length > 0 && !isStreaming

  if (isReplayOnly) return <div className="ws-replay-note">
    Replay of recorded answers — no new questions here.{' '}
    <a href="https://github.com/lijingshan-6/medrag-agent#ask-your-own-questions" target="_blank" rel="noreferrer">Run it locally to ask your own ↗</a>
  </div>

  const followUp = useContext && history.context.length > 0
  return <div className="ws-composer">
    <div className="ws-composer-box">
      <textarea ref={taRef} value={query} rows={1} disabled={isStreaming || !hydrated}
        onChange={e => setQuery(e.target.value)} onKeyDown={handleKey}
        placeholder={followUp ? 'Ask a follow-up…' : 'Ask about the indexed papers…'} />
      <div className="ws-composer-bar">
        <label className="ws-toggle"><input type="checkbox" checked={useContext} onChange={e => setUseContext(e.target.checked)} />
          Follow up on this conversation{history.context.length ? ` (${history.context.length} ${history.context.length === 1 ? 'turn' : 'turns'})` : ''}</label>
        {useContext && history.omitted > 0 && <span className="ws-composer-note">{history.omitted} older turns left out</span>}
        <button className={`ws-send${isStreaming ? ' is-stop' : ''}`} disabled={!isStreaming && !canSend}
          onClick={isStreaming ? cancel : () => { if (canSend) send() }}>{isStreaming ? 'Stop' : 'Ask'}</button>
      </div>
    </div>
    <p className="ws-disclaimer">Research demo, not medical advice. Answers can be wrong; check the claims and sources.</p>
  </div>
}
