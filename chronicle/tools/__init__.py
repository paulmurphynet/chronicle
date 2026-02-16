# Epistemic tool packages (Claim Decomposer, Contradiction Detector, MES Validator, etc.).
# See docs/spec/epistemic-tools.md.
#
# LLM backend (Phase 1): chronicle.tools.llm_config, chronicle.tools.llm_client (Ollama).
#
# Heuristic implementations (no LLM):
# - chronicle.tools.decomposer: analyze_claim_atomicity_heuristic(claim_text) -> DecompositionResult
# - chronicle.tools.contradiction: suggest_tensions_heuristic(claims) -> list[TensionSuggestion]
#
# Type and scope inference (Phase 5): chronicle.tools.type_scope_inference
# - suggest_claim_type_heuristic/llm(claim_text), suggest_scope_heuristic/llm(claim_text)
#
# Evidence relevance and temporal inference (Phase 6): chronicle.tools.evidence_temporal
# - suggest_evidence_links_heuristic/llm(claim_text, evidence_previews), suggest_temporal_heuristic/llm(claim_text, evidence_dates)
