# Thought experiment 07: Pre-publication launch readiness panel review (detailed)

## Setup

A cross-functional launch panel evaluates whether Chronicle is ready for a public-repo first impression after the latest Neo4j, security, standards, and workflow hardening work.

Panelists:

1. **Nora Salim** (domain practitioner, public launch owner)
2. **Calvin Rhodes** (reviewer/auditor, trust and controls)
3. **Asha Menon** (methodologist, epistemic validity and scope discipline)
4. **Victor Hale** (product/integration specialist, MLOps and platform operations)

Materials reviewed:

- `docs/to_do.md`
- `docs/support-policy.md`
- `docs/neo4j.md`
- `docs/aura-graph-pipeline.md`
- `tests/test_neo4j_live_integration.py`
- `.github/workflows/ci.yml`
- `.github/workflows/release.yml`
- `thought_experiments/decision-register.md`

---

## Nora Salim (domain practitioner)

**What I think is done well**

- Chronicle's core story is coherent and now well-backed by concrete artifacts (scorer/verifier/contracts/workflows).
- Neo4j moved from "optional side path" to a credible operational projection surface.
- Lessons/story/docs now align with actual command surfaces and workflows.

**What could improve and why**

- **Public-launch blockers should be strictly framed.** The remaining blockers should be shown as a short explicit gate list for launch-day execution.
- **Public evidence capture discipline.** We need one reproducible post-public evidence bundle for CI + branch protection + Neo4j live gate status.

---

## Calvin Rhodes (reviewer/auditor)

**What I think is done well**

- Accountability surfaces (ledger/packet/readiness gate) are materially stronger than prior rounds.
- Security and supply-chain gating are integrated into release workflows.
- Neo4j contract and live-integration checks reduce projection drift risk.

**What could improve and why**

- **Final external verification still pending.** Branch-protection rollout evidence cannot be completed before public status changes.
- **Operational Neo4j guidance still partial.** Query-pack/ops runbook/support-level details should finish before any "best-in-class" claim language.

---

## Asha Menon (methodologist)

**What I think is done well**

- Chronicle preserved boundary discipline: defensibility, not truth certification.
- The project improved methodological transparency (link assurance, compatibility, sensitivity, messy corpus, readiness reporting).
- Thought-experiment loop is now genuinely iterative with implementation feedback.

**What could improve and why**

- **Performance evidence remains a gap.** Large-scale Neo4j behavior needs benchmark-backed ceilings/thresholds, not just architectural claims.
- **Chronology-specific historian artifact remains open.** This is a meaningful cross-domain interpretability opportunity.

---

## Victor Hale (product/integration specialist)

**What I think is done well**

- CI/release workflows are now close to production-grade with explicit gates and artifacts.
- Neo4j export/sync gained practical operations features (chunking, retries, timeouts, progress/report outputs).
- Live Neo4j integration test wiring in CI/release is the right maturity signal.

**What could improve and why**

- **Deterministic frontend install still blocked by lockfile.** `npm ci` migration should complete before public launch.
- **First public CI pass is critical.** The system is prepared, but external proof is still the final step.

---

## Synthesis (moderator)

**Shared praise**

- Core trust posture is strong and improved since Round 2.
- The project is substantially more publication-ready than before (especially around Neo4j and review operations).
- The thought-experiment recommendations are now visibly connected to implementation outcomes.

**Shared gaps**

1. Public-repo dependent checks are still pending by environment, not by architecture.
2. Neo4j "best-in-class" designation needs performance + ops/query-pack completion.
3. Deterministic frontend dependency workflow should be closed before public launch.

---

## Follow-up discussion: launch now vs wait for full best-in-class completion

Panel consensus:

- **Public launch readiness:** yes, with explicit disclosure of remaining non-core follow-ups.
- **Best-in-class Neo4j claim readiness:** not yet; keep as an active program until N-07 through N-12 are complete and externally evidenced.

Rejected position:

- "Delay public repo until every Neo4j best-in-class item is complete."  
  Panel rejected this as unnecessarily blocking because trust-critical core and launch blockers are already narrowly defined.

---

## Round 2 deferred-item status backfill (current state)

| ID | Previous status | Current status | Notes |
|---|---|---|---|
| EP-R2-1 | Defer | Completed | Policy sensitivity comparison shipped (`R2-01`). |
| EP-R2-2 | Defer | Completed | Messy/noisy corpus shipped (`R2-03`). |
| J-R2-2 | Defer | Completed | Portfolio cross-investigation risk summary shipped (`R2-02`). |
| C-R2-1 | Defer | Completed | One-shot readiness gate shipped (`R2-04`). |
| C-R2-2 | Defer | Completed | Portfolio exception analytics shipped (`R2-02`). |
| L-R2-2 | Defer | Completed | General readiness gate now covers required artifact posture checks (`R2-04`). |
| H-R2-1 | Defer | Completed | History-relevant messy archive corpus shipped (`R2-03`). |
| R-R2-1 | Defer | Completed | Pipeline readiness gate command/report shipped (`R2-04`). |
| R-R2-2 | Defer | Completed | Large/noisy stress sample capability shipped via messy corpus (`R2-03`). |
| J-R2-1 | Defer | Still deferred | Editorial deadline-priority packet view still open. |
| L-R2-1 | Defer | Still deferred | Legal-stage packet presets still open. |
| H-R2-2 | Defer | Still deferred | Chronology comparison artifact still open. |

---

## Agreed concrete change list

| ID | Change | Layer | Decision | Why |
|---|---|---|---|---|
| P-1 | Complete frontend lockfile + `npm ci` migration in CI/release workflows. | CI/release ops | Adopt | Needed for deterministic public supply-chain posture. |
| P-2 | Execute first public CI + branch-protection rollout verification and archive evidence report. | CI/governance evidence | Adopt | Final external validation blocker before public confidence claims. |
| P-3 | Keep Neo4j support level explicit as **Beta** until N-07..N-12 done and evidenced. | Support policy/docs | Adopt | Prevents over-claiming maturity. |
| P-4 | Complete N-07/N-08/N-09 (performance, cross-mode parity, failure-mode tests). | Neo4j engineering | Defer | Important for best-in-class objective, not immediate public-launch blocker. |
| P-5 | Complete N-10/N-11/N-12 (ops runbook, query pack, explicit compatibility policy details). | Neo4j docs/operations | Defer | Needed for production-operability excellence, can continue post-public with transparency. |
| P-X1 | Block public launch until every Neo4j best-in-class item is complete. | Strategy | Reject | Over-constrains launch despite core readiness and explicit remaining roadmap. |

---

## Recommendation summary

| ID | Recommendation | Decision |
|----|----------------|----------|
| P-1 | Frontend lockfile + `npm ci` migration | Adopt |
| P-2 | First public CI/branch-protection evidence capture | Adopt |
| P-3 | Keep Neo4j labeled Beta until full program completion | Adopt |
| P-4 | Finish Neo4j N-07..N-09 | Defer |
| P-5 | Finish Neo4j N-10..N-12 | Defer |
| P-X1 | Block public launch until all Neo4j items complete | Reject |
