import { isGuidedDemo, demoSuffix } from './demo'
import React, { useEffect, useRef, useState } from 'react'
import { BrowserRouter, Routes, Route, useNavigate, useLocation } from 'react-router-dom'
import { AnswerPage } from './pages/AnswerPage'
import { ExplorerPage } from './pages/ExplorerPage'
import { DocumentPage } from './pages/DocumentPage'
import { AuditPage } from './pages/AuditPage'
import { fetchCorpusStats, fetchHealth, loadRecentThreads, saveThread } from './api/client'
import { useStore } from './store'

const auditOnly = import.meta.env.VITE_AUDIT_ONLY === '1'

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
const IconCompass   = (p: { size?: number; sw?: number; style?: React.CSSProperties }) =>
  <I {...p}><circle cx="12" cy="12" r="9"/><path d="m15 9-4 1.5L9.5 15l4-1.5L15 9Z"/></I>
const IconHistory   = (p: { size?: number; sw?: number; style?: React.CSSProperties }) =>
  <I {...p}><path d="M3 12a9 9 0 1 0 3-6.7L3 8M3 3v5h5"/><path d="M12 7v5l3 2"/></I>
const IconChevDown  = (p: { size?: number; sw?: number; style?: React.CSSProperties }) =>
  <I {...p}><path d="m6 9 6 6 6-6"/></I>
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
  const { threadId, setThreadId } = useStore()
  const [open, setOpen] = useState(false)
  const [threads, setThreads] = useState<string[]>([])
  const ref = useRef<HTMLDivElement>(null)

  useEffect(() => {
    setThreads(loadRecentThreads())
  }, [threadId])

  useEffect(() => {
    function onDoc(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false)
    }
    document.addEventListener('mousedown', onDoc)
    return () => document.removeEventListener('mousedown', onDoc)
  }, [])

  return (
    <div ref={ref} style={{ position: 'relative' }}>
      <button
        onClick={() => setOpen((v) => !v)}
        style={{
          display: 'inline-flex', alignItems: 'center', gap: 7,
          padding: '6px 10px 6px 11px',
          border: '1px solid var(--rule)', borderRadius: 7,
          background: 'var(--panel)',
          color: 'var(--ink-soft)', fontSize: 12, fontWeight: 500,
          maxWidth: 260,
        }}
      >
        <IconHistory size={12} sw={2} style={{ color: 'var(--faint)', flexShrink: 0 }} />
        <span style={{
          fontFamily: 'var(--serif)', fontStyle: 'italic',
          fontSize: 13, color: 'var(--ink)',
          overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
          maxWidth: 180,
        }}>
          {threadId || 'New thread'}
        </span>
        <IconChevDown size={11} sw={2} style={{ color: 'var(--faint)' }} />
      </button>

      {open && threads.length > 0 && (
        <div style={{
          position: 'absolute', top: 'calc(100% + 6px)', right: 0,
          minWidth: 280,
          background: 'var(--panel)',
          border: '1px solid var(--rule)',
          borderRadius: 8,
          boxShadow: 'var(--shadow-float)',
          padding: 6, zIndex: 50,
        }}>
          <div className="vm-eyebrow" style={{ padding: '6px 10px 4px' }}>Recent threads</div>
          {threads.map((t) => (
            <button
              key={t}
              onClick={() => { setThreadId(t); saveThread(t); setOpen(false) }}
              style={{
                display: 'flex', alignItems: 'baseline', gap: 8,
                width: '100%', padding: '8px 10px',
                border: 'none', background: t === threadId ? 'var(--accent-soft)' : 'transparent',
                color: 'var(--ink)', textAlign: 'left', borderRadius: 5,
              }}
              onMouseEnter={(e) => { if (t !== threadId) e.currentTarget.style.background = 'var(--panel-2)' }}
              onMouseLeave={(e) => { if (t !== threadId) e.currentTarget.style.background = 'transparent' }}
            >
              <span style={{
                fontFamily: 'var(--serif)', fontStyle: 'italic',
                fontSize: 13.5, color: 'var(--ink)', flex: 1,
                overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
              }}>{t}</span>
            </button>
          ))}
          <div style={{ borderTop: '1px solid var(--rule-soft)', margin: '4px 0' }} />
          <button
            onClick={() => {
              const newId = `session-${Date.now()}`
              setThreadId(newId)
              setOpen(false)
            }}
            style={{
              display: 'flex', alignItems: 'center', gap: 6,
              width: '100%', padding: '8px 10px', borderRadius: 5,
              border: 'none', background: 'transparent',
              color: 'var(--accent)', fontSize: 12, fontWeight: 600,
              textAlign: 'left',
            }}
          >
            + Start a new thread
          </button>
        </div>
      )}
    </div>
  )
}

// ── StatusPill ──────────────────────────────────────────────────────────────
function StatusPill() {
  const [text, setText] = useState(isGuidedDemo ? 'fixed examples · no live model' : 'checking…')
  const [healthy, setHealthy] = useState<boolean | null>(null)

  useEffect(() => {
    let cancelled = false
    async function poll() {
      if (isGuidedDemo) { setHealthy(null); return }
      try {
        const [health, stats] = await Promise.all([
          fetchHealth().catch(() => null),
          fetchCorpusStats().catch(() => null),
        ])
        if (cancelled) return
        if (health) {
          setHealthy(health.status === 'ok')
          const model = stats?.embedding_model ?? health.llm ?? 'mimo-v2.5'
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
    <div style={{
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
  const isExplore = location.pathname === '/explore'

  return (
    <header className="vm-header" style={{
      height: 60, flexShrink: 0,
      display: 'flex', alignItems: 'center', gap: 24,
      padding: '0 24px',
      background: 'var(--canvas)',
      borderBottom: '1px solid var(--rule)',
    }}>
      <BrandMark />
      {!auditOnly && <a href={isGuidedDemo ? "/" : "/?demo=1"} style={{fontSize: 12, color: "var(--accent)"}}>{isGuidedDemo ? "Live mode" : "Guided demo"}</a>}
      <span className="vm-research-label" style={{ fontSize: 11, color: "var(--muted)" }}>Research demo · not clinical advice</span>

      <span style={{ width: 1, height: 22, background: 'var(--rule)', margin: '0 2px' }} />

      <nav style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
        {!auditOnly && <><NavTab
          active={isAsk}
          label="Ask"
          sub="⌘K"
          icon={IconBook}
          onClick={() => navigate('/' + demoSuffix)}
        />
        <NavTab
          active={isExplore}
          label="Explore"
          icon={IconCompass}
          onClick={() => navigate('/explore' + demoSuffix)}
        /></>}
        <NavTab active={location.pathname === '/audit' || auditOnly} label="Audit" icon={IconBook}
          onClick={() => { window.location.href = '/audit' }} />
      </nav>

      <span style={{ flex: 1 }} />

      {isAsk && !auditOnly && <StatusPill />}

      {!auditOnly && <ThreadHistoryButton />}

      <ThemePopover theme={theme} setTheme={setTheme} />
    </header>
  )
}

// ── App ─────────────────────────────────────────────────────────────────────
function GuidedBanner() {
  const location = useLocation()
  if (!isGuidedDemo || location.pathname === '/audit') return null
  return <div role="status" style={{padding: '8px 16px', background: 'var(--accent-soft)', color: 'var(--ink)', fontSize: 12, textAlign: 'center'}}>GUIDED DEMO · Authored fixed examples and illustrative steps. No live retrieval, model calls or measured scores.</div>
}

export default function App() {
  const [theme, setTheme] = useState<Theme>('paper')

  useEffect(() => {
    document.documentElement.dataset.theme = theme === 'paper' ? '' : theme
    if (theme === 'paper') delete document.documentElement.dataset.theme
  }, [theme])

  // Cmd/Ctrl+K → Ask page
  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault()
        window.location.pathname !== '/' && (window.location.href = '/' + demoSuffix)
      }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [])

  return (
    <BrowserRouter>
      <div style={{ height: '100vh', display: 'flex', flexDirection: 'column', overflow: 'hidden', background: 'var(--canvas)' }}>
        <Header theme={theme} setTheme={setTheme} />
        <GuidedBanner />
        <main style={{ flex: 1, overflow: 'hidden' }}>
          <Routes>
            <Route path="/"                   element={auditOnly ? <AuditPage /> : <AnswerPage />} />
            <Route path="/audit"              element={<AuditPage />} />
            <Route path="/explore"            element={<ExplorerPage />} />
            <Route path="/document/:citation" element={<DocumentPage />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  )
}
