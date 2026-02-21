# Glossary

Short definitions of terms you’ll see in Chronicle docs, lessons, and code. For deeper treatment, see the [Technical report](technical-report.md) and [Epistemology scope](epistemology-scope.md).

| Term | Definition |
|------|------------|
| Claim | A falsifiable statement (e.g. an answer from a model or a witness). Proposed, linked to evidence via support/challenge, and never stored as “true.” |
| Defensibility | How well a claim holds up *given* the recorded evidence, links, tensions, and policy rules. A structural, policy-relative score—*not* a truth value. We compute it; we don’t certify that the claim is true. |
| Evidence | Immutable content (e.g. a document, a retrieved chunk). Stored with a content hash. Support and challenge links point to spans within evidence, not whole items. |
| Evidence span | A segment within an evidence item (e.g. character offsets). Links say “this span supports/challenges this claim” so the connection is explicit. |
| .chronicle | The portable export format: a ZIP containing `manifest.json`, `chronicle.db` (SQLite), and an `evidence/` directory. Verifiable without running the full app. See [Chronicle file format](chronicle-file-format.md). |
| Eval contract | Input (query, answer, evidence) and output (defensibility metrics) for the standalone scorer. Lets eval harnesses plug in without depending on implementation details. See [Eval contract](eval_contract.md). |
| Event-sourced | All changes are stored as append-only events (e.g. EvidenceIngested, ClaimProposed, SupportLinked). State is derived by replaying events; history is never overwritten. |
| Investigation | Top-level container for one line of inquiry: one set of claims, evidence, and tensions (e.g. one RAG run or one case). |
| Support / challenge | Link types from an evidence span to a claim. *Support* = this evidence backs the claim; *challenge* = this evidence undermines it. Optional rationale (warrant) and defeater_kind (e.g. rebutting, undercutting) on links; optional defeater_kind on tensions. We record these; we don't verify them. Corroboration and defensibility use the counts. |
| Tension | An explicit record that two claims conflict or weaken each other. Status can be open, acknowledged, or resolved. Optional defeater_kind. Tensions are first-class and affect defensibility. |
| Source | A real-world origin for evidence. Optional independence_notes and reliability_notes (user-supplied; we record, we don't verify). Used for corroboration (e.g. independent_sources_count). |
| Epistemic stance | Optional label on a claim (e.g. working_hypothesis, asserted_established). Structural only; we don't commit to a theory of knowledge. |
| Policy rationale | Optional rationale or citation on a policy profile (why thresholds were chosen). We record; we don't validate. |
| Verifier | Standalone tool (`chronicle-verify`) that checks a .chronicle file: manifest, DB schema, evidence hashes. Does *not* check truth, semantics, or source independence. See [Verifier](verifier.md) and [Verification guarantees](verification-guarantees.md). |

## Terminology for interop

When integrating with fact-checking tools, argumentation frameworks, or provenance systems, these mappings can help align vocabulary:

| Chronicle term | Common equivalent(s) |
|----------------|----------------------|
| Claim | Statement, assertion, verdict (when from a fact-checker). |
| Support | Evidence for, supports, backs. |
| Challenge | Evidence against, contradicts, undermines. |
| Tension | Contradiction, conflict (between two claims). |
| Evidence (item) | Source, document, chunk. |
| Span | Quote or segment within a source. |
| Defensibility | Structural score given evidence and policy; not “truth” or “verdict.” |
| Investigation | Case, run, thread (one line of inquiry). |

Consumers can treat Chronicle’s claim as “the statement we’re assessing,” support/ challenge as “evidence for” / “evidence against,” and tension as “recorded contradiction between two claims.” Export formats (e.g. [generic export](GENERIC_EXPORT.md), [consuming .chronicle](consuming-chronicle.md)) use these names; adapters can map to local schemas using the table above.
