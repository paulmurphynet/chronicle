import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../lib/api'

export function Home() {
  const navigate = useNavigate()
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function trySample() {
    setLoading(true)
    setError(null)
    try {
      const { investigation_uid } = await api.createInvestigation({
        title: 'Try sample: revenue claim',
        description: 'Created by Try sample. One evidence, one claim, one support link.',
      })
      await api.addEvidence(
        investigation_uid,
        'The company reported revenue of $1.2M in Q1 2024. Growth was 8% year-over-year.',
        'sample.txt'
      )
      const { claim_uid } = await api.addClaim(investigation_uid, 'Revenue was $1.2M in Q1 2024.')
      const { evidence } = await api.listEvidence(investigation_uid)
      const ev = evidence[0]
      if (ev) {
        const { spans } = await api.listSpans(ev.evidence_uid)
        if (spans[0]) {
          await api.linkSupport(investigation_uid, spans[0].span_uid, claim_uid, 'Evidence states revenue figure.')
        }
      }
      navigate(`/investigations/${investigation_uid}`, { state: { fromTrySample: true } })
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e))
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="page-home">
      <h2>Welcome</h2>
      <p>
        This is the <strong>Reference UI</strong> for Chronicle: an API-only client for investigations, evidence, claims, links, defensibility, and tensions.
      </p>
      <p>
        <strong>Try sample</strong> creates a minimal investigation (one evidence, one claim, one support link) and opens it so you can see defensibility and export.
      </p>
      <div className="actions">
        <button type="button" onClick={trySample} disabled={loading}>
          {loading ? 'Creating sample…' : 'Try sample'}
        </button>
      </div>
      {error && <p className="error">{error}</p>}
      <p className="muted">
        Ensure the API is running: <code>pip install -e ".[api]"</code>, set <code>CHRONICLE_PROJECT_PATH</code>, then <code>uvicorn chronicle.api.app:app --reload</code>. Default: <a href="http://127.0.0.1:8000/docs" target="_blank" rel="noreferrer">http://127.0.0.1:8000/docs</a>.
      </p>
    </div>
  )
}
