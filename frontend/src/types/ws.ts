/**
 * WebSocket event types — mirror of src/medrag/api/models.py AgentEvent variants.
 * Keep in sync manually; WebSocket frames are not part of the OpenAPI spec.
 */
import type { ChunkOut } from './index'

/** Mirror of models.py AnswerOut — used only in DoneEvent (WebSocket, not REST). */
export interface AnswerComponent {
  id: string
  requirement: string
  source_hint: string
  status: 'supported' | 'partial' | 'missing'
  evidence: { chunk_id: string; citation: string; quote: string }[]
  required_details: string[]
  gap: string
  answer: string
}

export interface AnswerOut {
  conversation_context?: {
    original_query: string; resolved_query: string; context_turn_ids: string[]; supplied_turn_ids: string[]
    needs_clarification: boolean; clarification: string; referent_entities: string[]
    omitted_context: number; elapsed_ms: number; model: string | null; usage: Record<string, unknown> | null
    status: string; raw_output: string
  }
  evidence_status?: 'complete' | 'partial' | 'insufficient' | null
  evidence_gap?: string
  answer_components?: AnswerComponent[]
  answer: string
  citations: string[]
  confidence: number
  faithful: boolean
  faithfulness_issues: string
  iterations: number
  regen_count: number
  rewritten_queries: string[]
  chunks: ChunkOut[]
  thread_id: string
  latency_ms: number
}

export interface NodeStartEvent {
  event: 'node_start'
  node: string
}

export interface NodeEndData {
  // retrieve / rerank
  count?: number | null
  // grade
  relevance_score?: number | null
  relevant?: boolean | null
  reason?: string | null
  rewrite_hint?: string | null
  // rewrite
  new_query?: string | null
  rewritten_queries?: string[] | null
  // generate
  answer_preview?: string | null
  // check
  faithful?: boolean | null
  issues?: string | null
  confidence?: number | null
  // route
  route?: string | null
}

export interface NodeEndEvent {
  event: 'node_end'
  node: string
  data: NodeEndData
}

export interface ChunkRetrievedData {
  chunk_id: string
  citation: string
  title: string
  score: number | null
  text_snippet: string
  source: string
  external_url: string
}

export interface ChunkRetrievedEvent {
  event: 'chunk_retrieved'
  node: string
  data: ChunkRetrievedData
}

export interface DoneEvent {
  event: 'done'
  node: null
  data: AnswerOut
}

export interface ErrorEvent {
  event: 'error'
  node: null
  data: { message: string }
}

export type AgentEvent =
  | NodeStartEvent
  | NodeEndEvent
  | ChunkRetrievedEvent
  | DoneEvent
  | ErrorEvent

/** Timeline node status for the UI */
export type NodeStatus = 'waiting' | 'running' | 'done' | 'rewrite' | 'error'

export interface TimelineNode {
  name: string
  label: string
  status: NodeStatus
  summary: string
  detail?: NodeEndData
  timestamp?: number
  elapsed_ms?: number
}
