import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { api } from '../lib/api'
import { getWebAppTestCase, seedWebAppTestCase, WEB_APP_TEST_CASES } from '../lib/testCases'

export function Home() {
  const navigate = useNavigate()
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [healthChecking, setHealthChecking] = useState(false)
  const [healthStatus, setHealthStatus] = useState<'unknown' | 'ok' | 'error'>('unknown')
  const [healthMessage, setHealthMessage] = useState<string>('')
  const [seedLoading, setSeedLoading] = useState(false)
  const [selectedCaseId, setSelectedCaseId] = useState<string>(WEB_APP_TEST_CASES[0]?.id ?? '')

  const selectedCase = getWebAppTestCase(selectedCaseId)

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

  async function checkApi() {
    setHealthChecking(true)
    setHealthMessage('')
    try {
      const result = await api.health()
      setHealthStatus('ok')
      setHealthMessage(`API healthy: ${result.status}`)
    } catch (e) {
      setHealthStatus('error')
      setHealthMessage(e instanceof Error ? e.message : String(e))
    } finally {
      setHealthChecking(false)
    }
  }

  async function createRealisticCase() {
    if (!selectedCaseId) return
    setSeedLoading(true)
    setError(null)
    try {
      const seeded = await seedWebAppTestCase(selectedCaseId)
      navigate(`/investigations/${seeded.investigation_uid}`, { state: { fromSeedCase: seeded.case_name } })
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e))
    } finally {
      setSeedLoading(false)
    }
  }

  return (
    <div className="page-home">
      <h2>Welcome</h2>
      <p>
        This is the <strong>Reference UI</strong> for Chronicle: an API-only client for investigations, evidence, claims, links, defensibility, and tensions.
      </p>
      <div className="home-card home-card-flow">
        <h3>Recommended first run</h3>
        <ol className="home-steps">
          <li>Check API connectivity.</li>
          <li>Create a sample investigation.</li>
          <li>Open Defensibility and Export tabs to inspect outputs.</li>
        </ol>
        <div className="actions">
          <button type="button" onClick={checkApi} disabled={healthChecking}>
            {healthChecking ? 'Checking API…' : 'Check API'}
          </button>
          <button type="button" onClick={trySample} disabled={loading}>
            {loading ? 'Creating sample…' : 'Try sample'}
          </button>
          <Link to="/investigations" className="button-link">Open investigations</Link>
        </div>
        {healthStatus === 'ok' && <p className="ok">{healthMessage}</p>}
        {healthStatus === 'error' && <p className="error">API check failed: {healthMessage}</p>}
      </div>
      {error && <p className="error">{error}</p>}
      <div className="home-card">
        <h3>Realistic fictional test cases</h3>
        <p className="muted">
          Seed complete synthetic investigations for QA, demos, and training. All entities in these cases are fictional.
        </p>
        <label>
          Scenario
          <select value={selectedCaseId} onChange={(e) => setSelectedCaseId(e.target.value)}>
            {WEB_APP_TEST_CASES.map((scenario) => (
              <option key={scenario.id} value={scenario.id}>{scenario.name}</option>
            ))}
          </select>
        </label>
        {selectedCase && (
          <p className="muted">
            {selectedCase.blurb} Includes {selectedCase.evidence.length} evidence items, {selectedCase.claims.length} claims, and {selectedCase.tensions.length} tensions. Target tier: {selectedCase.target_tier}.
          </p>
        )}
        <div className="actions">
          <button type="button" onClick={createRealisticCase} disabled={seedLoading || !selectedCaseId}>
            {seedLoading ? 'Creating scenario…' : 'Create realistic case'}
          </button>
        </div>
      </div>
      <div className="home-card">
        <h3>Next after sample</h3>
        <p className="muted">Use the Learn page for vertical workflows and checklist-style guides.</p>
        <Link to="/learn">Go to Learn</Link>
      </div>
      <p className="muted">
        Ensure the API is running: <code>pip install -e ".[api]"</code>, set <code>CHRONICLE_PROJECT_PATH</code>, then <code>uvicorn chronicle.api.app:app --reload</code>. Default: <a href="http://127.0.0.1:8000/docs" target="_blank" rel="noreferrer">http://127.0.0.1:8000/docs</a>.
      </p>
    </div>
  )
}
