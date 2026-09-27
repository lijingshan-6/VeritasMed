import { useEffect, useRef, useState } from 'react'
import { useStore } from '../store'
import { exportConversation, importConversation } from '../conversation/model'

const statusLabels: Record<string, string> = { complete: 'Answer saved', clarification: 'Clarification', running: 'Answering', failed: 'Failed', cancelled: 'Interrupted' }

export function ConversationHistory() {
  const { conversations, threadId, selectedTurnId, selectedRevisionId, selectRevision, activeRequest, addConversation } = useStore()
  const conversation = conversations.find(c => c.id === threadId)
  const file = useRef<HTMLInputElement>(null)
  const history = useRef<HTMLDivElement>(null)
  const [error, setError] = useState('')
  useEffect(() => {
    const container = history.current
    const selected = container?.querySelector('.selected')
    if (!container || !selected) return
    const box = container.getBoundingClientRect(), item = selected.getBoundingClientRect()
    if (item.top < box.top) container.scrollTop += item.top - box.top
    else if (item.bottom > box.bottom) container.scrollTop += item.bottom - box.bottom
  }, [threadId, selectedTurnId, selectedRevisionId])
  async function download() {
    if (!conversation) return
    try {
      const url = URL.createObjectURL(new Blob([await exportConversation(conversation)], { type: 'application/json' }))
      const link = document.createElement('a'); link.href = url; link.download = `veritasmed-conversation-${conversation.id}.json`
      link.click(); setTimeout(() => URL.revokeObjectURL(url), 1000)
    } catch { setError('Could not export the conversation.') }
  }
  return <section className="vm-conversation-history" aria-label="Conversation history">
    <div className="vm-history-toolbar"><span className="vm-eyebrow">Conversation · {conversation?.turns.length ?? 0} turns</span>
      <button onClick={() => void download()}>Export conversation</button>
      <button onClick={() => file.current?.click()}>Import</button>
      <input ref={file} type="file" accept=".json,application/json" hidden onChange={async e => {
        const input = e.target, selected = input.files?.[0]; if (!selected) return
        try {
          setError('')
          if (selected.size > 25 * 1024 * 1024) throw new Error('Import exceeds 25 MB. The original file has not been changed.')
          const data = await importConversation(await selected.text())
          for (const turn of data.turns) for (const revision of turn.revisions) if (revision.status === 'running') {
            revision.status = 'cancelled'; revision.error = 'Imported incomplete run; no completion assumed.'
          }
          addConversation(data)
        } catch (err) { setError(err instanceof Error ? err.message : 'Could not import this conversation.') }
        finally { input.value = '' }
      }} />
    </div>
    {error && <p role="alert">{error}</p>}
    {conversation?.legacy && !conversation.turns.length && <p>Only this old thread ID was saved. No previous messages are available.</p>}
    <div ref={history} className="vm-history-turns">{conversation?.turns.map((turn, i) => {
      const selected = turn.id === selectedTurnId
      const revision = (selected ? turn.revisions.find(r => r.id === selectedRevisionId) : null) ?? turn.revisions.at(-1)
      if (!revision) return null
      return <article key={turn.id} className={selected ? 'selected' : ''}>
        <button className="vm-turn-select" aria-pressed={selected} onClick={() => selectRevision(turn.id, revision.id)}>
          <span className="vm-eyebrow">{i + 1} · {revision.origin === 'authored_demo' ? 'Authored demo · ' : ''}{statusLabels[revision.status]}{revision.result?.evidence_status === 'partial' ? ' · Partial evidence' : revision.result?.evidence_status === 'insufficient' ? ' · Insufficient evidence' : ''} · {revision.audits.length} {revision.audits.length === 1 ? 'audit' : 'audits'}</span>
          <strong>{turn.question}</strong>
          {!selected && revision.result && <span className="vm-turn-preview">{revision.result.answer.slice(0, 240)}{revision.result.answer.length > 240 ? '…' : ''}</span>}
        </button>
        {selected && turn.revisions.length > 1 && <label>Answer version <select aria-label="Answer version" value={revision.id} onChange={e => selectRevision(turn.id, e.target.value)}>{turn.revisions.map((r, n) => <option key={r.id} value={r.id}>{n + 1} · {r.status} · {r.audits.length} audits</option>)}</select></label>}
      </article>
    })}</div>
    {activeRequest && (activeRequest.conversationId !== threadId || activeRequest.revisionId !== selectedRevisionId) && <p role="status">An answer is still running in another selection. Its result will be saved there. Use Stop below to cancel.</p>}
  </section>
}
