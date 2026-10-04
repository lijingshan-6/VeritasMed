import { create } from 'zustand'
import type { ChunkOut } from '../types'
import type { AnswerOut, TimelineNode } from '../types/ws'
import type { AuditRecord } from '../api/audit'
import type { Conversation, Revision } from '../conversation/model.ts'
import { attachAudit, contextFor, fingerprint, newConversation, newId, now } from '../conversation/model.ts'
import { loadConversations, saveConversation } from '../conversation/storage.ts'
import { cancelStream } from '../api/streamConnection.js'

type Target = { conversationId: string; turnId: string; revisionId: string }
type View = { activeQuery: string; result: AnswerOut | null; timeline: TimelineNode[]; liveChunks: ChunkOut[]; errorMessage: string | null; isStreaming: boolean }
const emptyView: View = { activeQuery: '', result: null, timeline: [], liveChunks: [], errorMessage: null, isStreaming: false }
const unreadableIds = new Set<string>()
export interface AppState extends View {
  conversations: Conversation[]; hydrated: boolean; storageError: string | null
  threadId: string; selectedTurnId: string | null; selectedRevisionId: string | null
  activeRequest: Target | null; useContext: boolean
  query: string; selectedChunkId: string | null
  setQuery: (query: string) => void; setSelectedChunkId: (id: string | null) => void
  setUseContext: (use: boolean) => void
  setThreadId: (id: string) => void; newThread: () => void
  selectRevision: (turnId: string, revisionId: string) => void
  begin: (query: string, origin: Revision['origin'], regenerate?: boolean) => Target | null
  patchRequest: (target: Target, patch: (revision: Revision) => Revision) => void
  finish: (target: Target, result?: AnswerOut, error?: string, cancelled?: boolean) => Promise<void>
  saveAudit: (target: Target, record: AuditRecord) => Promise<void>
  addConversation: (conversation: Conversation, replaceExisting?: boolean) => void
}
function view(conversations: Conversation[], cid: string, tid: string | null, rid: string | null): View {
  const turn = conversations.find(c => c.id === cid)?.turns.find(t => t.id === tid)
  const revision = turn?.revisions.find(r => r.id === rid)
  if (!revision) return emptyView
  return { activeQuery: turn.question, result: revision.result, timeline: revision.timeline, liveChunks: revision.liveChunks,
    errorMessage: revision.error, isStreaming: revision.status === 'running' }
}
function mutate(conversations: Conversation[], target: Target, fn: (r: Revision) => Revision) {
  return conversations.map(c => c.id !== target.conversationId ? c : { ...c, updated_at: now(), turns: c.turns.map(t => t.id !== target.turnId ? t : { ...t, revisions: t.revisions.map(r => r.id === target.revisionId ? fn(r) : r) }) })
}
function same(a: Target | null, b: Target) { return a?.conversationId === b.conversationId && a?.turnId === b.turnId && a?.revisionId === b.revisionId }
function updateView(state: AppState, conversations: Conversation[]) {
  return { conversations, ...view(conversations, state.threadId, state.selectedTurnId, state.selectedRevisionId) }
}
export const useStore = create<AppState>((set, get) => ({
  ...emptyView, conversations: [], hydrated: false, storageError: null,
  threadId: '', selectedTurnId: null, selectedRevisionId: null, activeRequest: null, useContext: true,
  query: '', selectedChunkId: null,
  setQuery: query => set({ query }), setSelectedChunkId: selectedChunkId => set({ selectedChunkId }),
  setUseContext: useContext => set({ useContext }),
  setThreadId: id => {
    const conversation = get().conversations.find(c => c.id === id)
    if (!conversation) return
    const turn = conversation.turns.at(-1), revision = turn?.revisions.at(-1)
    set({ threadId: id, selectedTurnId: turn?.id ?? null, selectedRevisionId: revision?.id ?? null, query: '', selectedChunkId: null,
      ...view(get().conversations, id, turn?.id, revision?.id) })
  },
  newThread: () => {
    const c = newConversation()
    set(s => ({ conversations: [...s.conversations, c] }))
    get().setThreadId(c.id)
  },
  selectRevision: (tid, rid) => {
    set(s => ({ selectedTurnId: tid, selectedRevisionId: rid, selectedChunkId: null, ...view(s.conversations, s.threadId, tid, rid) }))
  },
  begin: (question, origin, regenerate = false) => {
    const s = get()
    if (!s.hydrated || s.activeRequest || !question.trim()) return null
    const conversation = s.conversations.find(c => c.id === s.threadId)
    if (!conversation) return null
    const previous = conversation.turns.find(t => t.id === s.selectedTurnId)
    const oldRevision = previous?.revisions.find(r => r.id === s.selectedRevisionId)
    const selection = regenerate && oldRevision ? { context: oldRevision.context, omitted: oldRevision.omitted_context }
      : s.useContext && origin === 'live' ? contextFor(conversation, s.selectedTurnId, s.selectedRevisionId) : { context: [], omitted: 0 }
    const revision: Revision = { id: newId(), created_at: now(), status: 'running', origin, context: selection.context, omitted_context: selection.omitted,
      result: null, timeline: [], liveChunks: [], error: null, audits: [] }
    const turnId = regenerate && previous ? previous.id : newId()
    const target = { conversationId: conversation.id, turnId, revisionId: revision.id }
    const turns = regenerate && previous ? conversation.turns.map(t => t.id === previous.id ? { ...t, revisions: [...t.revisions, revision] } : t)
      : [...conversation.turns, { id: turnId, question, parent_turn_id: previous?.id ?? null, revisions: [revision] }]
    const conversations = s.conversations.map(c => c.id === conversation.id ? { ...c, title: c.turns.length ? c.title : question.slice(0, 100), updated_at: now(), turns } : c)
    set({ conversations, selectedTurnId: turnId, selectedRevisionId: revision.id, activeRequest: target, query: '', selectedChunkId: null,
      ...view(conversations, conversation.id, turnId, revision.id) })
    return target
  },
  patchRequest: (target, patch) => {
    if (!same(get().activeRequest, target)) return
    set(s => updateView(s, mutate(s.conversations, target, patch)))
  },
  finish: async (target, result, error, cancelled = false) => {
    const hashes = result ? await fingerprint(result) : {}
    if (!same(get().activeRequest, target)) return
    set(s => ({ ...updateView(s, mutate(s.conversations, target, r => ({ ...r, ...hashes, result: result ?? null,
      status: cancelled ? 'cancelled' : error ? 'failed' : result?.conversation_context?.needs_clarification ? 'clarification' : 'complete',
      error: error ?? (cancelled ? 'Stopped before completion. No complete answer or audit was created.' : null), liveChunks: [],
      timeline: r.timeline.map(n => n.status === 'running' ? { ...n, status: 'error', summary: 'Interrupted' } : n) }))), activeRequest: null }))
  },
  saveAudit: async (target, record) => {
    const revision = get().conversations.find(c => c.id === target.conversationId)?.turns.find(t => t.id === target.turnId)?.revisions.find(r => r.id === target.revisionId)
    if (!revision) throw new Error('Original answer revision is unavailable.')
    const audit = await attachAudit(revision, record)
    set(s => updateView(s, mutate(s.conversations, target, r => ({ ...r, audits: [...r.audits, audit] }))))
  },
  addConversation: (conversation, replaceExisting = false) => {
    if (unreadableIds.has(conversation.id)) throw new Error('An unreadable local record has this ID. Import in another browser profile to avoid overwriting it.')
    const existing = get().conversations.find(c => c.id === conversation.id)
    if (existing && JSON.stringify(existing) !== JSON.stringify(conversation)) {
      // Read-only replay holds no user work, so a newer bundled recording replaces the stored copy.
      if (!replaceExisting) throw new Error('A different version of this conversation already exists here. Import in another browser profile to preserve both.')
      set(s => ({ conversations: s.conversations.map(c => c.id === conversation.id ? conversation : c) }))
    }
    if (!existing) set(s => ({ conversations: [...s.conversations, conversation] }))
    get().setThreadId(conversation.id)
  },
}))

let initialization: Promise<void> | undefined
export function initializeConversations() {
  return initialization ??= (async () => {
    let conversations: Conversation[] = [], storageError: string | null = null
    try {
      const loaded = await loadConversations()
      conversations = loaded.conversations
      loaded.rejectedIds.forEach(id => unreadableIds.add(id))
      if (loaded.rejected) storageError = `${loaded.rejected} local records could not be read. They remain in browser storage and have not been overwritten.`
      const legacy = JSON.parse(localStorage.getItem('vm_threads') ?? '[]')
      if (Array.isArray(legacy)) for (const id of legacy) if (typeof id === 'string' && !unreadableIds.has(id) && !conversations.some(c => c.id === id)) {
        conversations.push({ ...newConversation(id), title: `Legacy ID · ${id}`, legacy: true })
      }
    } catch { storageError = 'Local history is unavailable. New work remains in this tab; export it before leaving.' }
    if (!conversations.length) conversations.push(newConversation())
    useStore.setState({ conversations, storageError, hydrated: true })
    let selected: string | null = null
    try { selected = localStorage.getItem('vm_selected_conversation') } catch { /* Storage warning already shown. */ }
    useStore.getState().setThreadId(conversations.find(c => c.id === selected)?.id ?? conversations.at(-1)!.id)
    try {
      const selection = JSON.parse(localStorage.getItem('vm_selected_answer') ?? 'null')
      if (selection?.conversationId === useStore.getState().threadId && conversations.find(c => c.id === selection.conversationId)?.turns.some(t => t.id === selection.turnId && t.revisions.some(r => r.id === selection.revisionId))) {
        useStore.getState().selectRevision(selection.turnId, selection.revisionId)
      }
    } catch { /* Default to the most recent answer. */ }
    let queue = Promise.resolve()
    useStore.subscribe((state, previous) => {
      for (const c of state.conversations) if (previous.conversations.find(p => p.id === c.id) !== c) {
        queue = queue.then(() => saveConversation(c)).catch(() => {
          useStore.setState({ storageError: 'Could not save local history (storage unavailable or full). Nothing was evicted. Export your conversation before leaving.' })
        })
      }
      if (state.threadId !== previous.threadId || state.selectedRevisionId !== previous.selectedRevisionId) {
        try {
          localStorage.setItem('vm_selected_conversation', state.threadId)
          localStorage.setItem('vm_selected_answer', JSON.stringify({ conversationId: state.threadId, turnId: state.selectedTurnId, revisionId: state.selectedRevisionId }))
        } catch { /* IDB preserves the actual records. */ }
      }
    })
  })()
}

// Editing the store during Vite development must not leave a fresh, unhydrated
// store attached to an old request. Treat it like an interrupted page session.
if (import.meta.hot) import.meta.hot.dispose(() => {
  cancelStream()
  const target = useStore.getState().activeRequest
  if (target) void useStore.getState().finish(target, undefined, undefined, true)
})
