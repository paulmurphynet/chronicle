import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../lib/api'

export function Investigations() {
  const [list, setList] = useState<Array<{ investigation_uid: string; title: string; description?: string; current_tier: string }>>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    api
      .listInvestigations()
      .then((r) => setList(r.investigations))
      .catch((e) => setError(e instanceof Error ? e.message : String(e)))
      .finally(() => setLoading(false))
  }, [])

  if (loading) return <p>Loading investigations…</p>
  if (error) return <p className="error">Failed to load: {error}</p>

  return (
    <div className="page-investigations">
      <h2>Investigations</h2>
      {list.length === 0 ? (
        <p className="muted">No investigations yet. Create one from the API or use <Link to="/">Try sample</Link> on the home page.</p>
      ) : (
        <ul className="inv-list">
          {list.map((inv) => (
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
