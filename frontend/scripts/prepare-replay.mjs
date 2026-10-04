// Copy the recorded conversations and the three-paper corpus into public/replay/ so the
// replay build needs no backend. Run automatically by `npm run replay` and `npm run build:replay`.
import { copyFileSync, mkdirSync, readFileSync, rmSync, writeFileSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'

const frontend = join(dirname(fileURLToPath(import.meta.url)), '..')
const source = join(frontend, '..', 'data', 'demo', 'conversations')
const target = join(frontend, 'public', 'replay')

rmSync(target, { recursive: true, force: true })
mkdirSync(target, { recursive: true })
const catalogue = JSON.parse(readFileSync(join(source, 'catalogue.json'), 'utf8'))
writeFileSync(join(target, 'catalogue.json'), JSON.stringify(catalogue))
for (const entry of catalogue) {
  if (entry.file.includes('/') || entry.file.includes('\\')) throw new Error(`Unexpected path: ${entry.file}`)
  copyFileSync(join(source, entry.file), join(target, entry.file))
}
const corpus = readFileSync(join(source, 'corpus.jsonl'), 'utf8').split('\n').filter(Boolean).map(line => JSON.parse(line))
writeFileSync(join(target, 'corpus.json'), JSON.stringify(corpus))
console.log(`Replay data: ${catalogue.length} conversations, ${corpus.length} passages → public/replay/`)
