import { useCallback, useEffect, useState } from 'react'
import { useParams, useLocation } from 'react-router-dom'
import { api, downloadBlob } from '../lib/api'
import type {
  Claim,
  EvidenceItem,
  Investigation,
  PolicyCompatibilityResult,
  Tension,
  TensionSuggestion,
} from '../types'

type Tab = 'overview' | 'evidence' | 'claims' | 'links' | 'defensibility' | 'tensions' | 'suggestions' | 'export' | 'writing' | 'reading' | 'publication' | 'policy' | 'graph'

export function InvestigationDetail() {
  const { id } = useParams<{ id: string }>()
  const location = useLocation()
  const navState = (location.state as { fromTrySample?: boolean; fromSeedCase?: string } | undefined) ?? {}
  const fromTrySample = navState.fromTrySample ?? false
  const fromSeedCase = navState.fromSeedCase ?? null

  const [inv, setInv] = useState<Investigation | null>(null)
  const [evidence, setEvidence] = useState<EvidenceItem[]>([])
  const [claims, setClaims] = useState<Claim[]>([])
  const [tensions, setTensions] = useState<Tension[]>([])
  const [suggestions, setSuggestions] = useState<TensionSuggestion[]>([])
  const [tab, setTab] = useState<Tab>('overview')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [defensibility, setDefensibility] = useState<Record<string, Record<string, unknown>>>({})
  const [spansByEvidence, setSpansByEvidence] = useState<Record<string, Array<{ span_uid: string }>>>({})

  const invId = id!

  const load = useCallback(() => {
    if (!invId) return
    setLoading(true)
    setError(null)
    Promise.all([
      api.getInvestigation(invId),
      api.listEvidence(invId),
      api.listClaims(invId),
      api.listTensions(invId),
      api.listTensionSuggestions(invId),
    ])
      .then(([i, e, c, t, s]) => {
        setInv(i)
        setEvidence(e.evidence)
        setClaims(c.claims)
        setTensions(t.tensions)
        setSuggestions(s.tension_suggestions)
        return e.evidence
      })
      .then((evList) => {
        return Promise.all(evList.map((ev) => api.listSpans(ev.evidence_uid).then((r) => ({ uid: ev.evidence_uid, spans: r.spans }))))
      })
      .then((results) => {
        const map: Record<string, Array<{ span_uid: string }>> = {}
        results.forEach(({ uid, spans }) => { map[uid] = spans })
        setSpansByEvidence(map)
      })
      .catch((e) => setError(e instanceof Error ? e.message : String(e)))
      .finally(() => setLoading(false))
  }, [invId])

  useEffect(() => { load() }, [load])

  useEffect(() => {
    if (tab !== 'defensibility' || claims.length === 0) return
    claims.forEach((c) => {
      api.getDefensibility(c.claim_uid).then((d) => setDefensibility((prev) => ({ ...prev, [c.claim_uid]: d }))).catch(() => {})
    })
  }, [tab, claims])

  const [newEvidence, setNewEvidence] = useState('')
  const [newClaim, setNewClaim] = useState('')
  const [tierReason, setTierReason] = useState('')
  const [linkSpan, setLinkSpan] = useState('')
  const [linkClaim, setLinkClaim] = useState('')
  const [linkKind, setLinkKind] = useState<'support' | 'challenge'>('support')
  const [actionLoading, setActionLoading] = useState(false)
  const [actionError, setActionError] = useState<string | null>(null)
  const [writingText, setWritingText] = useState('')
  const [readingEvidenceUid, setReadingEvidenceUid] = useState('')
  const [readingContent, setReadingContent] = useState('')
  const [readingLinkClaim, setReadingLinkClaim] = useState('')
  const [readingLinkKind, setReadingLinkKind] = useState<'support' | 'challenge'>('support')
  const [graphData, setGraphData] = useState<{ nodes: Array<{ id: string; type: string; label: string }>; edges: Array<{ from: string; to: string; link_type: string }> } | null>(null)
  const [policyViewingId, setPolicyViewingId] = useState('policy_legal')
  const [policyBuiltUnderOverride, setPolicyBuiltUnderOverride] = useState('')
  const [policyCompat, setPolicyCompat] = useState<PolicyCompatibilityResult | null>(null)
  const [policyCompatLoading, setPolicyCompatLoading] = useState(false)

  const doSetTier = (tier: string) => {
    setActionLoading(true)
    setActionError(null)
    api.setTier(invId, { tier, reason: tierReason || undefined })
      .then(() => { setTierReason(''); load() })
      .catch((e) => setActionError(e instanceof Error ? e.message : String(e)))
      .finally(() => setActionLoading(false))
  }

  const doAddEvidence = () => {
    if (!newEvidence.trim()) return
    setActionLoading(true)
    setActionError(null)
    api.addEvidence(invId, newEvidence.trim())
      .then(() => { setNewEvidence(''); load() })
      .catch((e) => setActionError(e instanceof Error ? e.message : String(e)))
      .finally(() => setActionLoading(false))
  }

  const doAddClaim = () => {
    if (!newClaim.trim()) return
    setActionLoading(true)
    setActionError(null)
    api.addClaim(invId, newClaim.trim())
      .then(() => { setNewClaim(''); load() })
      .catch((e) => setActionError(e instanceof Error ? e.message : String(e)))
      .finally(() => setActionLoading(false))
  }

  const doLink = () => {
    if (!linkSpan || !linkClaim) return
    setActionLoading(true)
    setActionError(null)
    const fn = linkKind === 'support' ? api.linkSupport : api.linkChallenge
    fn(invId, linkSpan, linkClaim)
      .then(() => { setLinkSpan(''); setLinkClaim(''); load() })
      .catch((e) => setActionError(e instanceof Error ? e.message : String(e)))
      .finally(() => setActionLoading(false))
  }

  const doConfirmSuggestion = (s: TensionSuggestion) => {
    setActionLoading(true)
    setActionError(null)
    api.declareTension(invId, s.claim_a_uid, s.claim_b_uid, s.suggested_tension_kind)
      .then(() => load())
      .catch((e) => setActionError(e instanceof Error ? e.message : String(e)))
      .finally(() => setActionLoading(false))
  }

  const doDismissSuggestion = (suggestionUid: string) => {
    setActionLoading(true)
    setActionError(null)
    api.dismissTensionSuggestion(invId, suggestionUid)
      .then(() => load())
      .catch((e) => setActionError(e instanceof Error ? e.message : String(e)))
      .finally(() => setActionLoading(false))
  }

  const doExportChronicle = () => {
    api.exportChronicle(invId).then((blob) => downloadBlob(blob as Blob, `${invId}.chronicle`)).catch((e) => setActionError(e instanceof Error ? e.message : String(e)))
  }

  const doExportSubmission = () => {
    api.exportSubmissionPackage(invId).then((blob) => downloadBlob(blob as Blob, `${invId}-submission.zip`)).catch((e) => setActionError(e instanceof Error ? e.message : String(e)))
  }

  const doPolicyPreflight = () => {
    setPolicyCompatLoading(true)
    setActionError(null)
    api.getPolicyCompatibility(invId, {
      viewing_profile_id: policyViewingId || undefined,
      built_under_profile_id: policyBuiltUnderOverride.trim() || undefined,
    })
      .then((result) => setPolicyCompat(result))
      .catch((e) => setActionError(e instanceof Error ? e.message : String(e)))
      .finally(() => setPolicyCompatLoading(false))
  }

  const doAddWritingAsEvidence = () => {
    if (!writingText.trim()) return
    setActionLoading(true)
    setActionError(null)
    api.addEvidence(invId, writingText.trim(), 'writing.md')
      .then(() => { setWritingText(''); load() })
      .catch((e) => setActionError(e instanceof Error ? e.message : String(e)))
      .finally(() => setActionLoading(false))
  }

  const doProposeClaimFromWriting = () => {
    const text = writingText.trim() || (document.getSelection()?.toString() ?? '').trim()
    if (!text) return
    setActionLoading(true)
    setActionError(null)
    api.addClaim(invId, text)
      .then(() => load())
      .catch((e) => setActionError(e instanceof Error ? e.message : String(e)))
      .finally(() => setActionLoading(false))
  }

  const loadReadingContent = (evidenceUid: string) => {
    setReadingEvidenceUid(evidenceUid)
    setReadingContent('')
    api.getEvidenceContent(evidenceUid).then(setReadingContent).catch(() => setReadingContent('(failed to load)'))
  }

  const doCreateSpanAndLink = (start: number, end: number, quote: string) => {
    if (!readingEvidenceUid || !readingLinkClaim || start >= end) return
    setActionLoading(true)
    setActionError(null)
    api.createSpan(invId, { evidence_uid: readingEvidenceUid, start_char: start, end_char: end, quote })
      .then((r) => {
        const fn = readingLinkKind === 'support' ? api.linkSupport : api.linkChallenge
        return fn(invId, r.span_uid, readingLinkClaim)
      })
      .then(() => { setReadingLinkClaim(''); load() })
      .catch((e) => setActionError(e instanceof Error ? e.message : String(e)))
      .finally(() => setActionLoading(false))
  }

  useEffect(() => {
    if (tab === 'graph' && invId) {
      api.getGraph(invId).then(setGraphData).catch(() => setGraphData(null))
    } else {
      setGraphData(null)
    }
  }, [tab, invId])

  const allSpans = evidence.flatMap((ev) => (spansByEvidence[ev.evidence_uid] ?? []).map((s) => ({ ...s, evidence_uid: ev.evidence_uid, label: ev.original_filename })))
  const openTensionCount = tensions.filter((t) => t.status === 'OPEN' || t.status === 'DISPUTED').length
  const publicationReady = claims.length > 0 && openTensionCount === 0 && inv?.current_tier !== 'spark'

  if (loading && !inv) return <p>Loading…</p>
  if (error && !inv) return <p className="error">{error}</p>
  if (!inv) return <p>Investigation not found.</p>

  const tabs: Tab[] = ['overview', 'evidence', 'claims', 'links', 'defensibility', 'tensions', 'suggestions', 'export', 'writing', 'reading', 'publication', 'policy', 'graph']

  return (
    <div className="page-investigation-detail">
      <h2>{inv.title || inv.investigation_uid}</h2>
      {fromTrySample && (
        <div className="banner">
          <p><strong>Sample created.</strong> Run this quick tour to understand the workflow:</p>
          <ol>
            <li>Open <strong>Evidence</strong> and add one more source.</li>
            <li>Open <strong>Claims</strong> and add or refine a claim.</li>
            <li>Open <strong>Defensibility</strong> to inspect score output.</li>
            <li>Open <strong>Export</strong> to download `.chronicle` and submission package.</li>
          </ol>
          <div className="button-row">
            <button type="button" onClick={() => setTab('evidence')}>Go to Evidence</button>
            <button type="button" onClick={() => setTab('defensibility')}>Go to Defensibility</button>
            <button type="button" onClick={() => setTab('export')}>Go to Export</button>
          </div>
        </div>
      )}
      {fromSeedCase && (
        <div className="banner">
          <p>
            <strong>Scenario seeded.</strong> Loaded <strong>{fromSeedCase}</strong> (fictional training case).
          </p>
          <ol>
            <li>Review support/challenge links in <strong>Links</strong>.</li>
            <li>Check contradictions in <strong>Tensions</strong> and <strong>Suggestions</strong>.</li>
            <li>Inspect score deltas in <strong>Defensibility</strong>.</li>
            <li>Run policy readiness checks in <strong>Policy</strong>.</li>
          </ol>
          <div className="button-row">
            <button type="button" onClick={() => setTab('links')}>Go to Links</button>
            <button type="button" onClick={() => setTab('tensions')}>Go to Tensions</button>
            <button type="button" onClick={() => setTab('defensibility')}>Go to Defensibility</button>
          </div>
        </div>
      )}
      {inv.description && <p className="muted">{inv.description}</p>}
      <p className="meta">Tier: <strong>{inv.current_tier}</strong> · Created {inv.created_at}</p>
      <div className="summary-grid">
        <div><span>Evidence</span><strong>{evidence.length}</strong></div>
        <div><span>Claims</span><strong>{claims.length}</strong></div>
        <div><span>Tensions</span><strong>{tensions.length}</strong></div>
        <div><span>Open/Disputed</span><strong>{openTensionCount}</strong></div>
      </div>

      <nav className="tabs">
        {tabs.map((t) => (
          <button key={t} type="button" className={tab === t ? 'active' : ''} onClick={() => setTab(t)}>{t}</button>
        ))}
      </nav>

      {actionError && <p className="error">{actionError}</p>}

      {tab === 'overview' && (
        <section>
          <h3>Tier</h3>
          <p>Current: <strong>{inv.current_tier}</strong>. Allowed next: {inv.current_tier === 'spark' ? 'forge' : inv.current_tier === 'forge' ? 'vault' : 'none'}.</p>
          <input type="text" placeholder="Reason (optional)" value={tierReason} onChange={(e) => setTierReason(e.target.value)} />
          <div className="button-row">
            {inv.current_tier !== 'forge' && inv.current_tier !== 'vault' && <button type="button" onClick={() => doSetTier('forge')} disabled={actionLoading}>Advance to Forge</button>}
            {inv.current_tier === 'forge' && <button type="button" onClick={() => doSetTier('vault')} disabled={actionLoading}>Advance to Vault</button>}
          </div>
          <h3>Tier history</h3>
          <TierHistory invId={invId} />
        </section>
      )}

      {tab === 'evidence' && (
        <section>
          <h3>Evidence ({evidence.length})</h3>
          <textarea placeholder="Paste or type content…" value={newEvidence} onChange={(e) => setNewEvidence(e.target.value)} rows={3} />
          <button type="button" onClick={doAddEvidence} disabled={actionLoading || !newEvidence.trim()}>Add evidence</button>
          {evidence.length === 0 ? (
            <p className="muted">No evidence yet. Add at least one source to unlock useful defensibility output.</p>
          ) : (
            <ul className="list">
              {evidence.map((ev) => (
                <li key={ev.evidence_uid}><strong>{ev.original_filename}</strong> · {ev.media_type} · {(ev.file_size_bytes / 1024).toFixed(1)} KB · {ev.created_at}</li>
              ))}
            </ul>
          )}
        </section>
      )}

      {tab === 'claims' && (
        <section>
          <h3>Claims ({claims.length})</h3>
          <textarea placeholder="Claim text…" value={newClaim} onChange={(e) => setNewClaim(e.target.value)} rows={2} />
          <button type="button" onClick={doAddClaim} disabled={actionLoading || !newClaim.trim()}>Add claim</button>
          {claims.length === 0 ? (
            <p className="muted">No claims yet. Add at least one claim, then link evidence in the Links tab.</p>
          ) : (
            <ul className="list">
              {claims.map((c) => (
                <li key={c.claim_uid}><strong>{c.claim_text}</strong> · {c.current_status} · {c.claim_type ?? '—'}</li>
              ))}
            </ul>
          )}
        </section>
      )}

      {tab === 'links' && (
        <section>
          <h3>Link evidence to claim (support or challenge)</h3>
          <div className="control-row">
            <label>Span <select value={linkSpan} onChange={(e) => setLinkSpan(e.target.value)}>
              <option value="">—</option>
              {allSpans.map((s) => (
                <option key={s.span_uid} value={s.span_uid}>{s.label} (span)</option>
              ))}
            </select></label>
            <label>Claim <select value={linkClaim} onChange={(e) => setLinkClaim(e.target.value)}>
              <option value="">—</option>
              {claims.map((c) => (
                <option key={c.claim_uid} value={c.claim_uid}>{c.claim_text.slice(0, 60)}…</option>
              ))}
            </select></label>
            <label>Kind <select value={linkKind} onChange={(e) => setLinkKind(e.target.value as 'support' | 'challenge')}>
              <option value="support">Support</option>
              <option value="challenge">Challenge</option>
            </select></label>
            <button type="button" onClick={doLink} disabled={actionLoading || !linkSpan || !linkClaim}>Add link</button>
          </div>
        </section>
      )}

      {tab === 'defensibility' && (
        <section>
          <h3>Defensibility by claim</h3>
          {claims.length === 0 ? <p className="muted">No claims. Add claims and link evidence to see defensibility.</p> : (
            <ul className="list">
              {claims.map((c) => (
                <li key={c.claim_uid}>
                  <strong>{c.claim_text}</strong>
                  {defensibility[c.claim_uid] ? (
                    <pre className="defensibility-json">{JSON.stringify(defensibility[c.claim_uid], null, 2)}</pre>
                  ) : (
                    <span className="muted">Loading…</span>
                  )}
                </li>
              ))}
            </ul>
          )}
        </section>
      )}

      {tab === 'tensions' && (
        <section>
          <h3>Tensions ({tensions.length})</h3>
          {tensions.length === 0 ? (
            <p className="muted">No tensions recorded yet.</p>
          ) : (
            <ul className="list">
              {tensions.map((t) => (
                <li key={t.tension_uid}>{t.claim_a_uid} ↔ {t.claim_b_uid} · {t.tension_kind ?? 'contradiction'} · {t.status}</li>
              ))}
            </ul>
          )}
          <p className="muted">Declare a tension from the Suggestions tab (confirm) or via API with claim_a_uid and claim_b_uid.</p>
        </section>
      )}

      {tab === 'suggestions' && (
        <section>
          <h3>Tension suggestions (Propose–Confirm)</h3>
          {suggestions.length === 0 ? <p className="muted">No pending suggestions. Suggestions are emitted by tools (e.g. contradiction detector).</p> : (
            <ul className="list">
              {suggestions.map((s) => (
                <li key={s.suggestion_uid}>
                  Claim {s.claim_a_uid} ↔ {s.claim_b_uid} · {s.suggested_tension_kind} · confidence {s.confidence.toFixed(2)} · {s.rationale}
                  <div className="button-row">
                    <button type="button" onClick={() => doConfirmSuggestion(s)} disabled={actionLoading}>Confirm (declare tension)</button>
                    <button type="button" onClick={() => doDismissSuggestion(s.suggestion_uid)} disabled={actionLoading}>Dismiss</button>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </section>
      )}

      {tab === 'export' && (
        <section>
          <h3>Export</h3>
          <div className="button-row">
            <button type="button" onClick={doExportChronicle}>Download .chronicle</button>
            <button type="button" onClick={doExportSubmission}>Download submission package (ZIP)</button>
          </div>
          <p className="muted">.chronicle = full investigation for verification. Submission package = .chronicle + reasoning_briefs/ (HTML per claim) + manifest.json.</p>
        </section>
      )}

      {tab === 'writing' && (
        <section>
          <h3>Writing (markdown + claims)</h3>
          <p className="muted">Paste or type markdown; add as evidence and/or propose claims from the text.</p>
          <textarea placeholder="Paste or type markdown…" value={writingText} onChange={(e) => setWritingText(e.target.value)} rows={8} className="writing-area" />
          <div className="button-row">
            <button type="button" onClick={doAddWritingAsEvidence} disabled={actionLoading || !writingText.trim()}>Add as evidence</button>
            <button type="button" onClick={doProposeClaimFromWriting} disabled={actionLoading || !writingText.trim()}>Propose whole as claim</button>
          </div>
          <p className="muted">To propose a selection as a claim: select text above then click &quot;Propose whole as claim&quot; (uses selection if any).</p>
        </section>
      )}

      {tab === 'reading' && (
        <section>
          <h3>Reading (evidence → select → link)</h3>
          <p className="muted">Open evidence content, select text, then link the selection to a claim as support or challenge.</p>
          <div className="control-row">
            <label>Evidence: <select value={readingEvidenceUid} onChange={(e) => loadReadingContent(e.target.value)}>
              <option value="">—</option>
              {evidence.map((ev) => (
                <option key={ev.evidence_uid} value={ev.evidence_uid}>{ev.original_filename}</option>
              ))}
            </select></label>
          </div>
          {readingEvidenceUid && (
            <>
              <div className="control-row">
                <label>Link to claim: <select value={readingLinkClaim} onChange={(e) => setReadingLinkClaim(e.target.value)}>
                  <option value="">—</option>
                  {claims.map((c) => (
                    <option key={c.claim_uid} value={c.claim_uid}>{c.claim_text.slice(0, 50)}…</option>
                  ))}
                </select></label>
                <label>As: <select value={readingLinkKind} onChange={(e) => setReadingLinkKind(e.target.value as 'support' | 'challenge')}>
                  <option value="support">Support</option>
                  <option value="challenge">Challenge</option>
                </select></label>
              </div>
              <div className="reading-content-wrap">
                <pre
                  className="reading-content"
                  onMouseUp={() => {
                    const sel = window.getSelection()
                    if (!sel || sel.rangeCount === 0 || !readingLinkClaim) return
                    const range = sel.getRangeAt(0)
                    const el = range.commonAncestorContainer.nodeType === Node.TEXT_NODE ? range.commonAncestorContainer.parentElement : range.commonAncestorContainer as HTMLElement
                    if (!el?.closest?.('.reading-content')) return
                    const pre = el.closest('.reading-content')
                    if (!pre || !pre.contains(range.startContainer) || !pre.contains(range.endContainer)) return
                    const preRange = document.createRange()
                    preRange.selectNodeContents(pre)
                    preRange.setEnd(range.startContainer, range.startOffset)
                    const startChar = preRange.toString().length
                    preRange.setEnd(range.endContainer, range.endOffset)
                    const endChar = preRange.toString().length
                    const quote = range.toString()
                    if (quote && startChar < endChar) doCreateSpanAndLink(startChar, endChar, quote)
                  }}
                >
                  {readingContent || 'Loading…'}
                </pre>
              </div>
              <p className="muted">Select text in the content above, then release mouse to create a span and link it to the selected claim.</p>
            </>
          )}
        </section>
      )}

      {tab === 'publication' && (
        <section>
          <h3>Publication readiness</h3>
          <p className={`status-chip ${publicationReady ? 'ready' : 'not-ready'}`}>
            {publicationReady ? 'Ready for package export' : 'Not ready yet'}
          </p>
          <ul className="list">
            <li>Claims: <strong>{claims.length}</strong></li>
            <li>Tensions: <strong>{tensions.length}</strong> ({openTensionCount} open/disputed)</li>
            <li>Tier: <strong>{inv.current_tier}</strong></li>
          </ul>
          <p className="muted">Guideline: keep open/disputed tensions at 0 and advance beyond Spark before final release export.</p>
          <div className="button-row">
            <button type="button" onClick={doExportSubmission}>Download submission package</button>
          </div>
        </section>
      )}

      {tab === 'policy' && (
        <section>
          <h3>Policy profiles</h3>
          <p className="muted">
            Example policy profiles for verticals. See{' '}
            <a href="https://github.com/chronicle-app/chronicle/blob/main/docs/policy-profiles/README.md" target="_blank" rel="noreferrer">docs/policy-profiles</a>
            {' '}and{' '}
            <a href="https://github.com/chronicle-app/chronicle/blob/main/docs/role-based-review-checklists.md" target="_blank" rel="noreferrer">role-based review checklists</a>.
          </p>
          <ul className="list">
            <li><strong>Journalism</strong> — Two-source rule, named sources, tensions block publication.</li>
            <li><strong>Legal</strong> — Stricter MES, chain of custody, tension resolution for checkpoints.</li>
            <li><strong>Compliance</strong> — Evidence admissibility, exception workflow, all tensions addressed.</li>
            <li><strong>History/Research</strong> — Source-context-heavy review with explicit uncertainty handling.</li>
          </ul>
          <h3>Compatibility preflight</h3>
          <p className="muted">Compare built-under policy to a viewing policy before checkpoint/export/submission.</p>
          <div className="control-row">
            <label>Viewing profile: <select value={policyViewingId} onChange={(e) => setPolicyViewingId(e.target.value)}>
              <option value="policy_legal">policy_legal</option>
              <option value="policy_compliance">policy_compliance</option>
              <option value="policy_history_research">policy_history_research</option>
              <option value="policy_investigative_journalism">policy_investigative_journalism</option>
            </select></label>
            <label>Built-under override (optional): <input type="text" placeholder="policy_investigative_journalism" value={policyBuiltUnderOverride} onChange={(e) => setPolicyBuiltUnderOverride(e.target.value)} /></label>
            <button type="button" onClick={doPolicyPreflight} disabled={policyCompatLoading}>
              {policyCompatLoading ? 'Running preflight…' : 'Run compatibility preflight'}
            </button>
          </div>
          {policyCompat && (
            <>
              <p className="meta">
                Built-under: <strong>{policyCompat.built_under || '(none)'}</strong> · Viewing: <strong>{policyCompat.viewing_under || '(none)'}</strong>
              </p>
              {policyCompat.message && <p className="muted">{policyCompat.message}</p>}
              {policyCompat.deltas.length === 0 ? (
                <p className="muted">No rule deltas.</p>
              ) : (
                <ul className="list">
                  {policyCompat.deltas.map((d, idx) => (
                    <li key={`${d.rule}-${idx}`}>
                      <strong>{d.rule}</strong> · built-under={JSON.stringify(d.built_under_value)} · viewing={JSON.stringify(d.viewing_under_value)}
                      {d.note ? ` · ${d.note}` : ''}
                    </li>
                  ))}
                </ul>
              )}
            </>
          )}
        </section>
      )}

      {tab === 'graph' && (
        <section>
          <h3>Graph (claims and evidence)</h3>
          {graphData ? (
            <div className="graph-viz">
              <svg viewBox="0 0 400 300" width="100%" style={{ maxWidth: 600, height: 300 }}>
                {graphData.nodes.map((n, i) => {
                  const row = Math.floor(i / 4)
                  const col = i % 4
                  const x = 80 + col * 100
                  const y = 40 + row * 80
                  return (
                    <g key={n.id}>
                      <rect x={x - 40} y={y - 12} width={80} height={24} rx={4} fill={n.type === 'claim' ? '#dbeafe' : '#e0e7ff'} stroke="#334155" />
                      <text x={x} y={y + 4} textAnchor="middle" fontSize={10} fill="#0f172a">{n.label.slice(0, 10)}…</text>
                    </g>
                  )
                })}
                {graphData.edges.map((e, i) => {
                  const fromI = graphData.nodes.findIndex((n) => n.id === e.from)
                  const toI = graphData.nodes.findIndex((n) => n.id === e.to)
                  if (fromI < 0 || toI < 0) return null
                  const fromRow = Math.floor(fromI / 4)
                  const fromCol = fromI % 4
                  const toRow = Math.floor(toI / 4)
                  const toCol = toI % 4
                  const x1 = 80 + fromCol * 100
                  const y1 = 40 + fromRow * 80
                  const x2 = 80 + toCol * 100
                  const y2 = 40 + toRow * 80
                  return (
                    <line key={i} x1={x1} y1={y1} x2={x2} y2={y2} stroke={e.link_type === 'support' ? '#22c55e' : '#ef4444'} strokeWidth={2} />
                  )
                })}
              </svg>
              <p className="muted">Green = support, red = challenge. Nodes: blue = claim, indigo = evidence.</p>
            </div>
          ) : (
            <p className="muted">Loading graph…</p>
          )}
        </section>
      )}
    </div>
  )
}

function TierHistory({ invId }: { invId: string }) {
  const [history, setHistory] = useState<Array<{ from_tier: string; to_tier: string; reason?: string; occurred_at: string; actor_id: string }>>([])
  useEffect(() => {
    api.getTierHistory(invId).then((r) => setHistory(r.tier_history)).catch(() => {})
  }, [invId])
  if (history.length === 0) return <p className="muted">No tier changes yet.</p>
  return (
    <ul className="list">
      {history.map((h, i) => (
        <li key={i}>{h.from_tier} → {h.to_tier} · {h.occurred_at} · {h.actor_id} {h.reason ? `· ${h.reason}` : ''}</li>
      ))}
    </ul>
  )
}
