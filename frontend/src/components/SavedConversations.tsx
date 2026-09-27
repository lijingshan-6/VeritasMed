import { useEffect, useState } from 'react'
import { api } from '../api/client'
import { importConversation } from '../conversation/model'
import { useStore } from '../store'

type Example = { id: string; label: string; description: string; turns: number }
export function SavedConversations() {
  const [examples, setExamples] = useState<Example[]>([])
  const [error, setError] = useState('')
  const [pending, setPending] = useState('')
  const [open, setOpen] = useState(true)
  const { addConversation, hydrated, selectRevision } = useStore()
  useEffect(() => {
    let alive = true
    api.get('/api/conversations/examples').then(({ data }) => { if (alive) setExamples(data.examples) })
      .catch(() => { if (alive) setError('Saved conversations are unavailable. Check that the local service is running.') })
    return () => { alive = false }
  }, [])
  async function load(example: Example) {
    setPending(example.id); setError('')
    try {
      const { data } = await api.get('/api/conversations/examples/' + encodeURIComponent(example.id))
      const conversation = await importConversation(JSON.stringify(data))
      addConversation(conversation)
      const first = conversation.turns[0]
      if (first) selectRevision(first.id, first.revisions[0].id)
      setOpen(false)
    } catch (err) { setError(err instanceof Error ? err.message : 'Could not load the recorded conversation.') }
    finally { setPending('') }
  }
  if (!examples.length && !error) return null
  return <section className="vm-saved-examples" aria-label="Recorded medical conversations"><details open={open} onToggle={e => setOpen(e.currentTarget.open)}>
    <summary>Recorded medical conversations · choose a conversation</summary>
    <div className="vm-eyebrow">SAVED INFERENCE · real medical conversations</div>
    <p>Open a recorded conversation, select a question, then inspect that answer’s sources and saved audits. Loading makes no model call.</p>
    <div>{examples.map(example => <button key={example.id} disabled={!hydrated || !!pending} onClick={() => void load(example)}>
      <strong>{pending === example.id ? 'Opening…' : example.label}</strong>
      <span>{example.turns} turns · {example.description}</span>
    </button>)}</div>
    {error && <p role="alert">{error}</p>}
  </details></section>
}
