import { useCallback, useEffect, useState } from 'react'
import { AgentTimeline } from '../components/AgentTimeline'
import { AnswerPanel } from '../components/AnswerPanel'
import { EvidencePanel } from '../components/EvidencePanel'
import { QueryInput } from '../components/QueryInput'
import { useAgentStream } from '../hooks/useAgentStream'
import { useStore } from '../store'
import { AuditPage } from './AuditPage'
import type { AuditHandoff } from '../api/auditHandoff'

import { demoQuestions } from '../demo'

const SUGGESTED_QUERIES = demoQuestions

export function AnswerPage() {
  const { setQuery, setSelectedChunkId, activeQuery, result } = useStore()
  const { send } = useAgentStream()
  const [auditContext, setAuditContext] = useState<AuditHandoff | null>(null)
  const [auditOpen, setAuditOpen] = useState(false)

  useEffect(() => {
    setAuditContext(null)
    setAuditOpen(false)
  }, [result])

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
      <div className="vm-answer-grid" hidden={auditOpen} style={{
        flex: 1,
        display: auditOpen ? 'none' : 'grid',
        gridTemplateColumns: '320px minmax(0, 1fr) 370px',
        overflow: 'hidden',
      }}>
        {/* Left: Reasoning trace */}
        <AgentTimeline />

        {/* Center: Answer */}
        <div style={{ overflow: 'hidden', borderRight: '1px solid var(--rule)' }}>
          <AnswerPanel
            query={activeQuery}
            suggestedQueries={SUGGESTED_QUERIES}
            onCiteClick={handleCiteClick}
            onPickQuery={handlePickQuery}
            onAudit={openAudit}
          />
        </div>

        {/* Right: Evidence */}
        <EvidencePanel />
      </div>

      {auditContext && <div style={{ flex: 1, minHeight: 0, overflow: 'hidden', display: auditOpen ? 'block' : 'none' }}>
        <AuditPage context={auditContext} onClose={() => setAuditOpen(false)} />
      </div>}

      {/* Bottom: Composer */}
      <QueryInput />
    </div>
  )
}
