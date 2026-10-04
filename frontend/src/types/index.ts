// REST types — generated from openapi.json, do not edit.
// Regenerate with: npm run generate-types
export type { components, paths, operations } from './api.gen'
import type { components } from './api.gen'

export type ChunkOut             = components['schemas']['ChunkOut']
export type DocumentResponse     = components['schemas']['DocumentResponse']
export type DocumentChunkSlim    = components['schemas']['DocumentChunkSlim']
export type ChunkSlim            = components['schemas']['ChunkSlim']
export type ChunkContextResponse = components['schemas']['ChunkContextResponse']
export type CorpusStats          = components['schemas']['CorpusStats']
// AnswerOut is WebSocket-only (DoneEvent) — import from './ws' directly.
