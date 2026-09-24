import type { AnswerOut } from '../types/ws'
import type { AuditInput } from './audit'

export type AuditHandoff = {
  kind: 'live_ask' | 'authored_demo'
  question: string
  thread_id: string
  citations: string[]
  input: AuditInput
  source_map: { id: string; chunk_id: string; citation: string; external_url: string; section?: string | null }[]
}

export function inputProblem(input: AuditInput): string | null {
  const length = (text: string) => Array.from(text).length
  if (!input.answer.trim()) return 'The answer is empty.'
  if (length(input.answer) > 12000) return 'This answer exceeds the 12,000-character audit limit. Nothing was truncated.'
  if (!input.sources.length) return 'This answer has no source texts to audit against.'
  if (input.sources.length > 40) return 'This answer has more than 40 source passages. Nothing was truncated.'
  if (input.sources.some(s => !s.text.trim() || length(s.text) > 50000 || !s.title.trim() || length(s.title) > 500)) return 'A source is empty or exceeds the source text/title limits. Nothing was truncated.'
  if (input.sources.reduce((sum, s) => sum + length(s.text), 0) > 80000) return 'Source texts exceed 80,000 characters combined. Nothing was truncated.'
  return null
}

export function makeAuditHandoff(answer: AnswerOut, question: string, guided: boolean): AuditHandoff {
  const input: AuditInput = { answer: answer.answer, strategy: 'direct', sources: answer.chunks.map((c, i) => ({
    id: `evidence-${i + 1}`, title: `${c.citation} · ${c.title}`, text: c.text,
  })) }
  const problem = inputProblem(input)
  if (problem) throw new Error(problem)
  return { kind: guided ? 'authored_demo' : 'live_ask', question, thread_id: answer.thread_id,
    citations: [...answer.citations], input,
    source_map: answer.chunks.map((c, i) => ({ id: input.sources[i].id, chunk_id: c.chunk_id,
      citation: c.citation, external_url: c.external_url, section: c.section })) }
}
