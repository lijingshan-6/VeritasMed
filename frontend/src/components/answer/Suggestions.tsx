import { isConversationDemo, isMedicalDemo } from '../../demo'
import { IconSparkle, IconArrowUp, IconChevRight } from './Icons'

export function FollowUps({ items, onPick }: { items: string[]; onPick: (q: string) => void }) {
  return (
    <div style={{ marginTop: 36 }}>
      <div className="vm-eyebrow" style={{ marginBottom: 10 }}>
        <span style={{ display: 'inline-flex', alignItems: 'center', gap: 6 }}>
          <IconSparkle size={11} sw={2} /> Example questions (independent)
        </span>
      </div>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
        {items.map((q, i) => (
          <button
            key={i}
            onClick={() => onPick(q)}
            style={{
              display: 'flex', alignItems: 'center', gap: 10,
              padding: '11px 4px',
              borderTop: i === 0 ? '1px solid var(--rule)' : 'none',
              borderBottom: '1px solid var(--rule)',
              background: 'transparent',
              color: 'var(--ink-soft)',
              fontSize: 14, fontFamily: 'var(--serif)',
              letterSpacing: '-0.005em',
              textAlign: 'left', lineHeight: 1.4,
              transition: 'color 120ms',
            }}
            onMouseEnter={(e) => e.currentTarget.style.color = 'var(--accent)'}
            onMouseLeave={(e) => e.currentTarget.style.color = 'var(--ink-soft)'}
          >
            <IconArrowUp size={13} sw={2} style={{ transform: 'rotate(45deg)', color: 'var(--faint)', flexShrink: 0 }} />
            <span style={{ flex: 1 }}>{q}</span>
            <IconChevRight size={13} sw={2} style={{ color: 'var(--faint)', flexShrink: 0 }} />
          </button>
        ))}
      </div>
    </div>
  )
}

export function EmptyState({ suggestedQueries, onPickQuery }: {
  suggestedQueries: string[]
  onPickQuery: (q: string) => void
}) {
  return (
    <div style={{
      height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center',
      padding: 40,
    }}>
      <div style={{ maxWidth: 560, textAlign: 'center' }}>
        <div style={{
          fontFamily: 'var(--serif)', fontSize: 56, lineHeight: 1, marginBottom: 4,
          color: 'var(--ink)', letterSpacing: '-0.03em',
        }}>
          <span style={{ fontStyle: 'italic' }}>Veritas</span>
          <span style={{ color: 'var(--accent)' }}>Med</span>
        </div>
        <div className="vm-eyebrow" style={{ marginBottom: 24 }}>Evidence-grounded literature Q&amp;A</div>

        <p style={{
          fontFamily: 'var(--serif)', fontSize: 19, lineHeight: 1.5,
          color: 'var(--ink-soft)', maxWidth: 480, margin: '0 auto 36px',
          letterSpacing: '-0.005em',
        }}>
          Ask a literature question, then follow up. Inspect retrieved passages,
          follow citations to their sources, and review the model’s evidence check.
          {' '}{isConversationDemo ? 'This demo searches 15 original abstract passages from three papers: GRADE hypoglycemia, a vegan diet trial and an exercise trial. This small collection cannot answer arbitrary medical questions.' : isMedicalDemo ? 'This demo searches the original GRADE hypoglycemia trial abstract (Seaquist et al., 2024; CC0). It is a single-paper demonstration, not a literature review.' : 'The bundled examples use labelled summaries, not original article text.'}
        </p>

        <div className="vm-eyebrow" style={{ marginBottom: 12 }}>Try a query</div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 6, textAlign: 'left' }}>
          {suggestedQueries.slice(0, 4).map((q, i) => (
            <button
              key={i}
              onClick={() => onPickQuery(q)}
              style={{
                display: 'flex', alignItems: 'center', gap: 12,
                padding: '12px 14px',
                background: 'var(--panel)', border: '1px solid var(--rule)',
                borderRadius: 8,
                color: 'var(--ink-soft)',
                fontSize: 14, fontFamily: 'var(--serif)',
                lineHeight: 1.4, letterSpacing: '-0.005em',
                transition: 'all 120ms', textAlign: 'left',
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.borderColor = 'var(--accent)'
                e.currentTarget.style.color = 'var(--ink)'
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.borderColor = 'var(--rule)'
                e.currentTarget.style.color = 'var(--ink-soft)'
              }}
            >
              <span className="vm-mono" style={{ fontSize: 10, color: 'var(--faint)', width: 16 }}>
                0{i + 1}
              </span>
              <span style={{ flex: 1 }}>{q}</span>
              <IconChevRight size={14} sw={2} style={{ color: 'var(--faint)' }} />
            </button>
          ))}
        </div>
      </div>
    </div>
  )
}
