# Code quality review

This document summarizes a project-wide review covering **logic errors**, **security**, and **test coverage**. It reflects the state of the repo after the hardening and tests added in this pass.

---

## 1. Test coverage

- **Overall:** ~34% statement coverage (pytest-cov on `chronicle`). Minimum required in config: 33%.
- **Well-covered:** `chronicle/core/events.py`, `chronicle/store/read_model/models.py`, `chronicle/core/errors.py`, `chronicle/eval_metrics.py` (~95%+), `chronicle/store/project.py`, `chronicle/store/schema.py` (~89%).
- **Under-covered:**
  - **CLI** (`chronicle/cli/main.py`): ~32% — many commands and branches untested; acceptable for a CLI driven by integration/manual use.
  - **Store commands:** evidence, claims, reasoning_brief, export_import, defensibility_as_of, tensions, sources, etc. at ~10–35%. Core session flow (ingest → claim → link → defensibility) is covered by `tests/test_session.py`.
  - **Optional/niche:** `chronicle/verify.py` (0%), `chronicle/store/read_model_snapshot.py` (0%), `chronicle/core/ssrf.py` (now covered by `tests/test_ssrf.py`), tools (contradiction, decomposer, evidence_temporal, llm_*, type_scope_inference), `chronicle/http_client.py`, `chronicle/core/policy_compat.py` — 0% and either optional or integration-heavy.
- **Tests added in this review:**
  - `tests/test_ssrf.py`: SSRF host checks (loopback, private, metadata, empty, public hostname).
  - `tests/test_scorer_security.py`: path traversal (paths outside cwd ignored), `allow_path=False` ignores path key.

**Recommendation:** Raise coverage on hot paths (scorer_contract, session, projection for core events, defensibility) and on `chronicle/verify.py` and `read_model_snapshot.py` when time allows. Keep CLI and optional tools as lower priority.

---

## 2. Security

### 2.1 Addressed in this review

- **Path traversal (scorer contract):** When `allow_path=True` (standalone script), evidence items with `"path"` are now restricted to paths under the current working directory. `Path(item["path"]).resolve().relative_to(Path.cwd().resolve())` is used; paths outside cwd (e.g. `/etc/passwd` or `../../../etc/passwd`) are skipped. The API uses `allow_path=False`, so path-based evidence is not accepted over HTTP.
- **SSRF (URL fetch):** The scorer’s `_fetch_url` uses `chronicle.core.ssrf.is_ssrf_unsafe_host()` and rejects non-http(s) schemes, blocks redirects to unsafe hosts, and caps response size (5 MiB). Tests in `test_ssrf.py` ensure loopback, private, metadata, and empty hosts are blocked and public hostnames are allowed by the host check.

### 2.2 Already in good shape

- **SQL:** Queries use parameterized statements (e.g. `conn.execute(sql, (param,))`). The only f-strings in SQL use fixed table/column lists (e.g. `READ_MODEL_TABLES_TRUNCATE_ORDER`, `_INSERT_ORDER`) or placeholder construction (`",".join("?" for _ in list)` with params passed separately). No user input is interpolated into SQL.
- **API:** No authentication in the minimal API; doc states to run behind auth/proxy in production. Project path comes from env (`CHRONICLE_PROJECT_PATH`), not from request body. POST /score does not accept path-based evidence.
- **Validation:** Evidence size capped by `MAX_EVIDENCE_BYTES`, claim text by `MAX_CLAIM_TEXT_LENGTH`, list limits by `MAX_LIST_LIMIT`, idempotency key cap by `MAX_IDEMPOTENCY_KEY_EVENTS`. FTS query sanitized and length-limited.

### 2.3 Recommendations

- **Standalone script + path evidence:** Use only with trusted input or from a dedicated directory; cwd-based restriction limits but does not eliminate risk if cwd is sensitive.
- **API auth:** Add auth (e.g. API key or OIDC) before exposing the API on untrusted networks.
- **Rate limiting:** Consider rate limiting for POST /score and other write endpoints in production.

---

## 3. Logic and correctness

- **Event store and projection:** Append-only event store with projection into read-model tables; replay and snapshot logic use the same apply path. No obvious ordering or double-apply bugs found.
- **Defensibility:** Computed from read model (support/challenge counts, tensions, policy); `eval_metrics.defensibility_metrics_for_claim` and scorecard shape are covered by session tests.
- **Scorer contract:** Validated in tests (valid input → metrics, invalid → error, URL fetch mocked). Path and URL branches now have path-traversal and SSRF coverage.
- **Neo4j sync:** Deduplication (evidence by content_hash, claims by hash of claim_text) and lineage (CONTAINS_EVIDENCE, CONTAINS_CLAIM) are consistent; table/column names in f-strings come from fixed lists.

**Recommendation:** Add regression tests for replay-from-event and snapshot create/restore when those features are exercised more in production.

---

## 4. Summary

| Area            | Status | Notes |
|-----------------|--------|--------|
| Test coverage   | OK     | 34%; core paths and scorer covered; CLI and optional modules under-covered. |
| SQL injection   | OK     | Parameterized queries; no user input in table/column names. |
| SSRF            | OK     | Host check + redirect check + size cap; tests added. |
| Path traversal  | OK     | Scorer path evidence restricted to under cwd; API does not accept path. |
| Auth / rate limit| Doc    | Out of scope for minimal API; document for production. |
| Logic / events  | OK     | No obvious bugs; replay/snapshot could use more tests. |

---

*Review date: 2025-02. Hardening: path traversal check in `chronicle/scorer_contract.py`; tests: `tests/test_ssrf.py`, `tests/test_scorer_security.py`.*
