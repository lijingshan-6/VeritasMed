import type { AuditRecord } from '../../api/audit'
import { category, LinkedText } from './Presentation'

type Props = { record: AuditRecord; selected: string; onSelect: (id: string) => void }

export function SourceList({ record, selected, onSelect }: Props) {
  const audit = record.audit
  const active = audit.claims.find(c => c.id === selected)
  return <aside className="audit-sources-column">
          <div className="audit-section-title"><h2>Provided sources</h2><span className="audit-muted">{record.input.sources.length} {record.input.sources.length === 1 ? 'text' : 'texts'}</span></div>
          <p className="audit-muted">Highlights follow claim {active ? audit.claims.indexOf(active) + 1 : '—'}. Click a marked source passage to select its claim. A reference proves text location, not semantic correctness.</p>
          {record.input.sources.map(source => {
            const refs = audit.claims.flatMap(c => c.evidence.filter(r => r.source_id === source.id).map(r => ({ ...r, claimId: c.id, category: category(c) })))
            const origin = record.provenance.handoff?.source_map.find(s => s.id === source.id)
            return <article className="audit-source" id={`audit-source-${source.id}`} key={source.id}>
              <header><span className="vm-eyebrow">{source.id} / supplied text</span><h3>{source.title}</h3></header>
              {origin && <p className="audit-muted">Original source passage: {origin.chunk_id}{origin.section ? ` · ${origin.section}` : ''}{/^https?:\/\//i.test(origin.external_url) && <> · <a href={origin.external_url} target="_blank" rel="noreferrer">Open source ↗</a></>}</p>}
              <div className="audit-source-text"><LinkedText text={source.text} spans={refs} selected={selected} onSelect={onSelect} /></div>
              <details><summary>Source fingerprint</summary><code className="audit-hash">SHA-256 {audit.source_hashes[source.id]}</code><p>Positions use Unicode code points, with an exclusive end.</p></details>
            </article>
          })}
        </aside>
}
