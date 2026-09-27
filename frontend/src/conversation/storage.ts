import type { Conversation } from './model'
import { validateConversation } from './model.ts'

let database: Promise<IDBDatabase> | undefined
function open() {
  return database ??= new Promise((resolve, reject) => {
    const request = indexedDB.open('veritasmed-conversations', 1)
    request.onupgradeneeded = () => request.result.createObjectStore('conversations', { keyPath: 'id' })
    request.onsuccess = () => resolve(request.result)
    request.onerror = () => reject(request.error)
    request.onblocked = () => reject(new Error('Local storage upgrade is blocked by another tab.'))
  })
}
export async function saveConversation(value: Conversation) {
  const db = await open()
  return new Promise<void>((resolve, reject) => {
    const transaction = db.transaction('conversations', 'readwrite')
    transaction.objectStore('conversations').put(value)
    transaction.oncomplete = () => resolve()
    transaction.onerror = transaction.onabort = () => reject(transaction.error)
  })
}
export async function loadConversations() {
  const db = await open()
  const values = await new Promise<unknown[]>((resolve, reject) => {
    const request = db.transaction('conversations', 'readonly').objectStore('conversations').getAll()
    request.onsuccess = () => resolve(request.result)
    request.onerror = () => reject(request.error)
  })
  const conversations: Conversation[] = []
  let rejected = 0
  const rejectedIds: string[] = []
  for (const value of values) {
    try {
      const conversation = await validateConversation(value)
      for (const turn of conversation.turns) for (const revision of turn.revisions) {
        if (revision.status === 'running') { revision.status = 'cancelled'; revision.error = 'Interrupted before completion (page closed or reloaded).' }
      }
      conversations.push(conversation)
    } catch {
      rejected++
      if (value && typeof value === 'object' && 'id' in value && typeof value.id === 'string') rejectedIds.push(value.id)
    }
  }
  return { conversations, rejected, rejectedIds }
}
