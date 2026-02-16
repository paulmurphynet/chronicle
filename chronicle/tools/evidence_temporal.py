# Evidence relevance and temporal inference (Phase 6). Suggest links and known_as_of.

import json
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from chronicle.tools.llm_client import LlmClient

# Link types for evidence–claim relationship
LINK_TYPES = frozenset({"SUPPORTS", "CHALLENGES"})


@dataclass
class EvidenceLinkSuggestion:
    """One suggested link from evidence to a claim (user picks span when linking)."""

    evidence_uid: str
    link_type: str  # SUPPORTS | CHALLENGES
    rationale: str


# --- Evidence relevance ---


# Evidence preview: minimal info for the prompt (no full content in read model)
def suggest_evidence_links_heuristic(
    claim_text: str,
    evidence_previews: list[dict[str, Any]],  # [{"evidence_uid": str, "title": str}, ...]
) -> list[EvidenceLinkSuggestion]:
    """Heuristic: no content to match; return empty. Phase 6."""
    return []


_EVIDENCE_SYSTEM = """You are an analyst. Given a claim and a list of evidence items (id and title/filename), suggest which evidence might SUPPORT or CHALLENGE the claim.
Output valid JSON only: an array of objects with keys "evidence_uid", "link_type" ("SUPPORTS" or "CHALLENGES"), "rationale" (short reason).
Use the exact evidence_uid values from the input list. If none are relevant, output [].
Output only the JSON array, no other text."""


def _parse_evidence_links_response(
    raw: str,
    allowed_evidence_uids: set[str],
) -> list[EvidenceLinkSuggestion]:
    if not (raw or "").strip():
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
    if not isinstance(data, list):
        return []
    out: list[EvidenceLinkSuggestion] = []
    for item in data:
        if not isinstance(item, dict):
            continue
        uid = item.get("evidence_uid")
        if not isinstance(uid, str) or uid not in allowed_evidence_uids:
            continue
        lt = item.get("link_type")
        if not isinstance(lt, str) or lt not in LINK_TYPES:
            continue
        rationale = item.get("rationale")
        if not isinstance(rationale, str) or not rationale.strip():
            rationale = "LLM suggested link."
        else:
            rationale = rationale.strip()
        out.append(
            EvidenceLinkSuggestion(
                evidence_uid=uid,
                link_type=lt,
                rationale=rationale,
            )
        )
    return out


def suggest_evidence_links_llm(
    claim_text: str,
    evidence_previews: list[dict[str, Any]],
    client: "LlmClient",
) -> list[EvidenceLinkSuggestion]:
    """LLM suggests which evidence might support or challenge the claim. Returns [] on parse failure or error."""
    if not (claim_text or "").strip():
        return []
    if not evidence_previews:
        return []
    allowed: set[str] = set()
    for p in evidence_previews:
        uid = p.get("evidence_uid")
        if isinstance(uid, str):
            allowed.add(uid)
    if not allowed:
        return []
    lines = [
        f"- {p.get('evidence_uid', '')}: {p.get('title', p.get('original_filename', '?'))}"
        for p in evidence_previews
    ]
    evidence_list = "\n".join(lines)
    user_prompt = f"Claim: {claim_text.strip()}\n\nEvidence list:\n{evidence_list}\n\nWhich evidence might support or challenge this claim? Output JSON array only."
    try:
        raw = client.generate(user_prompt, system=_EVIDENCE_SYSTEM)
    except Exception:
        return []
    return _parse_evidence_links_response(raw, allowed)


# --- Temporal inference ---


def suggest_temporal_heuristic(
    evidence_dates: list[str],  # ISO date strings (e.g. created_at or from file_metadata)
) -> dict[str, Any]:
    """Rule-based: use oldest date as known_as_of. Phase 6."""
    if not evidence_dates:
        return {}
    valid = [d for d in evidence_dates if d and isinstance(d, str)]
    if not valid:
        return {}
    # Simple string sort; ISO dates sort correctly
    oldest = min(valid)
    return {"known_as_of": oldest}


_TEMPORAL_SYSTEM = """You are an analyst. Given a claim and available evidence dates, suggest a temporal context.
Output valid JSON only: {"known_as_of": "YYYY-MM-DD" or null, "event_time": "..." or null, "time_notes": "..." or null}.
Use the oldest evidence date as known_as_of if relevant. Keep values short. Output only the JSON object."""


def _parse_temporal_response(raw: str) -> dict[str, Any] | None:
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
    out: dict[str, Any] = {}
    for k in ("known_as_of", "event_time", "time_notes"):
        v = data.get(k)
        if v is not None and isinstance(v, str) and v.strip():
            out[k] = v.strip()
    return out if out else None


def suggest_temporal_llm(
    claim_text: str,
    evidence_dates: list[str],
    client: "LlmClient",
) -> dict[str, Any] | None:
    """LLM suggests temporal context from claim and evidence dates. Returns None on failure."""
    if not evidence_dates:
        return suggest_temporal_heuristic([])
    dates_str = ", ".join(evidence_dates[:20])  # cap
    user_prompt = f"Claim: {claim_text.strip()}\n\nEvidence dates available: {dates_str}\n\nSuggest known_as_of or event_time. Output JSON only."
    try:
        raw = client.generate(user_prompt, system=_TEMPORAL_SYSTEM)
    except Exception:
        return None
    return _parse_temporal_response(raw) or suggest_temporal_heuristic(evidence_dates)
