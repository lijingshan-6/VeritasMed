import { useCallback, useEffect, useState } from 'react'
import { AgentTimeline } from '../components/AgentTimeline'
import { AnswerPanel } from '../components/AnswerPanel'
import { EvidencePanel } from '../components/EvidencePanel'
import { QueryInput } from '../components/QueryInput'
import { useAgentStream } from '../hooks/useAgentStream'
import { useStore } from '../store'
import { AuditPage } from './AuditPage'
import type { AuditHandoff } from '../api/auditHandoff'
import { ConversationHistory } from '../components/ConversationHistory'
import { SavedConversations } from '../components/SavedConversations'

import { demoQuestions, isReplayOnly } from '../demo'

const SUGGESTED_QUERIES = demoQuestions

export function AnswerPage() {
  const { setQuery, setSelectedChunkId, activeQuery, result, conversations, threadId, selectedTurnId, selectedRevisionId, saveAudit, storageError, hydrated } = useStore()
  const revision = conversations.find(c => c.id === threadId)?.turns.find(t => t.id === selectedTurnId)?.revisions.find(r => r.id === selectedRevisionId)
  const { send } = useAgentStream()
  const [auditContext, setAuditContext] = useState<AuditHandoff | null>(null)
  const [auditOpen, setAuditOpen] = useState(false)

  useEffect(() => {
    setAuditContext(null)
    setAuditOpen(false)
  }, [selectedRevisionId])

  function openAudit(handoff: AuditHandoff) {
    setAuditContext(current => current ?? handoff)
    setAuditOpen(true)
  }

  const handleCiteClick = useCallback((citation: string) => {
    const chunks = result?.chunks ?? []
    const idx = chunks.findIndex((c) => c.citation === citation)
    if (idx >= 0) {
      const id = chunks[idx].chunk_id
      setSelectedChunkId(id)
      document.getElementById(`chunk-${id}`)?.scrollIntoView({ behavior: 'smooth', block: 'start' })
    }
  }, [result, setSelectedChunkId])

  const handlePickQuery = useCallback((q: string) => {
    setQuery(q)
    send(q)
  }, [setQuery, send])

  return (
    <div className="vm-answer-page" style={{ height: '100%', display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
      {storageError && <div role="alert" className="vm-storage-warning">{storageError}</div>}
      {!hydrated && <div role="status">Restoring local conversations…</div>}
      <div className="vm-answer-grid" hidden={auditOpen} style={{
        flex: 1,
        display: auditOpen ? 'none' : 'grid',
        gridTemplateColumns: '320px minmax(0, 1fr) 370px',
        overflow: 'hidden',
      }}>
        {/* Left: Reasoning trace */}
        <AgentTimeline />

        {/* Center: Answer */}
        <div style={{ overflow: 'auto', borderRight: '1px solid var(--rule)' }}>
          <SavedConversations />
          <ConversationHistory />
          <AnswerPanel
            query={activeQuery}
            suggestedQueries={isReplayOnly ? [] : SUGGESTED_QUERIES}
            onCiteClick={handleCiteClick}
            onPickQuery={handlePickQuery}
            onAudit={openAudit}
            onRegenerate={isReplayOnly ? undefined : () => send(activeQuery, true)}
            guided={revision?.origin === 'authored_demo'}
          />
        </div>

        {/* Right: Evidence */}
        <EvidencePanel />
      </div>

      {auditContext && <div style={{ flex: 1, minHeight: 0, overflow: 'hidden', display: auditOpen ? 'block' : 'none' }}>
        <AuditPage key={selectedRevisionId} context={auditContext} onClose={() => setAuditOpen(false)} saved={revision?.audits ?? []}
          onRecord={record => saveAudit({ conversationId: threadId, turnId: selectedTurnId!, revisionId: selectedRevisionId! }, record)} />
      </div>}

      {/* Bottom: Composer */}
      <QueryInput />
    </div>
  )
}
