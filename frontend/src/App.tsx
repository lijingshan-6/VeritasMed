import { isReplayOnly } from './demo'
import React, { useEffect, useRef, useState } from 'react'
import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { AnswerPage } from './pages/AnswerPage'
import { DocumentPage } from './pages/DocumentPage'
import { fetchCorpusStats, fetchHealth } from './api/client'
import { initializeConversations } from './store'


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

// ── StatusPill ──────────────────────────────────────────────────────────────
function StatusPill() {
  const [text, setText] = useState(isReplayOnly ? 'Replay · recorded answers' : 'checking…')
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
  return (
    <header className="ws-header">
      <a href={import.meta.env.BASE_URL} className="ws-brand" aria-label="VeritasMed home"><BrandMark /></a>
      <span className="ws-tagline">Medical literature answers you can check</span>
      <span style={{ flex: 1 }} />
      <StatusPill />
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

  // Cmd/Ctrl+K focuses the question box.
  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault()
        document.querySelector<HTMLTextAreaElement>('.ws-composer textarea')?.focus()
      }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [])

  return (
    <BrowserRouter basename={import.meta.env.BASE_URL.replace(/\/$/, '')}>
      <div className="ws-app">
        <Header theme={theme} setTheme={setTheme} />
        <div className="ws-body">
          <Routes>
            <Route path="/"                   element={<AnswerPage />} />
            <Route path="/document/:citation" element={<DocumentPage />} />
          </Routes>
        </div>
      </div>
    </BrowserRouter>
  )
}
