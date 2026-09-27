import type { AnswerOut } from '../../types/ws'
import { useStore } from '../../store'
import { CITE_VARS, IconCheck, IconAlert } from './Icons'

export function EvidenceCoverage({ result, onCiteClick, guided }: { result: AnswerOut; onCiteClick: (c: string) => void; guided: boolean }) {
  const setSelectedChunkId = useStore((state) => state.setSelectedChunkId)
  if (!result.evidence_status) return null
  const labels = { complete: 'Evidence covers the question', partial: 'Partially covered', insufficient: 'Insufficient evidence' }
  const componentLabels = { supported: 'Source identified', partial: 'Partial support', missing: 'Evidence gap' }
  return (
    <section aria-label="Evidence coverage" style={{ margin: '0 0 26px', padding: '16px 18px', border: '1px solid var(--rule)', borderRadius: 8, background: 'var(--panel-2)' }}>
      <div className="vm-eyebrow" style={{ color: result.evidence_status === 'complete' ? 'var(--verified)' : 'var(--warn)' }}>
        {guided ? 'Illustrative coverage · ' : ''}{labels[result.evidence_status]}
      </div>
      <p style={{ margin: '8px 0', fontSize: 12, lineHeight: 1.6, color: 'var(--muted)' }}>
        Coverage reflects the retrieved passages and model assessment; it is not a correctness score.
      </p>
      {result.evidence_gap && <p style={{ fontSize: 13, lineHeight: 1.6, color: 'var(--ink-soft)' }}>{result.evidence_gap}</p>}
      {result.answer_components?.map((component) => (
        <details key={component.id} style={{ borderTop: '1px solid var(--rule)', padding: '10px 0 4px' }}>
          <summary style={{ cursor: 'pointer', fontSize: 13, lineHeight: 1.6, color: 'var(--ink-soft)' }}>
            {component.requirement}
            <span style={{ display: 'block', fontSize: 10, marginLeft: 16, color: 'var(--muted)' }}>{componentLabels[component.status]}</span>
          </summary>
          {component.gap && <p style={{ fontSize: 12, lineHeight: 1.6 }}>{component.gap}</p>}
          {component.evidence.map((span, i) => (
            <blockquote key={`${span.chunk_id}-${i}`} style={{ margin: '12px 0 8px', paddingLeft: 12, borderLeft: '2px solid var(--accent)', fontSize: 12, lineHeight: 1.65, color: 'var(--ink-soft)' }}>
              {span.quote}
              <button onClick={() => { onCiteClick(span.citation); setSelectedChunkId(span.chunk_id) }}
                style={{ display: 'block', padding: '8px 0', background: 'transparent', color: 'var(--accent)', fontSize: 11 }}>
                View source · {span.citation}
              </button>
            </blockquote>
          ))}
        </details>
      ))}
    </section>
  )
}

export function VerificationMark({ result, guided }: { result: AnswerOut; guided: boolean }) {
  const ok = result.faithful
  return (
    <div style={{
      marginTop: 36, padding: '18px 22px',
      border: `1px solid ${ok ? 'var(--verified)' : 'var(--warn)'}`,
      borderRadius: 4,
      background: ok ? 'var(--verified-soft)' : 'var(--warn-soft)',
      position: 'relative',
    }}>
      <div style={{
        position: 'absolute', top: -1, left: -1,
        width: 28, height: 28,
        background: ok ? 'var(--verified)' : 'var(--warn)',
        color: 'var(--panel)',
        display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
        borderRadius: '3px 0 8px 0',
      }}>
        {ok ? <IconCheck size={14} sw={2.6} /> : <IconAlert size={14} sw={2.4} />}
      </div>

      <div style={{ marginLeft: 36 }}>
        <div style={{
          fontFamily: 'var(--serif)', fontStyle: 'italic',
          fontSize: 18, lineHeight: 1.2,
          color: ok ? 'var(--verified)' : 'var(--warn)',
        }}>
          {guided ? 'Illustrative evidence-check result' : ok ? 'Model evidence check passed' : 'Evidence check did not pass'}
        </div>

        {!ok && result.faithfulness_issues && (
          <p style={{ margin: '6px 0 0 0', fontSize: 13, color: 'var(--ink-soft)', lineHeight: 1.5 }}>
            {result.faithfulness_issues}
          </p>
        )}

        <div style={{ marginTop: 12, display: 'flex', flexWrap: 'wrap', gap: '4px 22px', fontSize: 11, color: 'var(--muted)' }}>
          <Metric label="rewrites"      value={String(result.iterations)} />
          <Metric label="regenerations" value={String(result.regen_count)} />
          <Metric label="elapsed"       value={guided ? "illustrative" : `${(result.latency_ms / 1000).toFixed(2)}s`} />
          <Metric label="verifier"      value={guided ? "preset example" : "configured LLM"} />
        </div>
      </div>
    </div>
  )
}

function Metric({ label, value }: { label: string; value: string }) {
  if (!value) return null
  return (
    <div style={{ display: 'inline-flex', flexDirection: 'column', gap: 0 }}>
      <span className="vm-eyebrow" style={{ fontSize: 9, letterSpacing: '0.16em', color: 'var(--faint)' }}>
        {label}
      </span>
      <span className="vm-mono" style={{ fontSize: 12, color: 'var(--ink-soft)', fontWeight: 600 }}>
        {value}
      </span>
    </div>
  )
}

export function SourcesStrip({
  result,
  onCiteClick,
}: {
  result: AnswerOut
  onCiteClick: (c: string) => void
}) {
  return (
    <div style={{ marginTop: 32 }}>
      <div className="vm-eyebrow" style={{ marginBottom: 10 }}>
        Sources cited · {result.citations.length}
      </div>
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
        {result.citations.map((c: string, i: number) => {
          const chunk = result.chunks.find((ch: AnswerOut['chunks'][0]) => ch.citation === c)
          const colorVar = CITE_VARS[i % CITE_VARS.length]
          const ext = chunk as typeof chunk & { journal?: string; year?: number }
          return (
            <button
              key={c}
              onClick={() => onCiteClick(c)}
              style={{
                display: 'inline-flex', alignItems: 'center', gap: 8,
                padding: '6px 11px 6px 8px',
                border: '1px solid var(--rule)',
                borderRadius: 6,
                background: 'var(--panel)',
                color: 'var(--ink-soft)',
                fontSize: 11, textAlign: 'left',
                maxWidth: 320, transition: 'all 120ms',
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.background = 'var(--panel-2)'
                e.currentTarget.style.borderColor = `var(${colorVar})`
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.background = 'var(--panel)'
                e.currentTarget.style.borderColor = 'var(--rule)'
              }}
            >
              <span style={{
                fontFamily: 'var(--serif)', fontStyle: 'italic',
                color: `var(${colorVar})`, fontSize: 13, lineHeight: 1,
                width: 16, textAlign: 'center', fontWeight: 500,
              }}>
                {i + 1}
              </span>
              <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                <span className="vm-mono" style={{ color: 'var(--faint)', fontSize: 10 }}>{c}</span>
                {ext && (ext.journal || ext.year) && (
                  <span style={{ marginLeft: 6, color: 'var(--ink-soft)' }}>
                    {ext.journal}{ext.year ? ` · ${ext.year}` : ''}
                  </span>
                )}
              </span>
            </button>
          )
        })}
      </div>
    </div>
  )
}
