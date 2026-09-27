import type React from 'react'

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
export const IconCheck     = (p: { size?: number; sw?: number }) => <I {...p}><path d="m5 12 4 4L19 7"/></I>
export const IconAlert     = (p: { size?: number; sw?: number }) => <I {...p}><path d="M12 9v4M12 17h.01"/><path d="M10.3 3.86 1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0Z"/></I>
export const IconRefresh   = (p: { size?: number; sw?: number }) => <I {...p}><path d="M3 12a9 9 0 0 1 15.5-6.3L21 8M21 3v5h-5M21 12a9 9 0 0 1-15.5 6.3L3 16M3 21v-5h5"/></I>
export const IconCopy      = (p: { size?: number; sw?: number }) => <I {...p}><rect x="9" y="9" width="11" height="11" rx="2"/><path d="M5 15V5a2 2 0 0 1 2-2h10"/></I>
export const IconBookmark  = (p: { size?: number; sw?: number }) => <I {...p}><path d="M19 21 12 16.5 5 21V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2v16Z"/></I>
export const IconSparkle   = (p: { size?: number; sw?: number }) => <I {...p}><path d="M12 3v3M12 18v3M3 12h3M18 12h3M5.6 5.6l2.1 2.1M16.3 16.3l2.1 2.1M5.6 18.4l2.1-2.1M16.3 7.7l2.1-2.1"/></I>
export const IconArrowUp   = (p: { size?: number; sw?: number; style?: React.CSSProperties }) => <I {...p}><path d="M12 19V5M6 11l6-6 6 6"/></I>
export const IconChevRight = (p: { size?: number; sw?: number; style?: React.CSSProperties }) => <I {...p}><path d="m9 18 6-6-6-6"/></I>
export const CITE_VARS = ['--c0','--c1','--c2','--c3','--c4','--c5','--c6','--c7']
