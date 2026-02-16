# Type and scope inference for claims (Phase 5). Heuristic + LLM; UI pre-fill, user confirms.

import json
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from chronicle.tools.llm_client import LlmClient

# Valid claim types for suggestion (SEF is promotion-only, not suggested from text)
SUGGESTED_CLAIM_TYPES = frozenset({"SAC", "INFERENCE", "UNKNOWN"})

# Scope keys aligned with read model / ClaimScoped payload (who, where, when, conditions, etc.)
SCOPE_KEYS = frozenset({"who", "where", "when", "conditions", "exclusions", "domain"})


@dataclass
class TypeSuggestion:
    suggested_type: str  # SAC | INFERENCE | UNKNOWN
    rationale: str | None


@dataclass
class ScopeSuggestion:
    scope: dict[str, Any]  # who, where, when, conditions, exclusions, domain


# --- Type inference ---

_TYPE_SOURCE_PREFIXES = (
    "according to",
    "the document",
    "the filing",
    "the report",
    "as stated",
    "as per",
    "the source",
    "the record",
)
_TYPE_INFERENCE_PREFIXES = (
    "therefore",
    "thus",
    "this implies",
    "so ",
    "hence",
    "consequently",
    "it follows",
    "we conclude",
)


def suggest_claim_type_heuristic(claim_text: str) -> TypeSuggestion:
    """Heuristic type from opening words. No LLM."""
    if not (claim_text or "").strip():
        return TypeSuggestion(suggested_type="UNKNOWN", rationale="Empty claim.")
    lower = claim_text.strip().lower()
    for p in _TYPE_SOURCE_PREFIXES:
        if lower.startswith(p):
            return TypeSuggestion(
                suggested_type="SAC",
                rationale="Heuristic: opening suggests source attribution.",
            )
    for p in _TYPE_INFERENCE_PREFIXES:
        if lower.startswith(p):
            return TypeSuggestion(
                suggested_type="INFERENCE",
                rationale="Heuristic: opening suggests inference.",
            )
    return TypeSuggestion(
        suggested_type="UNKNOWN",
        rationale="Heuristic: no source or inference cue detected.",
    )


_TYPE_SYSTEM = """You are an analyst. Given a single claim sentence, classify its type for legal/evidential reasoning.
Output valid JSON only: {"type": "SAC"|"INFERENCE"|"UNKNOWN", "rationale": "brief reason"}.
- SAC: source-attributed claim (states what a document/source says).
- INFERENCE: conclusion or inference drawn from other claims or evidence.
- UNKNOWN: cannot determine or mixed.
Output only the JSON object, no other text."""


def _parse_type_response(raw: str) -> TypeSuggestion | None:
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
    t = data.get("type")
    if not isinstance(t, str) or not t.strip():
        return None
    t = t.strip().upper()
    if t not in SUGGESTED_CLAIM_TYPES:
        t = "UNKNOWN"
    rationale = data.get("rationale")
    rationale = rationale.strip() if isinstance(rationale, str) and rationale.strip() else None
    return TypeSuggestion(suggested_type=t, rationale=rationale)


def suggest_claim_type_llm(claim_text: str, client: "LlmClient") -> TypeSuggestion | None:
    """LLM type suggestion. Returns None on parse failure or client error."""
    if not (claim_text or "").strip():
        return TypeSuggestion(suggested_type="UNKNOWN", rationale="Empty claim.")
    prompt = f"Classify this claim:\n\n{claim_text.strip()}"
    try:
        raw = client.generate(prompt, system=_TYPE_SYSTEM)
    except Exception:
        return None
    return _parse_type_response(raw)


# --- Scope extraction ---


def suggest_scope_heuristic(claim_text: str) -> ScopeSuggestion:
    """Minimal heuristic scope (empty or placeholder). No LLM."""
    if not (claim_text or "").strip():
        return ScopeSuggestion(scope={})
    # Could add simple entity extraction later; for now return empty so UI can pre-fill with LLM or user
    return ScopeSuggestion(scope={})


_SCOPE_SYSTEM = """You are an analyst. Given a claim sentence, extract structured scope for who, where, when, and conditions.
Output valid JSON only. Use keys: who (person/entity), where (place/location), when (time/period), conditions (array or string), exclusions (optional), domain (optional).
Example: {"who": "the defendant", "where": null, "when": "2024", "conditions": [], "exclusions": null, "domain": null}.
Use null for missing values. Keep values short. Output only the JSON object, no other text."""


def _parse_scope_response(raw: str) -> ScopeSuggestion | None:
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
    scope: dict[str, Any] = {}
    for k in SCOPE_KEYS:
        v = data.get(k)
        if v is None:
            scope[k] = None
        elif isinstance(v, str | int | float | bool | list):
            scope[k] = v
        else:
            scope[k] = None
    return ScopeSuggestion(scope=scope)


def suggest_scope_llm(claim_text: str, client: "LlmClient") -> ScopeSuggestion | None:
    """LLM scope extraction. Returns None on parse failure or client error."""
    if not (claim_text or "").strip():
        return ScopeSuggestion(scope={})
    prompt = f"Extract scope from this claim:\n\n{claim_text.strip()}"
    try:
        raw = client.generate(prompt, system=_SCOPE_SYSTEM)
    except Exception:
        return None
    return _parse_scope_response(raw)
