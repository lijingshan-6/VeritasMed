import { isGuidedDemo, isReplayOnly, playDemo, cancelDemo } from '../demo'
import { useCallback } from 'react'
import { connectStream, cancelStream } from '../api/streamConnection.js'
import { wsAskUrl } from '../api/client'
import { useStore } from '../store'
import type { ChunkOut } from '../types'
import type { AgentEvent, NodeEndData } from '../types/ws'

const NODE_LABELS: Record<string, string> = {
  resolve_context: 'Interpret follow-up',
  route:          'Route',
  retrieve:       'Retrieve',
  rerank:         'Rerank',
  grade:          'Match evidence',
  rewrite:        'Rewrite',
  generate:       'Generate',
  check:          'Faithfulness Check',
  increment_regen: 'Regen Counter',
  summarize_gate: 'Summarize Gate',
  summarize:      'Summarize',
}

export function useAgentStream() {
  const {
    query,
    begin, patchRequest, finish,
  } = useStore()

  const send = useCallback((overrideQuery?: string, regenerate = false) => {
    if (isReplayOnly) return
    const q = overrideQuery !== undefined ? overrideQuery : query
    const target = begin(q, isGuidedDemo ? 'authored_demo' : 'live', regenerate)
    if (!target) return
    cancelStream()
    cancelDemo()
    const revision = useStore.getState().conversations.find(c => c.id === target.conversationId)!.turns.find(t => t.id === target.turnId)!.revisions.at(-1)!
    const pushNode = (node) => patchRequest(target, r => ({ ...r, timeline: [...r.timeline, node] }))
    const updateNode = (name, patch) => patchRequest(target, r => ({ ...r, timeline: r.timeline.map((n, i) =>
      i === r.timeline.findLastIndex(v => v.name === name && v.status === 'running')
        ? { ...n, ...patch, elapsed_ms: n.timestamp ? Date.now() - n.timestamp : undefined } : n) }))

    if (isGuidedDemo) {
      playDemo(q, target.conversationId, handleEvent)
      return
    }
    connectStream(wsAskUrl(), { query: q, thread_id: target.conversationId, context: revision.context, omitted_context: revision.omitted_context }, {
      onEvent: handleEvent,
      onError: (message: string) => {
        void finish(target, undefined, message)
      },
    })

    function handleEvent(ev: AgentEvent) {
      if (ev.event === 'node_start') {
        pushNode({
          name: ev.node,
          label: NODE_LABELS[ev.node] ?? ev.node,
          status: 'running',
          summary: '',
          timestamp: isGuidedDemo ? undefined : Date.now(),
        })
      }

      if (ev.event === 'node_end') {
        const d: NodeEndData = ev.data
        let summary = ''
        if (ev.node === 'retrieve' || ev.node === 'rerank') {
          summary = `${d.count ?? 0} candidates`
        } else if (ev.node === 'grade') {
          const score = d.relevance_score ?? 0
          summary = `score: ${score.toFixed(2)} · ${(d.relevant ?? score >= 0.6) ? 'relevant' : 'insufficient'}`
        } else if (ev.node === 'rewrite') {
          const nq = d.new_query ?? ''
          summary = nq.slice(0, 60) + (nq.length > 60 ? '…' : '')
        } else if (ev.node === 'resolve_context') {
          summary = d.reason === 'follow_up' ? 'Context resolved · fresh evidence required' : d.reason ?? ''
        } else if (ev.node === 'generate') {
          summary = 'answer generated'
        } else if (ev.node === 'check') {
          summary = (d.faithful ?? false) ? 'faithful ✓' : 'issues found ⚠'
        }

        updateNode(ev.node, {
          status: ev.node === 'rewrite' ? 'rewrite' : 'done',
          summary: isGuidedDemo ? "illustrative step" : summary,
          detail: isGuidedDemo ? undefined : d,
        })
      }

      if (ev.event === 'chunk_retrieved') {
        const d = ev.data
        const chunk: ChunkOut = {
          chunk_id: d.chunk_id,
          citation: d.citation,
          source: d.source as 'pubmed' | 'pmc',
          doc_id: d.citation.replace(/^(PMID|PMC):/, ''),
          title: d.title,
          section: null,
          pmid: d.citation.startsWith('PMID:') ? d.citation.slice(5) : null,
          chunk_idx: 0,
          total_chunks: 1,
          text: d.text_snippet,
          score: d.score ?? null,
          highlight_ranges: [],
          external_url: d.external_url,
        }
        patchRequest(target, r => ({ ...r, liveChunks: [...r.liveChunks, chunk] }))
      }

      if (ev.event === 'done') {
        void finish(target, ev.data).catch(() => finish(target, undefined, 'Could not preserve the answer and source fingerprints.'))
      }

      if (ev.event === 'error') {
        console.error('Agent error event:', ev.data.message)
        void finish(target, undefined, `Server error: ${ev.data.message}`)
      }
    }
  }, [
    query, begin, patchRequest, finish,
  ])

  const cancel = useCallback(() => {
    cancelStream()
    cancelDemo()
    const target = useStore.getState().activeRequest
    if (target) void finish(target, undefined, undefined, true)
  }, [finish])

  return { send, cancel }
}
