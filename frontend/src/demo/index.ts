import fixtures from './examples.json'
import type { ChunkOut } from '../types'
import type { AgentEvent, AnswerOut } from '../types/ws'

export const isReplayOnly = import.meta.env.VITE_REPLAY_ONLY === '1'
export const isGuidedDemo = !isReplayOnly && new URLSearchParams(window.location.search).get('demo') === '1'
export const isMedicalDemo = !isGuidedDemo && import.meta.env.VITE_MEDICAL_DEMO === '1'
export const isConversationDemo = !isGuidedDemo && import.meta.env.VITE_CONVERSATION_DEMO === '1'
export const demoSuffix = isGuidedDemo ? '?demo=1' : ''
export const demoChunks = fixtures.chunks as ChunkOut[]
export const demoQuestions = isConversationDemo ? [
  'In the GRADE report on hypoglycemia outcomes, what were the severe hypoglycemia percentages for glargine, glimepiride, liraglutide and sitagliptin while taking the assigned medication?',
  'In the 2016 brown-rice-based vegan diet trial, what HbA1c changes were reported for the two groups?',
  'What did the 2013 aerobic versus combined exercise study measure, and over what time period?',
] : isMedicalDemo ? [
  'In the GRADE trial report on hypoglycemia, what were the severe hypoglycemia rates for glargine, glimepiride, liraglutide and sitagliptin while participants were taking their assigned medications, and which population and analysis do these results describe?',
] : fixtures.examples.map((example) => example.query)
let pending: ReturnType<typeof setTimeout> | undefined

export function cancelDemo() { clearTimeout(pending) }

export function playDemo(query: string, threadId: string, emit: (event: AgentEvent) => void) {
  cancelDemo()
  const example = fixtures.examples.find((entry) => entry.query === query)
  if (!example) {
    emit({ event: 'error', node: null, data: { message: 'This guided demo has three fixed examples. Choose an example above; use Live mode for other questions.' } })
    return
  }
  const events: AgentEvent[] = []
  for (const node of ['route', 'retrieve', 'rerank', 'grade', 'generate', 'check']) {
    events.push({ event: 'node_start', node })
    events.push({ event: 'node_end', node, data: {
      count: 3, relevance_score: 1, relevant: true, faithful: example.faithful,
      issues: example.faithfulness_issues, reason: 'Illustrative preset; no model was called.',
    } })
  }
  events.push({ event: 'done', node: null, data: {
    ...(example as unknown as AnswerOut), confidence: 0, iterations: 0, regen_count: 0, rewritten_queries: [],
    chunks: demoChunks, thread_id: threadId, latency_ms: 0,
  } })
  function next() {
    const event = events.shift()
    if (!event) return
    emit(event)
    if (events.length) pending = setTimeout(next, 100)
  }
  next()
}
