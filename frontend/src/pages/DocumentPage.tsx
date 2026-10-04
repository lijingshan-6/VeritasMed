import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { ArrowLeft, ExternalLink, Zap } from 'lucide-react'
import { fetchDocument } from '../api/client'
import { useStore } from '../store'
import type { DocumentResponse } from '../types'

export function DocumentPage() {
  const { citation } = useParams<{ citation: string }>()
  const navigate = useNavigate()
  const { setQuery } = useStore()
  const [doc, setDoc] = useState<DocumentResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!citation) return
    setLoading(true)
    fetchDocument(decodeURIComponent(citation))
      .then(setDoc)
      .catch((e: Error) => setError(e.message))
      .finally(() => setLoading(false))
  }, [citation])

  if (loading) {
    return (
      <div className="vm-document-status" role="status">
        Loading source passages…
      </div>
    )
  }

  if (error || !doc) {
    return (
      <div className="vm-document-status" role="alert">
        <p>Document not found: {citation}</p>
        <button
          onClick={() => navigate(-1)}
          className="vm-document-link"
        >
          ← Back
        </button>
      </div>
    )
  }

  return (
    <section className="vm-document" aria-label="Source document">
      <div className="vm-document-body">
      {/* Header */}
      <nav className="vm-document-nav" aria-label="Document navigation">
        <button
          onClick={() => navigate(-1)}
          className="vm-document-link"
        >
          <ArrowLeft size={15} />
          Back
        </button>
        {doc.external_url && (
          <a
            href={doc.external_url}
            target="_blank"
            rel="noopener noreferrer"
            className="vm-document-link"
          >
            <ExternalLink size={14} />
            Open in {doc.source === 'pubmed' ? 'PubMed' : 'PMC'}
          </a>
        )}
      </nav>

      {/* Document title + meta */}
      <header className="vm-document-heading">
        <div className="vm-document-meta">
          <span className="vm-document-citation">
            {doc.citation}
          </span>
          <span>{doc.total_chunks} {doc.total_chunks === 1 ? 'passage' : 'passages'}</span>
        </div>
        <h1>{doc.title}</h1>
      </header>

      {/* Chunks */}
      <div className="vm-document-passages">
        {doc.chunks.map((chunk, i) => (
          <article
            key={chunk.chunk_id}
            id={`docchunk-${chunk.chunk_idx}`}
            className="vm-document-passage"
          >
            <div className="vm-eyebrow">
              <span>
                Passage {i + 1} / {doc.total_chunks}
                {chunk.section && ` · ${chunk.section}`}
              </span>
            </div>
            <p>{chunk.text}</p>
          </article>
        ))}
      </div>

      {/* Quick-ask button */}
      <footer className="vm-document-footer">
        <button
          onClick={() => {
            setQuery(`Based on ${doc.citation}: ${doc.title} — `)
            navigate('/')
          }}
          className="vm-document-ask"
        >
          <Zap size={14} />
          Ask a question based on this document
        </button>
      </footer>
      </div>
    </section>
  )
}
