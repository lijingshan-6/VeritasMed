// Conversations and their turns. Recorded examples load from static files in replay mode,
// or from the API in live mode; both become ordinary conversations in local storage.
import { useEffect, useRef, useState } from 'react'
import { api } from '../../api/client'
import { exportConversation, importConversation } from '../../conversation/model'
import type { Conversation, Revision } from '../../conversation/model'
import { isReplayOnly } from '../../demo'
import { replayCatalogue, replayConversation } from '../../replay/corpus'
import type { CatalogueEntry } from '../../replay/corpus'
import { useStore } from '../../store'

const catalogue = () => isReplayOnly ? replayCatalogue()
  : api.get('/api/conversations/examples').then(({ data }) => data.examples as CatalogueEntry[])
const recording = async (entry: CatalogueEntry) => isReplayOnly ? replayConversation(entry)
  : (await api.get('/api/conversations/examples/' + encodeURIComponent(entry.id))).data

export function turnTone(revision: Revision | undefined) {
  if (!revision) return 'idle'
  if (revision.status === 'running') return 'running'
  if (revision.status === 'failed' || revision.status === 'cancelled') return 'failed'
  if (revision.status === 'clarification') return 'partial'
  const evidence = revision.result?.evidence_status
  return evidence === 'complete' ? 'ok' : evidence === 'partial' ? 'partial' : evidence === 'insufficient' ? 'gap' : 'ok'
}

export function Sidebar() {
  const { conversations, threadId, setThreadId, newThread, selectedTurnId, selectedRevisionId, selectRevision,
    addConversation, hydrated, activeRequest } = useStore()
  const [examples, setExamples] = useState<CatalogueEntry[]>([])
  const [pending, setPending] = useState('')
  const [error, setError] = useState('')
  const file = useRef<HTMLInputElement>(null)
  const autoOpened = useRef(false)
  const current = conversations.find(c => c.id === threadId)

  async function open(entry: CatalogueEntry) {
    setPending(entry.id); setError('')
    try {
      const conversation = await importConversation(JSON.stringify(await recording(entry)))
      addConversation(conversation, isReplayOnly)
      const first = conversation.turns[0]
      if (first) selectRevision(first.id, first.revisions.at(-1)!.id)
    } catch (err) { setError(err instanceof Error ? err.message : 'Could not open the recorded conversation.') }
    finally { setPending('') }
  }

  useEffect(() => {
    let alive = true
    catalogue().then(list => { if (alive) setExamples(list) }).catch(() => { if (alive && isReplayOnly) setError('Recorded conversations are unavailable.') })
    return () => { alive = false }
  }, [])

  // A first-time visitor of the replay should land on an answer, not on an empty page.
  useEffect(() => {
    if (!isReplayOnly || autoOpened.current || !hydrated || !examples.length) return
    autoOpened.current = true
    if (!current?.turns.length) void open(examples[0])
  }, [hydrated, examples.length]) // eslint-disable-line react-hooks/exhaustive-deps

  async function download() {
    if (!current) return
    const url = URL.createObjectURL(new Blob([await exportConversation(current)], { type: 'application/json' }))
    const link = document.createElement('a'); link.href = url; link.download = `veritasmed-${current.id}.json`
    link.click(); setTimeout(() => URL.revokeObjectURL(url), 1000)
  }

  const recordedIds = new Set(examples.map(e => e.id))
  const own = conversations.filter(c => !recordedIds.has(c.id) && (c.turns.length || c.id === threadId) && !isReplayOnly)
    .sort((a, b) => b.updated_at.localeCompare(a.updated_at))

  return <nav className="ws-sidebar" aria-label="Conversations">
    <div className="ws-sidebar-scroll">
      {!isReplayOnly && <button className="ws-new" disabled={!hydrated || !!activeRequest} onClick={newThread}>
        <span aria-hidden="true">+</span> New conversation</button>}

      {examples.length > 0 && <section>
        <h2 className="ws-label">{isReplayOnly ? 'Recorded conversations' : 'Recorded examples'}</h2>
        {examples.map(entry => {
          const loaded = conversations.find(c => c.id === entry.id)
          const active = threadId === entry.id
          return <div key={entry.id}>
            <button className={`ws-convo${active ? ' is-active' : ''}`} disabled={!hydrated || !!pending}
              onClick={() => loaded ? setThreadId(entry.id) : void open(entry)}>
              <span className="ws-convo-title">{pending === entry.id ? 'Opening…' : entry.label}</span>
              <span className="ws-convo-meta">{entry.turns} questions · real model output</span>
            </button>
            {active && loaded && <TurnList conversation={loaded} selectedTurnId={selectedTurnId} selectedRevisionId={selectedRevisionId} onSelect={selectRevision} />}
          </div>
        })}
      </section>}

      {own.length > 0 && <section>
        <h2 className="ws-label">Your conversations</h2>
        {own.map(conversation => <div key={conversation.id}>
          <button className={`ws-convo${conversation.id === threadId ? ' is-active' : ''}`} onClick={() => setThreadId(conversation.id)}>
            <span className="ws-convo-title">{conversation.legacy ? `Legacy ID · ${conversation.id.slice(0, 8)}` : conversation.turns.length ? conversation.title : 'New conversation'}</span>
            <span className="ws-convo-meta">{conversation.turns.length} {conversation.turns.length === 1 ? 'question' : 'questions'}</span>
          </button>
          {conversation.id === threadId && <TurnList conversation={conversation} selectedTurnId={selectedTurnId} selectedRevisionId={selectedRevisionId} onSelect={selectRevision} />}
        </div>)}
      </section>}
      {error && <p className="ws-sidebar-error" role="alert">{error}</p>}
    </div>

    <footer className="ws-sidebar-footer">
      <button disabled={!current?.turns.length} onClick={() => void download()}>Export</button>
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
    </footer>
  </nav>
}

function TurnList({ conversation, selectedTurnId, selectedRevisionId, onSelect }: {
  conversation: Conversation; selectedTurnId: string | null; selectedRevisionId: string | null
  onSelect: (turnId: string, revisionId: string) => void
}) {
  if (!conversation.turns.length) return null
  return <ol className="ws-turns">{conversation.turns.map((turn, i) => {
    const selected = turn.id === selectedTurnId
    const revision = (selected ? turn.revisions.find(r => r.id === selectedRevisionId) : null) ?? turn.revisions.at(-1)
    if (!revision) return null
    return <li key={turn.id}>
      <button className={`ws-turn${selected ? ' is-active' : ''}`} aria-current={selected} onClick={() => onSelect(turn.id, revision.id)}>
        <span className={`ws-dot tone-${turnTone(revision)}`} aria-hidden="true" />
        <span className="ws-turn-index">{i + 1}</span>
        <span className="ws-turn-text">{turn.question}</span>
      </button>
    </li>
  })}</ol>
}
