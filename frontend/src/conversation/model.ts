import type { AnswerOut, TimelineNode } from '../types/ws'
import type { ChunkOut } from '../types'
import type { AuditRecord } from '../api/audit'
import { makeAuditHandoff } from '../api/auditHandoff.ts'

export type ContextTurn = { turn_id: string; revision_id: string; question: string; answer: string; source_titles: string[] }
export type SavedAudit = { id: string; revision_id: string; created_at: string; edited: boolean; record: AuditRecord }
export type Revision = {
  id: string; created_at: string; status: 'running' | 'complete' | 'cancelled' | 'failed' | 'clarification'
  origin: 'live' | 'authored_demo'; context: ContextTurn[]; omitted_context: number
  result: AnswerOut | null; timeline: TimelineNode[]; liveChunks: ChunkOut[]; error: string | null
  answer_sha256?: string; source_hashes?: Record<string, string>; audits: SavedAudit[]
}
export type Turn = { id: string; question: string; parent_turn_id: string | null; revisions: Revision[] }
export type Conversation = { schema: 1; id: string; title: string; created_at: string; updated_at: string; legacy?: boolean; turns: Turn[] }
export const newId = (): string => crypto.randomUUID()
export const now = () => new Date().toISOString()
export function newConversation(id = newId()): Conversation {
  return { schema: 1, id, title: 'New conversation', created_at: now(), updated_at: now(), turns: [] }
}
export async function sha256(text: string) {
  return Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256', new TextEncoder().encode(text))), b => b.toString(16).padStart(2, '0')).join('')
}
export async function fingerprint(result: AnswerOut) {
  const source_hashes = Object.fromEntries(await Promise.all(result.chunks.map(async c => [c.chunk_id, await sha256(c.text)])))
  return { answer_sha256: await sha256(result.answer), source_hashes }
}

// Follow the selected branch only. Whole turns are retained; no summaries or truncated qualifiers.
export function contextFor(conversation: Conversation, turnId: string | null, revisionId: string | null) {
  const chain: ContextTurn[] = []
  let previouslyOmitted = 0
  let turn = conversation.turns.find(t => t.id === turnId)
  if (turn) {
    const revision = turn.revisions.find(r => r.id === revisionId) ?? turn.revisions.at(-1)
    if (revision?.origin === 'live') { chain.push(...revision.context); previouslyOmitted = revision.omitted_context }
    if (revision?.origin === 'live' && revision.result && ['complete', 'clarification'].includes(revision.status)) {
      chain.push({ turn_id: turn.id, revision_id: revision.id, question: turn.question,
        answer: revision.result.answer, source_titles: revision.result.chunks.map(c => `${c.citation} · ${c.title}`) })
    }
  }
  const selected: ContextTurn[] = []
  let size = 0
  for (const item of chain.slice().reverse()) {
    const length = contextLength(item)
    if (selected.length >= 6 || size + length > 12000) break
    selected.unshift(item); size += length
  }
  return { context: selected, omitted: previouslyOmitted + chain.length - selected.length }
}
export function contextLength(item: ContextTurn) {
  return Array.from(item.question + item.answer + item.source_titles.join('')).length
}

export async function attachAudit(revision: Revision, record: AuditRecord): Promise<SavedAudit> {
  if (!revision.result || revision.status !== 'complete') throw new Error('Only a complete answer can be audited.')
  const expected = makeAuditHandoff(revision.result, '', revision.origin === 'authored_demo').input
  const edited = expected.answer !== record.input.answer || JSON.stringify(expected.sources) !== JSON.stringify(record.input.sources)
  if (await sha256(record.input.answer) !== record.audit.answer_sha256) throw new Error('Audit answer fingerprint does not match its input.')
  for (const source of record.input.sources) {
    if (await sha256(source.text) !== record.audit.source_hashes[source.id]) throw new Error('Audit source fingerprint does not match its input.')
  }
  return { id: newId(), revision_id: revision.id, created_at: now(), edited,
    record: { ...record, provenance: { ...record.provenance, input_edited: edited } } }
}

function assert(ok: unknown, message: string): asserts ok { if (!ok) throw new Error(message) }
function string(value: unknown): value is string { return typeof value === 'string' }
function object(value: unknown): value is Record<string, any> { return !!value && typeof value === 'object' && !Array.isArray(value) }
function strings(value: unknown) { return Array.isArray(value) && value.every(string) }
function validSpan(span: any, text: string) {
  return object(span) && Number.isInteger(span.start) && Number.isInteger(span.end) && span.start >= 0 && span.end >= span.start
    && span.end <= Array.from(text).length && span.text === Array.from(text).slice(span.start, span.end).join('')
}

// Import is deliberately strict: no fuzzy source repair and no implicit schema upgrades.
export async function validateConversation(value: unknown): Promise<Conversation> {
  assert(object(value) && value.schema === 1 && string(value.id) && string(value.title) && string(value.created_at) && string(value.updated_at) && Array.isArray(value.turns), 'Unsupported or incomplete conversation file.')
  const ids = new Set<string>()
  const priorTurns = new Map<string, Turn>()
  const priorRevisions = new Map<string, { turn: Turn; revision: Revision }>()
  const unique = (id: unknown) => { assert(string(id) && id.length > 0 && !ids.has(id), 'Duplicate or missing record ID.'); ids.add(id) }
  for (const turn of value.turns) {
    assert(object(turn) && string(turn.question) && Array.isArray(turn.revisions), 'Invalid turn.')
    unique(turn.id)
    assert(turn.parent_turn_id === null || priorTurns.has(turn.parent_turn_id), 'Unknown or out-of-order parent turn.')
    for (const revision of turn.revisions) {
      assert(object(revision) && ['running', 'complete', 'failed', 'cancelled', 'clarification'].includes(revision.status)
        && ['live', 'authored_demo'].includes(revision.origin) && string(revision.created_at) && Array.isArray(revision.context)
        && Number.isInteger(revision.omitted_context) && revision.omitted_context >= 0
        && Array.isArray(revision.timeline) && Array.isArray(revision.liveChunks) && Array.isArray(revision.audits)
        && (revision.error === null || string(revision.error)), 'Invalid answer revision.')
      unique(revision.id)
      for (const node of revision.timeline) assert(object(node) && string(node.name) && string(node.label) && string(node.summary) && ['waiting', 'running', 'done', 'rewrite', 'error'].includes(node.status), 'Invalid trace.')
      assert(revision.context.length <= 6, 'Too many context turns.')
      for (const item of revision.context) {
        assert(object(item) && string(item.question) && string(item.answer) && strings(item.source_titles), 'Invalid context snapshot.')
        const previous = priorRevisions.get(item.revision_id)
        assert(previous && previous.turn.id === item.turn_id && previous.turn.question === item.question
          && previous.revision.result?.answer === item.answer
          && JSON.stringify(previous.revision.result.chunks.map(c => `${c.citation} · ${c.title}`)) === JSON.stringify(item.source_titles), 'Context does not match its original answer revision.')
      }
      assert(revision.context.reduce((n, c) => n + contextLength(c), 0) <= 12000, 'Context exceeds the character budget.')
      if (revision.result !== null) {
        const result = revision.result
        assert(object(result) && string(result.answer) && strings(result.citations) && strings(result.rewritten_queries)
          && typeof result.confidence === 'number' && typeof result.faithful === 'boolean' && string(result.faithfulness_issues)
          && Number.isInteger(result.iterations) && Number.isInteger(result.regen_count) && typeof result.latency_ms === 'number'
          && result.thread_id === value.id && Array.isArray(result.chunks), 'Invalid answer or conversation identity.')
        const chunkIds = new Set<string>()
        for (const c of result.chunks) {
          assert(object(c) && string(c.chunk_id) && !chunkIds.has(c.chunk_id) && string(c.text) && string(c.title) && string(c.citation)
            && string(c.external_url) && string(c.source) && string(c.doc_id) && Number.isInteger(c.chunk_idx) && Number.isInteger(c.total_chunks)
            && Array.isArray(c.highlight_ranges), 'Invalid source snapshot.')
          chunkIds.add(c.chunk_id)
        }
        const hashes = await fingerprint(result as AnswerOut)
        assert(revision.answer_sha256 === hashes.answer_sha256 && object(revision.source_hashes)
          && Object.keys(revision.source_hashes).length === Object.keys(hashes.source_hashes).length
          && Object.entries(hashes.source_hashes).every(([key, hash]) => revision.source_hashes[key] === hash), 'Answer/source fingerprint mismatch. The file was changed or is incomplete.')
        if (result.conversation_context) {
          const context = result.conversation_context
          assert(object(context) && string(context.original_query) && string(context.resolved_query) && strings(context.context_turn_ids)
            && strings(context.supplied_turn_ids) && typeof context.needs_clarification === 'boolean' && string(context.clarification)
            && typeof context.elapsed_ms === 'number' && typeof context.omitted_context === 'number', 'Invalid question interpretation.')
        }
        if (result.answer_components) {
          assert(Array.isArray(result.answer_components) && result.answer_components.every(c => object(c) && string(c.id)
            && string(c.requirement) && string(c.status) && Array.isArray(c.evidence)
            && c.evidence.every(e => object(e) && string(e.chunk_id) && string(e.citation) && string(e.quote))), 'Invalid answer components.')
        }
      }
      assert(!['complete', 'clarification'].includes(revision.status) || revision.result !== null, 'Completed answer is missing.')
      for (const audit of revision.audits) {
        unique(audit.id)
        assert(audit.revision_id === revision.id && object(audit.record) && object(audit.record.audit)
          && Array.isArray(audit.record.audit.claims) && Array.isArray(audit.record.audit.calls) && object(audit.record.audit.checked_coverage)
          && Array.isArray(audit.record.audit.checked_coverage.uncovered) && object(audit.record.input)
          && string(audit.record.input.answer) && Array.isArray(audit.record.input.sources), 'Invalid saved audit.')
        const record = audit.record
        assert(object(record.provenance) && string(record.provenance.note) && string(record.audit.id) && string(record.audit.status)
          && string(record.audit.created_utc) && typeof record.audit.elapsed_seconds === 'number' && object(record.audit.summary)
          && typeof record.audit.checked_coverage.covered_nonspace_characters === 'number'
          && typeof record.audit.checked_coverage.total_nonspace_characters === 'number', 'Invalid audit metadata.')
        assert(record.input.sources.every(s => object(s) && string(s.id) && string(s.text) && string(s.title)), 'Invalid audit sources.')
        for (const claim of record.audit.claims) {
          assert(object(claim) && string(claim.id) && string(claim.quote) && string(claim.status) && string(claim.explanation)
            && Array.isArray(claim.evidence), 'Invalid audit claim.')
          for (const span of [...(claim.answer_spans ?? []), ...(claim.context_spans ?? []),
            ...(claim.answer_span ? [claim.answer_span] : []), ...(claim.context_span ? [claim.context_span] : [])]) {
            assert(validSpan(span, record.input.answer), 'Claim position does not match the saved answer.')
          }
          for (const span of claim.evidence) {
            const source = record.input.sources.find(s => s.id === span.source_id)
            assert(source && validSpan(span, source.text) && span.source_sha256 === record.audit.source_hashes[source.id], 'Evidence position does not match the saved source.')
          }
          for (const q of claim.qualifier_anchors ?? []) {
            assert(object(q) && string(q.quote) && string(q.parent_quote) && object(q.binding) && object(q.parent_binding), 'Invalid qualifier anchor.')
            for (const span of [q.binding.span, q.parent_binding.span].filter(Boolean)) {
              assert(validSpan(span, record.input.answer), 'Qualifier position does not match the saved answer.')
            }
            if (q.binding.span) {
              assert(q.parent_binding.span && q.binding.span.text === q.quote && q.parent_binding.span.text === q.parent_quote
                && q.binding.span.start >= q.parent_binding.span.start && q.binding.span.end <= q.parent_binding.span.end,
              'Qualifier does not belong to its recorded original passage.')
            }
          }
        }
        assert(record.audit.checked_coverage.uncovered.every(span => validSpan(span, record.input.answer)), 'Uncovered text does not match the answer.')
        const checked = await attachAudit(revision as Revision, audit.record as AuditRecord)
        assert(checked.edited === audit.edited, 'Edited audit is incorrectly attached as an original verdict.')
      }
      priorRevisions.set(revision.id, { turn: turn as Turn, revision: revision as Revision })
    }
    priorTurns.set(turn.id, turn as Turn)
  }
  return value as Conversation
}

export async function exportConversation(conversation: Conversation) {
  const payload = JSON.stringify(conversation)
  return JSON.stringify({ format: 'veritasmed-conversation', schema: 1, sha256: await sha256(payload), conversation }, null, 2)
}
export async function importConversation(text: string) {
  const envelope = JSON.parse(text)
  assert(envelope.format === 'veritasmed-conversation' && envelope.schema === 1, 'Unsupported export format.')
  assert(envelope.sha256 === await sha256(JSON.stringify(envelope.conversation)), 'Export checksum mismatch.')
  return validateConversation(envelope.conversation)
}
