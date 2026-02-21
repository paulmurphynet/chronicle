import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../lib/api'

export function Investigations() {
  const [list, setList] = useState<Array<{ investigation_uid: string; title: string; description?: string; current_tier: string }>>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [query, setQuery] = useState('')

  const load = useCallback(() => {
    setLoading(true)
    setError(null)
    api
      .listInvestigations()
      .then((r) => setList(r.investigations))
      .catch((e) => setError(e instanceof Error ? e.message : String(e)))
      .finally(() => setLoading(false))
  }, [])

  useEffect(() => {
    load()
  }, [load])

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase()
    if (!q) return list
    return list.filter((inv) => {
      const haystack = `${inv.title ?? ''} ${inv.description ?? ''}`.toLowerCase()
      return haystack.includes(q)
    })
  }, [list, query])

  if (loading) return <p>Loading investigations…</p>
  if (error) {
    return (
      <div className="page-investigations">
        <h2>Investigations</h2>
        <p className="error">Failed to load investigations: {error}</p>
        <div className="button-row">
          <button type="button" onClick={load}>Retry</button>
          <Link to="/">Go to home</Link>
        </div>
      </div>
    )
  }

  return (
    <div className="page-investigations">
      <h2>Investigations</h2>
      <p className="meta">Total: <strong>{list.length}</strong></p>
      <input
        type="text"
        placeholder="Filter by title or description…"
        value={query}
        onChange={(e) => setQuery(e.target.value)}
      />
      {list.length === 0 ? (
        <div className="empty-state">
          <p className="muted">No investigations yet.</p>
          <p className="muted">Create one from the API or use <Link to="/">Try sample</Link> on the home page.</p>
        </div>
      ) : filtered.length === 0 ? (
        <div className="empty-state">
          <p className="muted">No investigations match your filter.</p>
          <button type="button" onClick={() => setQuery('')}>Clear filter</button>
        </div>
      ) : (
        <ul className="inv-list">
          {filtered.map((inv) => (
            <li key={inv.investigation_uid}>
              <Link to={`/investigations/${inv.investigation_uid}`}>
                <strong>{inv.title || inv.investigation_uid}</strong>
                <span className="tier">{inv.current_tier}</span>
              </Link>
              {inv.description && <p className="inv-desc">{inv.description}</p>}
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
