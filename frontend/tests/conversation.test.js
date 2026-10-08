import test from 'node:test'
import assert from 'node:assert/strict'
import { useStore } from '../src/store/index.ts'
import { newConversation, exportConversation, importConversation, sha256, attachAudit, contextFor } from '../src/conversation/model.ts'

function reset() {
  const c = newConversation()
  useStore.setState({ conversations: [c], hydrated: true, activeRequest: null, useContext: true })
  useStore.getState().setThreadId(c.id)
  return c.id
}
function answer(id, text = 'An answer with its original source.') {
  return { answer: text, citations: ['PMID:1'], confidence: 0, faithful: false, faithfulness_issues: '',
    iterations: 0, regen_count: 0, rewritten_queries: [], thread_id: id, latency_ms: 1,
    chunks: [{ chunk_id: 'pubmed:1:0', citation: 'PMID:1', source: 'pubmed', doc_id: '1', title: 'Study A',
      section: null, pmid: '1', chunk_idx: 0, total_chunks: 1, text: 'Original evidence.', score: null, highlight_ranges: [], external_url: 'https://pubmed.ncbi.nlm.nih.gov/1/' }] }
}
async function complete(question, text) {
  const target = useStore.getState().begin(question, 'live')
  await useStore.getState().finish(target, answer(target.conversationId, text))
  return target
}
test('history, regeneration and branch selection retain original answers and context revisions', async () => {
  reset()
  const first = await complete('First question?', 'First answer')
  const second = await complete('What about the sample?', 'Second answer')
  const regen = useStore.getState().begin('What about the sample?', 'live', true)
  await useStore.getState().finish(regen, answer(regen.conversationId, 'New answer'))
  useStore.getState().selectRevision(first.turnId, first.revisionId)
  const branch = await complete('A different follow-up?', 'Branch answer')
  const c = useStore.getState().conversations[0]
  assert.equal(c.turns.length, 3)
  assert.deepEqual(c.turns[1].revisions.map(r => r.result.answer), ['Second answer', 'New answer'])
  assert.deepEqual(c.turns[2].revisions[0].context.map(c => c.revision_id), [first.revisionId])
  assert.equal(c.turns[1].id, second.turnId)
  assert.equal(c.turns[2].id, branch.turnId)
  assert.deepEqual(await importConversation(await exportConversation(c)), c)
})
test('late results stay with their request, cancellation cannot finish a later turn', async () => {
  const original = reset()
  const running = useStore.getState().begin('Running?', 'live')
  useStore.getState().newThread()
  const selected = useStore.getState().threadId
  await useStore.getState().finish(running, answer(original))
  assert.equal(useStore.getState().threadId, selected)
  assert.equal(useStore.getState().result, null)
  assert.equal(useStore.getState().conversations[0].turns[0].revisions[0].status, 'complete')
  const cancelled = useStore.getState().begin('Stop?', 'live')
  await useStore.getState().finish(cancelled, undefined, undefined, true)
  const next = useStore.getState().begin('Next?', 'live')
  await useStore.getState().finish(cancelled, answer(selected, 'Late answer'))
  assert.equal(useStore.getState().activeRequest.revisionId, next.revisionId)
  assert.equal(useStore.getState().result, null)
})
test('export rejects source tampering even when envelope checksum is recomputed', async () => {
  reset(); await complete('Question?', 'Answer')
  const envelope = JSON.parse(await exportConversation(useStore.getState().conversations[0]))
  envelope.conversation.turns[0].revisions[0].result.chunks[0].text = 'Changed evidence'
  envelope.sha256 = await sha256(JSON.stringify(envelope.conversation))
  await assert.rejects(importConversation(JSON.stringify(envelope)), /fingerprint mismatch/)
})
test('edited audits are retained as experiments; reruns append to the exact original revision', async () => {
  reset(); const target = await complete('Question?', 'Answer')
  const make = async text => ({ mode: 'live', provenance: { note: 'Constructed protocol test' }, input: { answer: text, strategy: 'direct', sources: [{ id: 'evidence-1', title: 'PMID:1 · Study A', text: 'Original evidence.' }] },
    audit: { id: crypto.randomUUID(), strategy: 'direct', status: 'complete', created_utc: new Date().toISOString(), elapsed_seconds: 1,
      answer_sha256: await sha256(text), source_hashes: { 'evidence-1': await sha256('Original evidence.') }, claims: [], calls: [], summary: {}, claims_at_cap: false,
      checked_coverage: { covered_nonspace_characters: 0, total_nonspace_characters: 6, uncovered: [] } } })
  await useStore.getState().saveAudit(target, await make('Answer'))
  await useStore.getState().saveAudit(target, await make('Edited answer'))
  const revision = useStore.getState().conversations[0].turns[0].revisions[0]
  assert.deepEqual(revision.audits.map(r => r.edited), [false, true])
  const bad = await make('Answer'); bad.audit.source_hashes['evidence-1'] = 'bad'
  await assert.rejects(attachAudit(revision, bad), /source fingerprint/)
  assert.equal((await importConversation(await exportConversation(useStore.getState().conversations[0]))).turns[0].revisions[0].audits.length, 2)
})
test('oversized context is omitted whole, authored demos are never used as live context', async () => {
  reset(); await complete('Question?', 'x'.repeat(12001))
  let s = useStore.getState()
  assert.deepEqual(contextFor(s.conversations[0], s.selectedTurnId, s.selectedRevisionId), { context: [], omitted: 1 })
  reset(); const target = useStore.getState().begin('Demo?', 'authored_demo')
  await useStore.getState().finish(target, answer(target.conversationId))
  s = useStore.getState()
  assert.equal(contextFor(s.conversations[0], s.selectedTurnId, s.selectedRevisionId).context.length, 0)
})

test('a newer bundled recording replaces the stored copy only when replacement is allowed', async () => {
  const id = reset()
  await complete('Question?', 'Original recorded answer.')
  const stored = useStore.getState().conversations.find(c => c.id === id)
  const newer = { ...structuredClone(stored), title: 'Re-recorded' }
  assert.throws(() => useStore.getState().addConversation(newer), /different version/)
  useStore.getState().addConversation(newer, true)
  assert.equal(useStore.getState().conversations.find(c => c.id === id).title, 'Re-recorded')
  assert.equal(useStore.getState().conversations.filter(c => c.id === id).length, 1)
})

test('audits with the title-prefixed (v2) or passage-only (v1) hand-off both count as unedited', async () => {
  reset(); const target = await complete('Question?', 'Answer')
  const make = async text => ({ mode: 'live', provenance: { note: 'Constructed protocol test' }, input: { answer: 'Answer', strategy: 'direct', sources: [{ id: 'evidence-1', title: 'PMID:1 · Study A', text }] },
    audit: { id: crypto.randomUUID(), strategy: 'direct', status: 'ok', created_utc: new Date().toISOString(), elapsed_seconds: 1,
      answer_sha256: await sha256('Answer'), source_hashes: { 'evidence-1': await sha256(text) }, claims: [], calls: [], summary: {}, claims_at_cap: false,
      checked_coverage: { covered_nonspace_characters: 0, total_nonspace_characters: 6, uncovered: [] } } })
  await useStore.getState().saveAudit(target, await make('PMID:1 · Study A\n\nOriginal evidence.'))
  await useStore.getState().saveAudit(target, await make('Original evidence.'))
  await useStore.getState().saveAudit(target, await make('PMID:1 · Study B\n\nOriginal evidence.'))
  const revision = useStore.getState().conversations[0].turns[0].revisions[0]
  assert.deepEqual(revision.audits.map(r => r.edited), [false, false, true])
})

test('imports a conversation whose answers lack the deprecated confidence field', async () => {
  reset()
  const target = useStore.getState().begin('A question?', 'live')
  const { confidence, ...withoutConfidence } = answer(target.conversationId)
  await useStore.getState().finish(target, withoutConfidence)
  const c = useStore.getState().conversations[0]
  assert.equal(c.turns[0].revisions[0].result.confidence, undefined)
  assert.deepEqual(await importConversation(await exportConversation(c)), c)
})
