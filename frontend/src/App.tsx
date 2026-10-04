import { isReplayOnly } from './demo'
import React, { useEffect, useRef, useState } from 'react'
import { BrowserRouter, Routes, Route, useNavigate, useLocation } from 'react-router-dom'
import { AnswerPage } from './pages/AnswerPage'
import { DocumentPage } from './pages/DocumentPage'
import { fetchCorpusStats, fetchHealth } from './api/client'
import { useStore, initializeConversations } from './store'


// ── SVG base ───────────────────────────────────────────────────────────────
function I({ size = 16, sw = 1.6, children, style }: {
  size?: number; sw?: number; children: React.ReactNode; style?: React.CSSProperties
}) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none"
      stroke="currentColor" strokeWidth={sw} strokeLinecap="round"
      strokeLinejoin="round" aria-hidden="true" style={style}>
      {children}
    </svg>
  )
}
const IconBook      = (p: { size?: number; sw?: number; style?: React.CSSProperties }) =>
  <I {...p}><path d="M4 4.5A2.5 2.5 0 0 1 6.5 2H20v17H6.5A2.5 2.5 0 0 0 4 21.5v-17Z"/><path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/></I>
const IconHistory   = (p: { size?: number; sw?: number; style?: React.CSSProperties }) =>
  <I {...p}><path d="M3 12a9 9 0 1 0 3-6.7L3 8M3 3v5h5"/><path d="M12 7v5l3 2"/></I>
const IconSettings  = (p: { size?: number; sw?: number; style?: React.CSSProperties }) =>
  <I {...p}><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.6 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.6a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09A1.65 1.65 0 0 0 15 4.6a1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9c.06.32.21.62.42.85.21.22.51.35.81.36H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1Z"/></I>

// ── BrandMark ───────────────────────────────────────────────────────────────
function BrandMark() {
  return (
    <div style={{ display: 'inline-flex', alignItems: 'center', gap: 9 }}>
      <span style={{
        width: 28, height: 28, borderRadius: 6,
        background: 'var(--ink)', color: 'var(--canvas)',
        display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
        fontFamily: 'var(--serif)', fontStyle: 'italic', fontWeight: 400,
        fontSize: 19, lineHeight: 1, paddingBottom: 1,
        letterSpacing: '-0.04em',
        position: 'relative',
      }}>
        V
        <span style={{
          position: 'absolute', bottom: 5, left: '50%', transform: 'translateX(-50%)',
          width: 12, height: 1, background: 'var(--accent)',
        }} />
      </span>
      <span style={{ display: 'inline-flex', alignItems: 'baseline', gap: 0 }}>
        <span style={{
          fontFamily: 'var(--serif)', fontStyle: 'italic',
          fontSize: 22, lineHeight: 1, color: 'var(--ink)',
          letterSpacing: '-0.025em',
        }}>Veritas</span>
        <span style={{
          fontFamily: 'var(--sans)', fontWeight: 600,
          fontSize: 18, color: 'var(--accent)',
          letterSpacing: '-0.005em',
        }}>Med</span>
      </span>
    </div>
  )
}

// ── NavTab ──────────────────────────────────────────────────────────────────
function NavTab({ active, label, sub, onClick, icon: Icon }: {
  active: boolean
  label: string
  sub?: string
  onClick: () => void
  icon: React.ComponentType<{ size?: number; sw?: number; style?: React.CSSProperties }>
}) {
  return (
    <button
      onClick={onClick}
      style={{
        display: 'inline-flex', alignItems: 'baseline', gap: 7,
        padding: '8px 12px',
        border: 'none', background: 'transparent',
        color: active ? 'var(--ink)' : 'var(--muted)',
        fontSize: 13, fontWeight: 600, letterSpacing: '-0.005em',
        whiteSpace: 'nowrap',
        position: 'relative',
        transition: 'color 120ms',
      }}
      onMouseEnter={(e) => { if (!active) e.currentTarget.style.color = 'var(--ink-soft)' }}
      onMouseLeave={(e) => { if (!active) e.currentTarget.style.color = 'var(--muted)' }}
    >
      <Icon size={13} sw={2} style={{ alignSelf: 'center' }} />
      {label}
      {sub && (
        <span className="vm-mono" style={{ fontSize: 9.5, color: 'var(--faint)' }}>
          {sub}
        </span>
      )}
      {active && (
        <span style={{
          position: 'absolute', bottom: -1, left: 12, right: 12,
          height: 1, background: 'var(--ink)',
        }} />
      )}
    </button>
  )
}

// ── ThreadHistoryButton ─────────────────────────────────────────────────────
function ThreadHistoryButton() {
  const { conversations, threadId, setThreadId, newThread, hydrated } = useStore()
  return <div className="vm-conversation-picker">
    <IconHistory size={12} />
    <select aria-label="Conversation" disabled={!hydrated} value={threadId} onChange={e => setThreadId(e.target.value)}>
      {conversations.slice().sort((a, b) => b.updated_at.localeCompare(a.updated_at)).map(c => <option key={c.id} value={c.id}>{c.title} · {c.turns.length} turns</option>)}
    </select>
    {!isReplayOnly && <button disabled={!hydrated} onClick={newThread}>+ New</button>}
  </div>
}

// ── StatusPill ──────────────────────────────────────────────────────────────
function StatusPill() {
  const [text, setText] = useState(isReplayOnly ? 'saved inference · no API calls' : 'checking…')
  const [healthy, setHealthy] = useState<boolean | null>(null)

  useEffect(() => {
    let cancelled = false
    async function poll() {
      if (isReplayOnly) { setHealthy(null); return }
      try {
        const [health, stats] = await Promise.all([
          fetchHealth().catch(() => null),
          fetchCorpusStats().catch(() => null),
        ])
        if (cancelled) return
        if (health) {
          setHealthy(health.status === 'ok')
          const model = stats?.embedding_model ?? health.llm ?? 'unknown'
          setText(health.status === 'ok' ? `ready · ${model}` : `needs setup · ${health.qdrant} / ${health.llm}`)
        } else {
          setHealthy(false)
          setText('backend offline')
        }
      } catch {
        if (!cancelled) { setHealthy(false); setText('offline') }
      }
    }
    poll()
    const id = setInterval(poll, 30_000)
    return () => { cancelled = true; clearInterval(id) }
  }, [])

  const dotColor = healthy === null ? 'var(--faint)' : healthy ? 'var(--verified)' : 'var(--error)'
  const dotShadow = healthy ? '0 0 0 3px var(--verified-soft)' : 'none'

  return (
    <div className="vm-backend-status" style={{
      display: 'inline-flex', alignItems: 'center', gap: 8,
      padding: '5px 11px 5px 9px',
      border: '1px solid var(--rule)', borderRadius: 999,
      fontSize: 11, color: 'var(--muted)',
    }}>
      <span style={{
        width: 6, height: 6, borderRadius: '50%',
        background: dotColor,
        boxShadow: dotShadow,
        display: 'inline-block',
        transition: 'background 300ms',
      }} />
      <span className="vm-mono">{text}</span>
    </div>
  )
}

// ── ThemeSettings ───────────────────────────────────────────────────────────
type Theme = 'paper' | 'midnight' | 'clinical'

function ThemePopover({ theme, setTheme }: { theme: Theme; setTheme: (t: Theme) => void }) {
  const [open, setOpen] = useState(false)
  const ref = useRef<HTMLDivElement>(null)

  useEffect(() => {
    function onDoc(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false)
    }
    document.addEventListener('mousedown', onDoc)
    return () => document.removeEventListener('mousedown', onDoc)
  }, [])

  const options: { id: Theme; label: string }[] = [
    { id: 'paper', label: 'Paper' },
    { id: 'midnight', label: 'Dark' },
    { id: 'clinical', label: 'Cool' },
  ]

  return (
    <div ref={ref} style={{ position: 'relative' }}>
      <button
        onClick={() => setOpen((v) => !v)}
        title="Theme"
        style={{
          padding: 7, borderRadius: 7,
          border: '1px solid var(--rule)', background: 'var(--panel)',
          color: 'var(--ink-soft)',
        }}
      >
        <IconSettings size={14} sw={2} />
      </button>
      {open && (
        <div style={{
          position: 'absolute', top: 'calc(100% + 6px)', right: 0,
          background: 'var(--panel)',
          border: '1px solid var(--rule)',
          borderRadius: 8,
          boxShadow: 'var(--shadow-float)',
          padding: 6, zIndex: 50, minWidth: 140,
        }}>
          <div className="vm-eyebrow" style={{ padding: '6px 10px 4px' }}>Theme</div>
          {options.map((o) => (
            <button
              key={o.id}
              onClick={() => { setTheme(o.id); setOpen(false) }}
              style={{
                display: 'flex', alignItems: 'center', gap: 8,
                width: '100%', padding: '8px 10px',
                border: 'none',
                background: o.id === theme ? 'var(--accent-soft)' : 'transparent',
                color: o.id === theme ? 'var(--accent-ink)' : 'var(--ink)',
                fontSize: 13, fontWeight: o.id === theme ? 600 : 400,
                borderRadius: 5, textAlign: 'left',
              }}
              onMouseEnter={(e) => { if (o.id !== theme) e.currentTarget.style.background = 'var(--panel-2)' }}
              onMouseLeave={(e) => { if (o.id !== theme) e.currentTarget.style.background = 'transparent' }}
            >
              {o.label}
            </button>
          ))}
        </div>
      )}
    </div>
  )
}

// ── Header ──────────────────────────────────────────────────────────────────
function Header({ theme, setTheme }: { theme: Theme; setTheme: (t: Theme) => void }) {
  const navigate = useNavigate()
  const location = useLocation()
  const isAsk     = location.pathname === '/'

  return (
    <header className="vm-header" style={{
      height: 60, flexShrink: 0,
      display: 'flex', alignItems: 'center', gap: 24,
      padding: '0 24px',
      background: 'var(--canvas)',
      borderBottom: '1px solid var(--rule)',
    }}>
      <BrandMark />
      <span className="vm-research-label" style={{ fontSize: 11, color: "var(--muted)" }}>Research demo · not clinical advice</span>

      <span style={{ width: 1, height: 22, background: 'var(--rule)', margin: '0 2px' }} />

      <nav style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
        <NavTab active={isAsk} label="Ask" sub="⌘K" icon={IconBook} onClick={() => navigate('/')} />
      </nav>

      <span style={{ flex: 1 }} />

      {isAsk && <StatusPill />}

      <ThreadHistoryButton />

      <ThemePopover theme={theme} setTheme={setTheme} />
    </header>
  )
}

// ── App ───────────────────────────────────────────────────────────────────────
export default function App() {
  const [theme, setTheme] = useState<Theme>('paper')
  useEffect(() => { void initializeConversations() }, [])

  useEffect(() => {
    document.documentElement.dataset.theme = theme === 'paper' ? '' : theme
    if (theme === 'paper') delete document.documentElement.dataset.theme
  }, [theme])

  // Cmd/Ctrl+K → Ask page
  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault()
        if (window.location.pathname !== '/') window.location.href = '/'
      }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [])

  return (
    <BrowserRouter>
      <div style={{ height: '100vh', display: 'flex', flexDirection: 'column', overflow: 'hidden', background: 'var(--canvas)' }}>
        <Header theme={theme} setTheme={setTheme} />
        <main style={{ flex: 1, overflow: 'hidden' }}>
          <Routes>
            <Route path="/"                   element={<AnswerPage />} />
            <Route path="/document/:citation" element={<DocumentPage />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  )
}
