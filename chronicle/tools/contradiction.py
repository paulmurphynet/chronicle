# Heuristic and LLM Contradiction Detector. Spec epistemic-tools.md 7.2.
# Suggests potential tensions; user confirms -> DeclareTension.

import json
import re
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from chronicle.tools.llm_client import LlmClient


@dataclass(frozen=True)
class TensionSuggestion:
    """One suggested tension (user must confirm to create TensionDeclared)."""

    claim_a_uid: str
    claim_b_uid: str
    suggested_tension_kind: str
    confidence: float
    rationale: str


# Negation / opposition cues
_NEGATION_WORDS = frozenset(
    {
        "not",
        "no",
        "never",
        "none",
        "neither",
        "nobody",
        "nothing",
        "nowhere",
        "hardly",
        "barely",
        "without",
        "deny",
        "denies",
        "denied",
        "false",
        "reject",
        "rejected",
    }
)
_POSITIVE_OPPOSITES = (
    ("failed", "succeeded", "succeed"),
    ("failure", "success"),
    ("wrong", "right", "correct"),
    ("false", "true"),
    ("denied", "confirmed", "admitted"),
    ("rejected", "accepted", "approved"),
    ("refused", "agreed"),
    ("against", "for", "support"),
    ("no", "yes"),
    ("never", "always"),
    ("impossible", "possible"),
    ("disagree", "agree"),
    ("disagreed", "agreed"),
)


def _normalize_words(s: str) -> list[str]:
    """Lowercase alphanumeric tokens."""
    return re.findall(r"[a-z0-9]+", s.lower())


def _has_negation(words: list[str]) -> bool:
    return bool(words and _NEGATION_WORDS & set(words))


def _word_overlap(a: list[str], b: list[str], min_overlap: int = 2) -> int:
    """Count of common words (excluding very short)."""
    sa = {w for w in a if len(w) > 2}
    sb = {w for w in b if len(w) > 2}
    return len(sa & sb)


def _opposition_score(text_a: str, text_b: str) -> float:
    """0..1 score if one text has a negative form and the other has the positive form."""
    wa = _normalize_words(text_a)
    wb = _normalize_words(text_b)
    for pair in _POSITIVE_OPPOSITES:
        # pair is e.g. ("failed", "succeeded", "succeed") -> first is neg, rest are pos
        negs = {pair[0]}
        poss = set(pair[1:])
        set_a = set(wa)
        set_b = set(wb)
        in_a_neg = bool(negs & set_a)
        in_a_pos = bool(poss & set_a)
        in_b_neg = bool(negs & set_b)
        in_b_pos = bool(poss & set_b)
        if (in_a_neg and in_b_pos) or (in_a_pos and in_b_neg):
            return 0.7
    if _has_negation(wa) != _has_negation(wb) and _word_overlap(wa, wb) >= 2:
        return 0.5
    return 0.0


def suggest_tensions_heuristic(
    claims: list[tuple[str, str]],  # (claim_uid, claim_text)
) -> list[TensionSuggestion]:
    """
    Heuristic contradiction detector: no LLM. Pairs claims that have
    overlapping subject matter and opposite polarity (negation / success-failure etc.).
    Spec epistemic-tools.md 7.2 (Mode 1 — passive analysis).
    """
    out: list[TensionSuggestion] = []
    n = len(claims)
    for i in range(n):
        uid_a, text_a = claims[i]
        words_a = _normalize_words(text_a)
        for j in range(i + 1, n):
            uid_b, text_b = claims[j]
            words_b = _normalize_words(text_b)
            overlap = _word_overlap(words_a, words_b)
            if overlap < 2:
                continue
            opp = _opposition_score(text_a, text_b)
            if opp >= 0.5:
                kind = "interpretation_variance"
                if opp >= 0.7:
                    kind = "source_conflict_unadjudicated"
                out.append(
                    TensionSuggestion(
                        claim_a_uid=uid_a,
                        claim_b_uid=uid_b,
                        suggested_tension_kind=kind,
                        confidence=opp,
                        rationale="Heuristic: overlapping subject with opposite polarity (negation or success/failure).",
                    )
                )
    return out


# --- LLM path (Phase 3) ---

_CONTRADICTION_SYSTEM = """You are an analyst comparing two claims for logical or factual tension.
Output valid JSON only with this shape: {"conflict": true|false, "confidence": 0.0-1.0, "rationale": "brief reason", "tension_kind": "interpretation_variance"|"source_conflict_unadjudicated"|"other"}.
Use tension_kind "source_conflict_unadjudicated" when sources directly contradict; "interpretation_variance" when interpretations differ. If no conflict, set "conflict": false and give a short rationale. Output only the JSON object, no other text."""

# Cap pairs sent to LLM to avoid timeouts.
_MAX_LLM_PAIRS = 50
# Phase 10: batch size for one LLM call (fewer calls when many pairs).
_BATCH_SIZE = 8

# Phase 10: system prompt for batched contradiction (array of results, one per pair in order).
_CONTRADICTION_BATCH_SYSTEM = """You are an analyst comparing claim pairs for logical or factual tension.
I will give you a list of pairs. Reply with a JSON array: one object per pair, in the same order.
Each object: {"conflict": true|false, "confidence": 0.0-1.0, "rationale": "brief reason", "tension_kind": "interpretation_variance"|"source_conflict_unadjudicated"|"other"}.
Use tension_kind "source_conflict_unadjudicated" when sources directly contradict; "interpretation_variance" when interpretations differ. If no conflict, set "conflict": false.
Output only the JSON array, no other text."""


def _parse_llm_contradiction_response(
    raw: str,
    claim_a_uid: str,
    claim_b_uid: str,
) -> TensionSuggestion | None:
    """Parse LLM JSON response into one TensionSuggestion. Returns None if no conflict or parse failure."""
    if not (raw or "").strip():
        return None
    text = raw.strip()
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
    if not data.get("conflict"):
        return None
    confidence = data.get("confidence")
    if isinstance(confidence, int | float):
        confidence = max(0.0, min(1.0, float(confidence)))
    else:
        confidence = 0.7
    rationale = data.get("rationale")
    if not isinstance(rationale, str) or not rationale.strip():
        rationale = "LLM detected conflict."
    else:
        rationale = rationale.strip()
    kind = data.get("tension_kind")
    if not isinstance(kind, str) or not kind.strip():
        kind = "interpretation_variance"
    else:
        kind = kind.strip()
    return TensionSuggestion(
        claim_a_uid=claim_a_uid,
        claim_b_uid=claim_b_uid,
        suggested_tension_kind=kind,
        confidence=confidence,
        rationale=rationale,
    )


def _parse_llm_contradiction_batch_response(
    raw: str,
    pairs: list[tuple[str, str, str, str]],  # (uid_a, uid_b, text_a, text_b) per pair
) -> list[TensionSuggestion]:
    """Parse LLM JSON array response (one object per pair in order). Phase 10. Returns only conflict=true; empty on parse failure or wrong array length."""
    if not (raw or "").strip() or not pairs:
        return []
    text = raw.strip()
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
        return []
    if not isinstance(data, list) or len(data) != len(pairs):
        return []
    out: list[TensionSuggestion] = []
    for idx, item in enumerate(data):
        if idx >= len(pairs):
            break
        if not isinstance(item, dict):
            continue
        if not item.get("conflict"):
            continue
        uid_a, uid_b, _text_a, _text_b = pairs[idx]
        confidence = item.get("confidence")
        if isinstance(confidence, int | float):
            confidence = max(0.0, min(1.0, float(confidence)))
        else:
            confidence = 0.7
        rationale = item.get("rationale")
        if not isinstance(rationale, str) or not rationale.strip():
            rationale = "LLM detected conflict."
        else:
            rationale = rationale.strip()
        kind = item.get("tension_kind")
        if not isinstance(kind, str) or not kind.strip():
            kind = "interpretation_variance"
        else:
            kind = kind.strip()
        out.append(
            TensionSuggestion(
                claim_a_uid=uid_a,
                claim_b_uid=uid_b,
                suggested_tension_kind=kind,
                confidence=confidence,
                rationale=rationale,
            )
        )
    return out


def suggest_tensions_llm(
    claims: list[tuple[str, str]],
    client: "LlmClient",
    *,
    max_pairs: int = _MAX_LLM_PAIRS,
    batch_size: int = _BATCH_SIZE,
) -> list[TensionSuggestion]:
    """
    Use LLM to suggest tensions between claim pairs. Phase 10: batches multiple pairs per call when batch_size > 1.
    On parse failure for a batch, falls back to heuristic for those pairs. Capped at max_pairs.
    Caller should fall back to suggest_tensions_heuristic on LlmClientError or when LLM is disabled.
    """
    from chronicle.tools.llm_client import LlmClientError

    # Collect pairs up to max_pairs: (uid_a, uid_b, text_a, text_b)
    n = len(claims)
    pairs: list[tuple[str, str, str, str]] = []
    for i in range(n):
        if len(pairs) >= max_pairs:
            break
        uid_a, text_a = claims[i]
        for j in range(i + 1, n):
            if len(pairs) >= max_pairs:
                break
            uid_b, text_b = claims[j]
            pairs.append((uid_a, uid_b, text_a, text_b))

    if not pairs:
        return []

    out: list[TensionSuggestion] = []
    for chunk_start in range(0, len(pairs), batch_size):
        chunk = pairs[chunk_start : chunk_start + batch_size]
        if batch_size > 1 and len(chunk) > 1:
            # Batched call (Phase 10)
            lines = []
            for k, (_ua, _ub, ta, tb) in enumerate(chunk, 1):
                lines.append(f"Pair {k}:\nClaim A: {ta}\nClaim B: {tb}")
            user_prompt = (
                "\n\n".join(lines)
                + "\n\nFor each pair above, output conflict (true/false), confidence, rationale, tension_kind. JSON array only, one object per pair in order."
            )
            try:
                raw = client.generate(user_prompt, system=_CONTRADICTION_BATCH_SYSTEM)
            except LlmClientError:
                raw = None
            if raw is None:
                for ua, ub, ta, tb in chunk:
                    out.extend(suggest_tensions_heuristic([(ua, ta), (ub, tb)]))
                continue
            batch_suggestions = _parse_llm_contradiction_batch_response(raw, chunk)
            # Valid batch = parser got array of right length (it returns [] on wrong length)
            try:
                text = raw.strip()
                if text.startswith("```"):
                    lines = text.split("\n")
                    if lines and lines[0].startswith("```"):
                        lines = lines[1:]
                    if lines and lines[-1].strip() == "```":
                        lines = lines[:-1]
                    text = "\n".join(lines)
                data = json.loads(text)
                valid_batch = isinstance(data, list) and len(data) == len(chunk)
            except (json.JSONDecodeError, Exception):
                valid_batch = False
            if valid_batch:
                out.extend(batch_suggestions)
            else:
                for ua, ub, ta, tb in chunk:
                    out.extend(suggest_tensions_heuristic([(ua, ta), (ub, tb)]))
        else:
            # Single-pair or batch_size=1: use original per-pair call
            for uid_a, uid_b, text_a, text_b in chunk:
                user_prompt = f"Claim A: {text_a}\n\nClaim B: {text_b}\n\nDo these conflict? Output JSON only."
                try:
                    raw = client.generate(user_prompt, system=_CONTRADICTION_SYSTEM)
                except LlmClientError:
                    raw = None
                if raw is None:
                    out.extend(suggest_tensions_heuristic([(uid_a, text_a), (uid_b, text_b)]))
                    continue
                suggestion = _parse_llm_contradiction_response(raw, uid_a, uid_b)
                if suggestion is not None:
                    out.append(suggestion)
                else:
                    out.extend(suggest_tensions_heuristic([(uid_a, text_a), (uid_b, text_b)]))
    return out
