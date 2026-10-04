import { useCallback, useEffect, useState } from 'react'
import type { ReactNode } from 'react'
import { EvidencePanel } from '../components/EvidencePanel'
import { QueryInput } from '../components/QueryInput'
import { Sidebar } from '../components/workspace/Sidebar'
import { AnswerBody, TurnHeader } from '../components/workspace/AnswerView'
import type { Tab } from '../components/workspace/AnswerView'
import { LiveProgress, ProcessDetails } from '../components/workspace/Process'
import { useAgentStream } from '../hooks/useAgentStream'
import { useStore } from '../store'
import { AuditPage } from './AuditPage'
import { makeAuditHandoff } from '../api/auditHandoff'
import { demoQuestions, isReplayOnly } from '../demo'

export function AnswerPage() {
  const { setQuery, setSelectedChunkId, activeQuery, result, timeline, isStreaming, errorMessage, conversations, threadId,
    selectedTurnId, selectedRevisionId, saveAudit, storageError, hydrated } = useStore()
  const revision = conversations.find(c => c.id === threadId)?.turns.find(t => t.id === selectedTurnId)?.revisions.find(r => r.id === selectedRevisionId)
  const turn = conversations.find(c => c.id === threadId)?.turns.find(t => t.id === selectedTurnId)
  const { send } = useAgentStream()
  const [tab, setTab] = useState<Tab>('answer')
  const [copied, setCopied] = useState(false)

  useEffect(() => { setTab('answer'); setCopied(false) }, [selectedRevisionId])

  const onCiteClick = useCallback((citation: string) => {
    const chunk = result?.chunks.find(c => c.citation === citation)
    if (!chunk) return
    setSelectedChunkId(chunk.chunk_id)
    if (window.matchMedia('(max-width: 1279px)').matches) setTab('sources')
    requestAnimationFrame(() => document.getElementById(`chunk-${chunk.chunk_id}`)?.scrollIntoView({ behavior: 'smooth', block: 'start' }))
  }, [result, setSelectedChunkId])

  const pick = useCallback((q: string) => { setQuery(q); send(q) }, [setQuery, send])
  const handoff = (() => { try { return result && !isStreaming ? makeAuditHandoff(result, activeQuery, revision?.origin === 'authored_demo') : null } catch { return null } })()

  function download() {
    if (!result) return
    const url = URL.createObjectURL(new Blob([`# ${activeQuery}\n\n${result.answer}\n\nResearch demonstration; not clinical advice.\n`], { type: 'text/markdown;charset=utf-8' }))
    const link = document.createElement('a'); link.href = url; link.download = 'veritasmed-answer.md'
    link.click(); setTimeout(() => URL.revokeObjectURL(url), 1000)
  }

  const actions = result && <>
    <button onClick={() => navigator.clipboard.writeText(result.answer).then(() => setCopied(true)).catch(() => undefined)}>{copied ? 'Copied' : 'Copy'}</button>
    <button onClick={download}>Download</button>
    {!isReplayOnly && <button disabled={isStreaming} onClick={() => send(activeQuery, true)}>Re-run</button>}
    {turn && turn.revisions.length > 1 && <select aria-label="Answer version" value={selectedRevisionId ?? ''}
      onChange={e => useStore.getState().selectRevision(turn.id, e.target.value)}>
      {turn.revisions.map((r, n) => <option key={r.id} value={r.id}>Version {n + 1}</option>)}</select>}
  </>

  let body: ReactNode
  if (!turn) body = isReplayOnly ? <ReplayIntro /> : <Welcome onPick={pick} />
  else if (errorMessage) body = <div className="ws-error" role="alert"><h2>The answer could not be completed</h2><p>{errorMessage}</p></div>
  else if (isStreaming && !result) body = <LiveProgress timeline={timeline} />
  else if (result && tab === 'check' && handoff) body = <AuditPage key={selectedRevisionId} variant="tab" context={handoff}
    onClose={() => setTab('answer')} saved={revision?.audits ?? []}
    onRecord={record => saveAudit({ conversationId: threadId, turnId: selectedTurnId!, revisionId: selectedRevisionId! }, record)} />
  else if (result && tab === 'sources') body = <div className="ws-inline-sources"><EvidencePanel /></div>
  else if (result) body = <>
    <AnswerBody result={result} revision={revision} onCiteClick={onCiteClick} onOpenCheck={() => setTab('check')} />
    <ProcessDetails timeline={timeline} result={result} />
  </>

  const wide = tab === 'check' && !!result
  return <div className={`ws${wide ? ' ws--wide' : ''}`}>
    <Sidebar />
    <main className="ws-main">
      {storageError && <div role="alert" className="ws-banner">{storageError}</div>}
      {!hydrated && <div role="status" className="ws-banner">Restoring local conversations…</div>}
      <div className="ws-scroll">
        <article className={`ws-article${wide ? ' ws-article--wide' : ''}`}>
          {turn && <TurnHeader question={turn.question} result={result} revision={revision} tab={tab} onTab={setTab} actions={actions} />}
          {body}
        </article>
      </div>
      <QueryInput />
    </main>
    {!wide && <aside className="ws-inspector" aria-label="Sources"><EvidencePanel /></aside>}
  </div>
}

function Welcome({ onPick }: { onPick: (q: string) => void }) {
  return <div className="ws-welcome">
    <h1>Ask a question about the literature.</h1>
    <p>Answers cite the exact source sentences. Every statement can then be checked against them.
      This demo index holds three papers (15 abstract passages), so ask about them.</p>
    <ul>{demoQuestions.map(q => <li key={q}><button onClick={() => onPick(q)}>{q}</button></li>)}</ul>
  </div>
}

function ReplayIntro() {
  return <div className="ws-welcome">
    <h1>Recorded conversations</h1>
    <p>Choose a conversation on the left. Every answer, source and claim check is real model output, replayed without new calls.</p>
  </div>
}
