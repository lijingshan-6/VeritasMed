import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { chunkContext, documentFor } from '../src/replay/corpus.ts'

const rows = readFileSync(new URL('../../data/demo/conversations/corpus.jsonl', import.meta.url), 'utf8')
  .split('\n').filter(Boolean).map(line => JSON.parse(line))

test('static replay returns a passage with its neighbours, like the live API', () => {
  const middle = rows.find(r => r.chunk_idx === 1)
  const context = chunkContext(rows, middle.chunk_id)
  assert.equal(context.chunk.text, middle.text)
  assert.equal(context.prev_chunk.chunk_id, middle.chunk_id.replace(/:1$/, ':0'))
  assert.equal(context.next_chunk.chunk_id, middle.chunk_id.replace(/:1$/, ':2'))
  assert.equal(context.document.citation, `PMC:${middle.doc_id}`)
  const alone = chunkContext(rows, middle.chunk_id, 0)
  assert.equal(alone.prev_chunk, null)
  assert.equal(chunkContext(rows, rows.find(r => r.chunk_idx === 0).chunk_id).prev_chunk, null)
  assert.throws(() => chunkContext(rows, 'pmc:missing:0'), /not in the bundled corpus/)
})

test('static replay assembles each paper from its ordered abstract sections', () => {
  const doc = documentFor(rows, 'PMC:PMC11567630')
  assert.equal(doc.total_chunks, 5)
  assert.deepEqual(doc.chunks.map(c => c.chunk_idx), [0, 1, 2, 3, 4])
  assert.equal(doc.pmid, '39546502')
  assert.throws(() => documentFor(rows, 'PMC:unknown'), /not in the bundled corpus/)
})
