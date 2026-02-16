# Claim Decomposer: heuristic (no LLM) and LLM path. Spec epistemic-tools.md 7.1.

import json
import re
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from chronicle.tools.llm_client import LlmClient


@dataclass(frozen=True)
class DecompositionResult:
    """Result of heuristic atomicity analysis."""

    is_atomic: bool
    suggested_splits: list[
        dict
    ]  # SuggestedSplit-shaped: suggested_text, source_offset_start, source_offset_end?, confidence, rationale?
    overall_confidence: float
    analysis_rationale: str | None


# Conjunction / clause boundaries (ordered: try longer patterns first)
_SPLIT_PATTERNS = [
    (r"\s+and\s+", " and "),
    (r"\s+but\s+", " but "),
    (r"\s+however\s*,?\s*", " however "),
    (r"\s+although\s+", " although "),
    (r"\s+while\s+", " while "),
    (r"\s*;\s*", ";"),  # semicolon (optional space either side)
    (r"\.\s+(?=[A-Z])", ". "),  # sentence boundary: period + space + capital
]


def analyze_claim_atomicity_heuristic(claim_text: str) -> DecompositionResult:
    """
    Heuristic claim decomposer: no LLM. Splits on conjunctions and sentence boundaries.
    Spec epistemic-tools.md 7.1 (Mode 1 — passive analysis).
    """
    if not (claim_text or "").strip():
        return DecompositionResult(
            is_atomic=True,
            suggested_splits=[],
            overall_confidence=0.0,
            analysis_rationale="Empty claim; treated as atomic.",
        )
    text = claim_text.strip()
    segments_with_offsets: list[tuple[str, int, int]] = []  # (segment, start, end) in original text

    for pattern, _ in _SPLIT_PATTERNS:
        parts = re.split(pattern, text, flags=re.IGNORECASE)
        segments_only = [p.strip() for p in parts if p.strip()]
        if len(segments_only) >= 2:
            # Compute start/end in original text for each segment
            search_start = 0
            for segment in segments_only:
                start = text.find(segment, search_start)
                if start == -1:
                    start = search_start
                end = start + len(segment)
                segments_with_offsets.append((segment, start, end))
                search_start = end
            break
    else:
        segments_with_offsets = [(text, 0, len(text))]

    if len(segments_with_offsets) <= 1:
        return DecompositionResult(
            is_atomic=True,
            suggested_splits=[],
            overall_confidence=0.7,
            analysis_rationale="No conjunction or sentence boundary detected; heuristic treats as atomic.",
        )

    suggested_splits = [
        {
            "suggested_text": seg,
            "source_offset_start": start,
            "source_offset_end": end,
            "confidence": 0.6,
            "rationale": "Split on conjunction or sentence boundary (heuristic).",
        }
        for seg, start, end in segments_with_offsets
    ]
    return DecompositionResult(
        is_atomic=False,
        suggested_splits=suggested_splits,
        overall_confidence=0.6,
        analysis_rationale=f"Heuristic found {len(segments_with_offsets)} segments (conjunction or sentence split).",
    )


# --- LLM path (Phase 2) ---

_DECOMPOSER_SYSTEM = """You are an analyst. Given a single claim, determine if it is one atomic fact or multiple independent facts.
If multiple, output valid JSON only with this shape: {"is_atomic": false, "splits": [{"text": "first proposition", "rationale": "why separate"}, ...], "rationale": "overall reason"}.
If one atomic claim: {"is_atomic": true, "splits": [], "rationale": "brief reason"}.
Output only the JSON object, no other text. Preserve the original meaning in each split; do not add or drop content."""


def _parse_llm_decomposition_response(raw: str) -> DecompositionResult | None:
    """Parse LLM JSON response into DecompositionResult. Returns None on parse failure."""
    if not (raw or "").strip():
        return None
    text = raw.strip()
    # Strip markdown code fence if present
    if text.startswith("```"):
        lines = text.split("\n")
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines)
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return None
    if not isinstance(data, dict):
        return None
    is_atomic = data.get("is_atomic", True)
    splits_raw = data.get("splits") or []
    rationale = data.get("rationale")
    if not isinstance(splits_raw, list):
        return None
    suggested_splits = []
    for s in splits_raw:
        if not isinstance(s, dict):
            continue
        st = s.get("text") or s.get("suggested_text") or ""
        if not st.strip():
            continue
        suggested_splits.append(
            {
                "suggested_text": st.strip(),
                "source_offset_start": None,
                "source_offset_end": None,
                "confidence": 0.8,
                "rationale": s.get("rationale") if isinstance(s.get("rationale"), str) else None,
            }
        )
    if is_atomic and suggested_splits:
        is_atomic = False
    return DecompositionResult(
        is_atomic=is_atomic,
        suggested_splits=suggested_splits,
        overall_confidence=0.8,
        analysis_rationale=rationale if isinstance(rationale, str) else "LLM analysis.",
    )


def analyze_claim_atomicity_llm(claim_text: str, client: "LlmClient") -> DecompositionResult | None:
    """
    Use LLM to analyze claim atomicity. Returns DecompositionResult or None on parse failure.
    Caller should fall back to heuristic when None or when client raises LlmClientError.
    """
    if not (claim_text or "").strip():
        return DecompositionResult(
            is_atomic=True,
            suggested_splits=[],
            overall_confidence=0.0,
            analysis_rationale="Empty claim.",
        )
    user_prompt = f"Analyze this claim for atomicity:\n\n{claim_text.strip()}"
    try:
        raw = client.generate(user_prompt, system=_DECOMPOSER_SYSTEM)
    except Exception:
        return None
    return _parse_llm_decomposition_response(raw)
