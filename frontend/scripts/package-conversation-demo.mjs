// Build browser-compatible exports from unchanged, recorded API outputs.
import fs from 'node:fs/promises'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { attachAudit, validateConversation, exportConversation, importConversation } from '../src/conversation/model.ts'

const root = fileURLToPath(new URL('../../data/demo/conversations/', import.meta.url))
const protocol = JSON.parse(await fs.readFile(path.join(root, 'protocol.json'), 'utf8'))
// Recording to package: run02 (current code) by default; run01 is the original v0.8 recording.
const run = process.argv[2] ?? 'run02'
const catalogue = []
const exports = []
for (const spec of protocol.conversations) {
  const conversation = JSON.parse(await fs.readFile(path.join(root, run, spec.id + '.json'), 'utf8'))
  if (conversation.turns.length !== spec.questions.length || conversation.turns.some(t => t.revisions.some(r => r.status === 'running'))) throw new Error('Recording is incomplete: ' + spec.id)
  let firstEligible = true
  for (const turn of conversation.turns) {
    const revision = turn.revisions[0]
    revision.audits = []
    const eligible = revision.status === 'complete' && revision.result?.chunks.length
    const methods = eligible ? (firstEligible ? ['direct', 'atomic_v2'] : ['direct']) : []
    if (eligible) firstEligible = false
    for (const strategy of methods) {
      const file = path.join(root, run, turn.id + '-' + strategy + '.json')
      // Every scheduled audit must exist; a missing file is not an unaudited success.
      const record = JSON.parse(await fs.readFile(file, 'utf8'))
      if (!record.audit) throw new Error('Audit has no completed response; preserve and inspect the raw failure: ' + file)
      const audit = await attachAudit(revision, record)
      audit.id = turn.id + '-audit-' + strategy
      audit.created_at = record.audit.created_utc
      revision.audits.push(audit)
    }
  }
  await validateConversation(conversation)
  const output = await exportConversation(conversation)
  await importConversation(output)
  const file = spec.id + '.json'
  exports.push({ file, output })
  const statuses = conversation.turns.map(t => t.revisions[0].status)
  const auditCount = conversation.turns.reduce((sum, t) => sum + t.revisions[0].audits.length, 0)
  catalogue.push({ id: spec.id, label: spec.label, file, turns: statuses.length,
    description: auditCount + ' saved audits · original passages included', origin: 'saved_inference' })
}
// Prepare all conversations before replacing any published export.
for (const { file, output } of exports) await fs.writeFile(path.join(root, file), output + '\n')
await fs.writeFile(path.join(root, 'catalogue.json'), JSON.stringify(catalogue, null, 2) + '\n')
console.log('Packaged and imported ' + catalogue.length + ' actual conversations from ' + run + '.')
