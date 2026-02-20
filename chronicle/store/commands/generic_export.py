"""Generic export for integrations: JSON/CSV and standards-oriented exports."""

from __future__ import annotations

import csv
import io
import json
import zipfile
from collections.abc import Callable
from typing import Any, Protocol

from chronicle.eval_metrics import scorecard_to_metrics_dict
from chronicle.store.read_model import DefensibilityScorecard

GENERIC_EXPORT_SCHEMA_VERSION = 1
CLAIM_EVIDENCE_METRICS_SCHEMA_VERSION = 1
STANDARDS_JSONLD_SCHEMA_VERSION = 1
CLAIMREVIEW_EXPORT_SCHEMA_VERSION = 1
RO_CRATE_EXPORT_SCHEMA_VERSION = 1


class ReadModelLike(Protocol):
    def get_investigation(self, uid: str) -> Any: ...
    def list_claims_by_type(
        self,
        claim_type: str | None = ...,
        investigation_uid: str | None = ...,
        limit: int | None = ...,
        include_withdrawn: bool = ...,
    ) -> list: ...
    def list_evidence_by_investigation(self, investigation_uid: str) -> list: ...
    def list_tensions(
        self, investigation_uid: str, *, status: str | None = ..., limit: int = ...
    ) -> list: ...
    def get_support_for_claim(self, claim_uid: str) -> list: ...
    def get_challenges_for_claim(self, claim_uid: str) -> list: ...
    def get_evidence_span(self, span_uid: str) -> Any: ...
    def get_evidence_item(self, evidence_uid: str) -> Any: ...
    def get_sources_backing_claim(self, claim_uid: str) -> list[dict[str, Any]]: ...
    def list_sources_by_investigation(self, investigation_uid: str) -> list: ...
    def get_source(self, uid: str) -> Any: ...
    def list_evidence_source_links(self, evidence_uid: str) -> list: ...


def _get_sources_backing_claim_safe(read_model: ReadModelLike, claim_uid: str) -> list[dict[str, Any]]:
    """Return sources_backing_claim when read_model supports it (includes independence_notes)."""
    try:
        result = read_model.get_sources_backing_claim(claim_uid)
    except AttributeError:
        return []
    return result if isinstance(result, list) else []


def _row_to_dict(obj: Any) -> dict[str, Any]:
    """Convert dataclass to dict for JSON (no recursion for nested objects)."""
    if obj is None:
        return {}
    if hasattr(obj, "__dataclass_fields__"):
        return {k: getattr(obj, k) for k in obj.__dataclass_fields__}
    return {}


def _parse_json_maybe(value: Any) -> Any:
    """Best-effort parse for JSON-encoded string fields; keep raw on parse failure."""
    if value is None:
        return None
    if not isinstance(value, str):
        return value
    stripped = value.strip()
    if not stripped:
        return None
    if not (stripped.startswith("{") or stripped.startswith("[")):
        return value
    try:
        return json.loads(stripped)
    except json.JSONDecodeError:
        return value


def _normalize_link_type(raw: str | None) -> str:
    value = (raw or "").strip().upper()
    if value == "SUPPORTS":
        return "SUPPORT"
    if value == "CHALLENGES":
        return "CHALLENGE"
    if value in {"SUPPORT", "CHALLENGE"}:
        return value
    return "SUPPORT"


def _chronicle_urn(kind: str, uid: str) -> str:
    return f"urn:chronicle:{kind}:{uid}"


def _list_sources_safe(read_model: ReadModelLike, investigation_uid: str) -> list:
    """Return sources when supported by read model; otherwise empty list."""
    try:
        rows = read_model.list_sources_by_investigation(investigation_uid)
    except AttributeError:
        return []
    return rows if isinstance(rows, list) else []


def _get_source_safe(read_model: ReadModelLike, source_uid: str) -> Any:
    """Return one source object when supported by read model; otherwise None."""
    try:
        return read_model.get_source(source_uid)
    except AttributeError:
        return None


def _list_evidence_source_links_safe(read_model: ReadModelLike, evidence_uid: str) -> list:
    """Return evidence-source links when supported by read model; otherwise empty list."""
    try:
        rows = read_model.list_evidence_source_links(evidence_uid)
    except AttributeError:
        return []
    return rows if isinstance(rows, list) else []


def _source_node(source: Any) -> dict[str, Any]:
    """Build one JSON-LD source node."""
    source_uid = getattr(source, "source_uid", "") or ""
    source_id = _chronicle_urn("source", source_uid)
    node: dict[str, Any] = {
        "@id": source_id,
        "@type": ["prov:Agent", "chronicle:Source"],
        "chronicle:sourceUid": source_uid,
        "chronicle:displayName": getattr(source, "display_name", "") or "",
        "chronicle:sourceType": getattr(source, "source_type", "") or "",
    }
    if getattr(source, "alias", None):
        node["chronicle:alias"] = source.alias
    if getattr(source, "notes", None):
        node["chronicle:notes"] = source.notes
    if getattr(source, "independence_notes", None):
        node["chronicle:independenceNotes"] = source.independence_notes
    if getattr(source, "reliability_notes", None):
        node["chronicle:reliabilityNotes"] = source.reliability_notes
    return node


def build_generic_export_json(
    read_model: ReadModelLike,
    investigation_uid: str,
) -> dict[str, Any]:
    """Build generic export payload for one investigation. Phase 7.1. Documented in docs/GENERIC_EXPORT.md."""
    inv = read_model.get_investigation(investigation_uid)
    if inv is None:
        raise ValueError("Investigation not found")
    claims = read_model.list_claims_by_type(investigation_uid=investigation_uid, limit=10_000)
    evidence = read_model.list_evidence_by_investigation(investigation_uid)
    tensions = read_model.list_tensions(investigation_uid, limit=5000)
    return {
        "schema_version": GENERIC_EXPORT_SCHEMA_VERSION,
        "schema_doc": "https://github.com/chronicle-app/chronicle/blob/main/docs/GENERIC_EXPORT.md",
        "investigation": _row_to_dict(inv),
        "claims": [_row_to_dict(c) for c in claims],
        "evidence": [_row_to_dict(e) for e in evidence],
        "tensions": [_row_to_dict(t) for t in tensions],
    }


DefensibilityGetter = Callable[[str], DefensibilityScorecard | None]


def build_claim_evidence_metrics_export(
    read_model: ReadModelLike,
    get_defensibility_score: DefensibilityGetter,
    investigation_uid: str,
    *,
    claim_limit: int = 10_000,
) -> dict[str, Any]:
    """Build claim–evidence–metrics export for one investigation (stable JSON for fact-checking UIs).

    Returns a single JSON object with schema_version, investigation_uid, and a claims array. Each
    claim has claim_uid, claim_text, evidence_refs (evidence_uid, span_uid, link_type, uri),
    support_count, challenge_count, and defensibility (scorecard). Shape is defined in
    docs/claim-evidence-metrics-export.md.
    """
    inv = read_model.get_investigation(investigation_uid)
    if inv is None:
        raise ValueError("Investigation not found")
    inv_uid = getattr(inv, "investigation_uid", investigation_uid)
    claims = read_model.list_claims_by_type(
        investigation_uid=investigation_uid, limit=claim_limit
    )
    out_claims: list[dict[str, Any]] = []
    for c in claims:
        raw_claim_uid = getattr(c, "claim_uid", None)
        if not isinstance(raw_claim_uid, str) or not raw_claim_uid:
            continue
        claim_uid = raw_claim_uid
        claim_text = getattr(c, "claim_text", "") or ""
        support_links = read_model.get_support_for_claim(claim_uid)
        challenge_links = read_model.get_challenges_for_claim(claim_uid)
        evidence_refs: list[dict[str, Any]] = []
        for link in support_links + challenge_links:
            span = read_model.get_evidence_span(getattr(link, "span_uid", ""))
            evidence_uid = getattr(span, "evidence_uid", None) if span else None
            uri: str | None = None
            if evidence_uid:
                item = read_model.get_evidence_item(evidence_uid)
                uri = getattr(item, "uri", None) if item else None
            link_type = (getattr(link, "link_type", "") or "").replace("SUPPORTS", "SUPPORT").replace("CHALLENGES", "CHALLENGE")
            ref: dict[str, Any] = {
                "evidence_uid": evidence_uid or "",
                "link_type": link_type or "SUPPORT",
            }
            if getattr(link, "span_uid", None):
                ref["span_uid"] = link.span_uid
            if uri is not None:
                ref["uri"] = uri
            evidence_refs.append(ref)
        scorecard = get_defensibility_score(claim_uid)
        defensibility: dict[str, Any] = (
            scorecard_to_metrics_dict(claim_uid, scorecard) if scorecard else {}
        )
        claim_entry: dict[str, Any] = {
            "claim_uid": claim_uid,
            "claim_text": claim_text,
            "investigation_uid": inv_uid,
            "evidence_refs": evidence_refs,
            "support_count": len(support_links),
            "challenge_count": len(challenge_links),
            "defensibility": defensibility,
        }
        sources_backing = _get_sources_backing_claim_safe(read_model, claim_uid)
        if sources_backing:
            claim_entry["sources_backing_claim"] = sources_backing
        out_claims.append(claim_entry)
    return {
        "schema_version": CLAIM_EVIDENCE_METRICS_SCHEMA_VERSION,
        "schema_doc": "https://github.com/chronicle-app/chronicle/blob/main/docs/claim-evidence-metrics-export.md",
        "investigation_uid": inv_uid,
        "claims": out_claims,
    }


def build_standards_jsonld_export(
    read_model: ReadModelLike,
    investigation_uid: str,
    *,
    claim_limit: int = 10_000,
    include_withdrawn: bool = True,
) -> dict[str, Any]:
    """Build JSON-LD export profile for one investigation (JSON-LD + PROV-oriented mapping)."""
    inv = read_model.get_investigation(investigation_uid)
    if inv is None:
        raise ValueError("Investigation not found")

    investigation_id = _chronicle_urn("investigation", investigation_uid)
    claims = read_model.list_claims_by_type(
        investigation_uid=investigation_uid,
        limit=claim_limit,
        include_withdrawn=include_withdrawn,
    )
    evidence = read_model.list_evidence_by_investigation(investigation_uid)
    tensions = read_model.list_tensions(investigation_uid, limit=5000)
    sources = _list_sources_safe(read_model, investigation_uid)

    graph: list[dict[str, Any]] = [
        {
            "@id": investigation_id,
            "@type": ["prov:Bundle", "chronicle:Investigation"],
            "chronicle:investigationUid": investigation_uid,
            "chronicle:title": getattr(inv, "title", "") or "",
            "chronicle:description": getattr(inv, "description", None),
            "chronicle:createdAt": getattr(inv, "created_at", None),
            "chronicle:updatedAt": getattr(inv, "updated_at", None),
        }
    ]

    source_uids_seen: set[str] = set()
    for source in sources:
        source_uid = getattr(source, "source_uid", None)
        if not isinstance(source_uid, str) or not source_uid or source_uid in source_uids_seen:
            continue
        source_uids_seen.add(source_uid)
        graph.append(_source_node(source))

    evidence_ids_by_uid: dict[str, str] = {}
    for item in evidence:
        evidence_uid = getattr(item, "evidence_uid", "")
        if not isinstance(evidence_uid, str) or not evidence_uid:
            continue
        evidence_id = _chronicle_urn("evidence", evidence_uid)
        evidence_ids_by_uid[evidence_uid] = evidence_id

        node: dict[str, Any] = {
            "@id": evidence_id,
            "@type": ["prov:Entity", "chronicle:EvidenceItem"],
            "chronicle:evidenceUid": evidence_uid,
            "chronicle:investigation": {"@id": investigation_id},
            "chronicle:uri": getattr(item, "uri", "") or "",
            "chronicle:mediaType": getattr(item, "media_type", "") or "",
            "chronicle:contentHash": getattr(item, "content_hash", "") or "",
            "chronicle:integrityStatus": getattr(item, "integrity_status", "") or "",
            "chronicle:createdAt": getattr(item, "created_at", None),
        }
        metadata = _parse_json_maybe(getattr(item, "metadata_json", None))
        if metadata is not None:
            node["chronicle:metadata"] = metadata

        evidence_source_links = _list_evidence_source_links_safe(read_model, evidence_uid)
        source_refs: list[dict[str, str]] = []
        for es_link in evidence_source_links:
            source_uid = getattr(es_link, "source_uid", "")
            if not isinstance(source_uid, str) or not source_uid:
                continue
            source_id = _chronicle_urn("source", source_uid)
            source_refs.append({"@id": source_id})

            if source_uid not in source_uids_seen:
                source_obj = _get_source_safe(read_model, source_uid)
                if source_obj is not None:
                    source_uids_seen.add(source_uid)
                    graph.append(_source_node(source_obj))

            link_event = getattr(es_link, "source_event_id", "") or ""
            link_id = _chronicle_urn(
                "evidence-source-link",
                f"{evidence_uid}:{source_uid}:{link_event}",
            )
            link_node: dict[str, Any] = {
                "@id": link_id,
                "@type": ["prov:Attribution", "chronicle:EvidenceSourceLink"],
                "chronicle:evidence": {"@id": evidence_id},
                "chronicle:source": {"@id": source_id},
                "prov:entity": {"@id": evidence_id},
                "prov:agent": {"@id": source_id},
            }
            if getattr(es_link, "relationship", None):
                link_node["chronicle:relationship"] = es_link.relationship
            if getattr(es_link, "created_at", None):
                link_node["chronicle:createdAt"] = es_link.created_at
            if link_event:
                link_node["chronicle:sourceEventId"] = link_event
            graph.append(link_node)
        if source_refs:
            node["prov:wasAttributedTo"] = source_refs
        graph.append(node)

    span_uids_seen: set[str] = set()
    for claim in claims:
        claim_uid = getattr(claim, "claim_uid", "")
        if not isinstance(claim_uid, str) or not claim_uid:
            continue
        claim_id = _chronicle_urn("claim", claim_uid)

        support_links = read_model.get_support_for_claim(claim_uid)
        challenge_links = read_model.get_challenges_for_claim(claim_uid)
        support_evidence_refs: list[dict[str, str]] = []
        challenge_evidence_refs: list[dict[str, str]] = []
        support_seen: set[str] = set()
        challenge_seen: set[str] = set()

        for link in support_links + challenge_links:
            span_uid = getattr(link, "span_uid", "")
            span = read_model.get_evidence_span(span_uid) if span_uid else None
            if span is None:
                continue
            evidence_uid = getattr(span, "evidence_uid", "")
            evidence_id = evidence_ids_by_uid.get(evidence_uid, _chronicle_urn("evidence", evidence_uid))
            span_id = _chronicle_urn("span", span_uid)

            if span_uid and span_uid not in span_uids_seen:
                span_uids_seen.add(span_uid)
                graph.append(
                    {
                        "@id": span_id,
                        "@type": ["prov:Entity", "chronicle:EvidenceSpan"],
                        "chronicle:spanUid": span_uid,
                        "chronicle:evidence": {"@id": evidence_id},
                        "chronicle:anchorType": getattr(span, "anchor_type", "") or "",
                        "chronicle:anchor": _parse_json_maybe(getattr(span, "anchor_json", None)),
                    }
                )

            link_uid = getattr(link, "link_uid", "") or f"{claim_uid}:{span_uid}"
            link_id = _chronicle_urn("evidence-link", link_uid)
            normalized = _normalize_link_type(getattr(link, "link_type", None))
            graph.append(
                {
                    "@id": link_id,
                    "@type": ["prov:Influence", "chronicle:EvidenceLink"],
                    "chronicle:linkUid": link_uid,
                    "chronicle:linkType": normalized,
                    "chronicle:claim": {"@id": claim_id},
                    "chronicle:evidence": {"@id": evidence_id},
                    "chronicle:span": {"@id": span_id},
                    "prov:entity": {"@id": evidence_id},
                    "prov:influenced": {"@id": claim_id},
                    "chronicle:rationale": getattr(link, "rationale", None),
                    "chronicle:notes": getattr(link, "notes", None),
                    "chronicle:strength": getattr(link, "strength", None),
                    "chronicle:defeaterKind": getattr(link, "defeater_kind", None),
                    "chronicle:createdAt": getattr(link, "created_at", None),
                }
            )

            if normalized == "SUPPORT":
                if evidence_id not in support_seen:
                    support_seen.add(evidence_id)
                    support_evidence_refs.append({"@id": evidence_id})
            else:
                if evidence_id not in challenge_seen:
                    challenge_seen.add(evidence_id)
                    challenge_evidence_refs.append({"@id": evidence_id})

        claim_node: dict[str, Any] = {
            "@id": claim_id,
            "@type": ["prov:Entity", "chronicle:Claim"],
            "chronicle:claimUid": claim_uid,
            "chronicle:text": getattr(claim, "claim_text", "") or "",
            "chronicle:status": getattr(claim, "current_status", "") or "",
            "chronicle:claimType": getattr(claim, "claim_type", None),
            "chronicle:investigation": {"@id": investigation_id},
            "chronicle:createdAt": getattr(claim, "created_at", None),
            "chronicle:updatedAt": getattr(claim, "updated_at", None),
        }
        if support_evidence_refs:
            claim_node["prov:wasDerivedFrom"] = support_evidence_refs
            claim_node["chronicle:supportingEvidence"] = support_evidence_refs
        if challenge_evidence_refs:
            claim_node["chronicle:challengingEvidence"] = challenge_evidence_refs
        graph.append(claim_node)

    for tension in tensions:
        tension_uid = getattr(tension, "tension_uid", "")
        claim_a_uid = getattr(tension, "claim_a_uid", "")
        claim_b_uid = getattr(tension, "claim_b_uid", "")
        if not isinstance(tension_uid, str) or not tension_uid:
            continue
        if not isinstance(claim_a_uid, str) or not isinstance(claim_b_uid, str):
            continue
        tension_id = _chronicle_urn("tension", tension_uid)
        claim_a_id = _chronicle_urn("claim", claim_a_uid)
        claim_b_id = _chronicle_urn("claim", claim_b_uid)
        graph.append(
            {
                "@id": tension_id,
                "@type": ["prov:Influence", "chronicle:Tension"],
                "chronicle:tensionUid": tension_uid,
                "chronicle:status": getattr(tension, "status", "") or "",
                "chronicle:tensionKind": getattr(tension, "tension_kind", None),
                "chronicle:defeaterKind": getattr(tension, "defeater_kind", None),
                "chronicle:notes": getattr(tension, "notes", None),
                "chronicle:claimA": {"@id": claim_a_id},
                "chronicle:claimB": {"@id": claim_b_id},
                "prov:influencer": {"@id": claim_a_id},
                "prov:influenced": {"@id": claim_b_id},
                "chronicle:createdAt": getattr(tension, "created_at", None),
                "chronicle:updatedAt": getattr(tension, "updated_at", None),
            }
        )

    return {
        "@context": {
            "prov": "http://www.w3.org/ns/prov#",
            "chronicle": "https://w3id.org/chronicle/ns#",
            "schema": "https://schema.org/",
            "xsd": "http://www.w3.org/2001/XMLSchema#",
        },
        "schema_version": STANDARDS_JSONLD_SCHEMA_VERSION,
        "schema_doc": "https://github.com/chronicle-app/chronicle/blob/main/docs/standards-jsonld-export.md",
        "chronicle_context_version": 1,
        "@id": investigation_id,
        "@type": ["prov:Bundle", "chronicle:InvestigationBundle"],
        "chronicle:investigationUid": investigation_uid,
        "@graph": graph,
    }


def _coerce_types(node: dict[str, Any]) -> set[str]:
    """Return node @type values as a normalized set of strings."""
    raw = node.get("@type")
    if isinstance(raw, str):
        return {raw}
    if isinstance(raw, list):
        return {x for x in raw if isinstance(x, str)}
    return set()


def _single_ref_id(value: Any) -> str | None:
    """Extract one @id string from a dict reference; otherwise None."""
    if not isinstance(value, dict):
        return None
    raw = value.get("@id")
    return raw if isinstance(raw, str) and raw else None


def _ref_ids(value: Any) -> list[str]:
    """Extract one or many @id values from dict/list reference fields."""
    if isinstance(value, dict):
        ref = _single_ref_id(value)
        return [ref] if ref else []
    if isinstance(value, list):
        out: list[str] = []
        for item in value:
            ref = _single_ref_id(item)
            if ref:
                out.append(ref)
        return out
    return []


def validate_standards_jsonld_export(payload: dict[str, Any]) -> list[str]:
    """Validate required PROV-aligned mapping invariants for standards JSON-LD export."""
    errors: list[str] = []
    graph = payload.get("@graph")
    if not isinstance(graph, list):
        return ["@graph must be a list of JSON-LD nodes"]

    nodes_by_id: dict[str, dict[str, Any]] = {}
    types_by_id: dict[str, set[str]] = {}
    for index, node in enumerate(graph):
        if not isinstance(node, dict):
            errors.append(f"@graph[{index}] must be an object")
            continue
        node_id = node.get("@id")
        if not isinstance(node_id, str) or not node_id:
            errors.append(f"@graph[{index}] missing @id")
            continue
        if node_id in nodes_by_id:
            errors.append(f"Duplicate node @id: {node_id}")
            continue
        nodes_by_id[node_id] = node
        types_by_id[node_id] = _coerce_types(node)

    def _ensure_ref_exists(owner: str, field: str, ref_id: str, required_type: str | None) -> None:
        if ref_id not in nodes_by_id:
            errors.append(f"{owner} field {field} references missing node {ref_id}")
            return
        if required_type and required_type not in types_by_id.get(ref_id, set()):
            errors.append(f"{owner} field {field} must reference node typed {required_type}: {ref_id}")

    for node_id, node in nodes_by_id.items():
        node_types = types_by_id.get(node_id, set())

        if "chronicle:Claim" in node_types and "prov:Entity" not in node_types:
            errors.append(f"{node_id} chronicle:Claim must include prov:Entity type")
        if "chronicle:EvidenceItem" in node_types and "prov:Entity" not in node_types:
            errors.append(f"{node_id} chronicle:EvidenceItem must include prov:Entity type")
        if "chronicle:EvidenceSpan" in node_types and "prov:Entity" not in node_types:
            errors.append(f"{node_id} chronicle:EvidenceSpan must include prov:Entity type")
        if "chronicle:Source" in node_types and "prov:Agent" not in node_types:
            errors.append(f"{node_id} chronicle:Source must include prov:Agent type")

        if "chronicle:Claim" in node_types:
            for ref_id in _ref_ids(node.get("prov:wasDerivedFrom")):
                _ensure_ref_exists(node_id, "prov:wasDerivedFrom", ref_id, "prov:Entity")

        if "chronicle:EvidenceLink" in node_types:
            if "prov:Influence" not in node_types:
                errors.append(f"{node_id} chronicle:EvidenceLink must include prov:Influence type")
            entity_ref = _single_ref_id(node.get("prov:entity"))
            influenced_ref = _single_ref_id(node.get("prov:influenced"))
            if not entity_ref:
                errors.append(f"{node_id} missing prov:entity reference")
            else:
                _ensure_ref_exists(node_id, "prov:entity", entity_ref, "prov:Entity")
            if not influenced_ref:
                errors.append(f"{node_id} missing prov:influenced reference")
            else:
                _ensure_ref_exists(node_id, "prov:influenced", influenced_ref, "prov:Entity")

        if "chronicle:EvidenceSourceLink" in node_types:
            if "prov:Attribution" not in node_types:
                errors.append(f"{node_id} chronicle:EvidenceSourceLink must include prov:Attribution type")
            entity_ref = _single_ref_id(node.get("prov:entity"))
            agent_ref = _single_ref_id(node.get("prov:agent"))
            if not entity_ref:
                errors.append(f"{node_id} missing prov:entity reference")
            else:
                _ensure_ref_exists(node_id, "prov:entity", entity_ref, "prov:Entity")
            if not agent_ref:
                errors.append(f"{node_id} missing prov:agent reference")
            else:
                _ensure_ref_exists(node_id, "prov:agent", agent_ref, "prov:Agent")

        if "chronicle:Tension" in node_types:
            if "prov:Influence" not in node_types:
                errors.append(f"{node_id} chronicle:Tension must include prov:Influence type")
            influencer_ref = _single_ref_id(node.get("prov:influencer"))
            influenced_ref = _single_ref_id(node.get("prov:influenced"))
            if not influencer_ref:
                errors.append(f"{node_id} missing prov:influencer reference")
            else:
                _ensure_ref_exists(node_id, "prov:influencer", influencer_ref, "chronicle:Claim")
            if not influenced_ref:
                errors.append(f"{node_id} missing prov:influenced reference")
            else:
                _ensure_ref_exists(node_id, "prov:influenced", influenced_ref, "chronicle:Claim")

    return errors


def _claimreview_rating_for_provenance(provenance_quality: str | None) -> tuple[int, str]:
    """Map Chronicle provenance labels to ClaimReview-compatible rating scale."""
    normalized = (provenance_quality or "").strip().lower()
    if normalized == "strong":
        return 4, "Supported"
    if normalized == "medium":
        return 3, "Mostly Supported"
    if normalized == "weak":
        return 2, "Weakly Supported"
    return 1, "Challenged"


def build_claimreview_export(
    read_model: ReadModelLike,
    get_defensibility_score: DefensibilityGetter,
    investigation_uid: str,
    *,
    claim_limit: int = 10_000,
    publisher_name: str = "Chronicle",
) -> dict[str, Any]:
    """Build schema.org ClaimReview profile for one investigation."""
    inv = read_model.get_investigation(investigation_uid)
    if inv is None:
        raise ValueError("Investigation not found")

    claim_rows = read_model.list_claims_by_type(
        investigation_uid=investigation_uid,
        limit=claim_limit,
        include_withdrawn=False,
    )
    claimreviews: list[dict[str, Any]] = []
    for claim in claim_rows:
        claim_uid = getattr(claim, "claim_uid", None)
        if not isinstance(claim_uid, str) or not claim_uid:
            continue
        scorecard = get_defensibility_score(claim_uid)
        if scorecard is None:
            continue

        rating_value, label = _claimreview_rating_for_provenance(
            getattr(scorecard, "provenance_quality", None)
        )
        claim_id = _chronicle_urn("claim", claim_uid)
        review_id = _chronicle_urn("claimreview", claim_uid)
        review_body = (
            "Chronicle defensibility rating derived from recorded support/challenge links, "
            "source modeling, and tension state. This is not a claim of absolute truth."
        )
        claimreviews.append(
            {
                "@type": "ClaimReview",
                "@id": review_id,
                "url": review_id,
                "claimReviewed": getattr(claim, "claim_text", "") or "",
                "itemReviewed": {
                    "@type": "Claim",
                    "@id": claim_id,
                    "identifier": claim_uid,
                    "text": getattr(claim, "claim_text", "") or "",
                },
                "author": {"@type": "Organization", "name": publisher_name},
                "reviewRating": {
                    "@type": "Rating",
                    "ratingValue": rating_value,
                    "bestRating": 4,
                    "worstRating": 1,
                    "alternateName": label,
                },
                "datePublished": getattr(claim, "created_at", None),
                "dateModified": getattr(claim, "updated_at", None),
                "inLanguage": getattr(claim, "language", None) or "en",
                "isPartOf": {"@id": _chronicle_urn("investigation", investigation_uid)},
                "reviewBody": review_body,
                "additionalType": "https://w3id.org/chronicle/ns#ClaimReviewProfileV1",
            }
        )

    return {
        "schema_version": CLAIMREVIEW_EXPORT_SCHEMA_VERSION,
        "schema_doc": "https://github.com/chronicle-app/chronicle/blob/main/docs/claimreview-export.md",
        "@context": "https://schema.org",
        "@type": "ItemList",
        "name": f"ClaimReview export for {getattr(inv, 'title', investigation_uid)}",
        "itemListElement": claimreviews,
    }


def build_ro_crate_export(
    read_model: ReadModelLike,
    investigation_uid: str,
    *,
    claim_limit: int = 10_000,
) -> dict[str, Any]:
    """Build a Chronicle RO-Crate profile for one investigation."""
    inv = read_model.get_investigation(investigation_uid)
    if inv is None:
        raise ValueError("Investigation not found")

    claims = read_model.list_claims_by_type(
        investigation_uid=investigation_uid,
        limit=claim_limit,
        include_withdrawn=True,
    )
    evidence = read_model.list_evidence_by_investigation(investigation_uid)
    tensions = read_model.list_tensions(investigation_uid, limit=5000)

    graph: list[dict[str, Any]] = [
        {
            "@id": "ro-crate-metadata.json",
            "@type": "CreativeWork",
            "about": {"@id": "./"},
            "conformsTo": {"@id": "https://w3id.org/ro/crate/1.2"},
        },
        {
            "@id": "chronicle.db",
            "@type": "File",
            "encodingFormat": "application/vnd.sqlite3",
            "name": "Chronicle SQLite store",
            "description": "Chronicle event log and read model database.",
        },
        {
            "@id": "manifest.json",
            "@type": "File",
            "encodingFormat": "application/json",
            "name": "Chronicle package manifest",
        },
    ]

    has_part: list[dict[str, str]] = [{"@id": "chronicle.db"}, {"@id": "manifest.json"}]
    for claim in claims:
        claim_uid = getattr(claim, "claim_uid", None)
        if not isinstance(claim_uid, str) or not claim_uid:
            continue
        claim_id = f"#claim:{claim_uid}"
        has_part.append({"@id": claim_id})
        text = getattr(claim, "claim_text", "") or ""
        graph.append(
            {
                "@id": claim_id,
                "@type": "CreativeWork",
                "additionalType": "https://w3id.org/chronicle/ns#Claim",
                "identifier": claim_uid,
                "name": text[:120] + ("..." if len(text) > 120 else ""),
                "text": text,
                "dateCreated": getattr(claim, "created_at", None),
                "dateModified": getattr(claim, "updated_at", None),
            }
        )

    for item in evidence:
        evidence_uid = getattr(item, "evidence_uid", None)
        if not isinstance(evidence_uid, str) or not evidence_uid:
            continue
        uri = getattr(item, "uri", "") or f"#evidence:{evidence_uid}"
        has_part.append({"@id": uri})
        graph.append(
            {
                "@id": uri,
                "@type": "File",
                "additionalType": "https://w3id.org/chronicle/ns#EvidenceItem",
                "identifier": evidence_uid,
                "name": getattr(item, "original_filename", "") or evidence_uid,
                "encodingFormat": getattr(item, "media_type", "") or "application/octet-stream",
                "sha256": getattr(item, "content_hash", "") or "",
                "dateCreated": getattr(item, "created_at", None),
            }
        )

    for tension in tensions:
        tension_uid = getattr(tension, "tension_uid", None)
        if not isinstance(tension_uid, str) or not tension_uid:
            continue
        tension_id = f"#tension:{tension_uid}"
        has_part.append({"@id": tension_id})
        graph.append(
            {
                "@id": tension_id,
                "@type": "CreativeWork",
                "additionalType": "https://w3id.org/chronicle/ns#Tension",
                "identifier": tension_uid,
                "name": f"Tension {tension_uid}",
                "description": getattr(tension, "notes", None),
                "dateCreated": getattr(tension, "created_at", None),
                "dateModified": getattr(tension, "updated_at", None),
            }
        )

    graph.append(
        {
            "@id": "./",
            "@type": ["Dataset", "https://w3id.org/chronicle/ns#InvestigationDataset"],
            "identifier": investigation_uid,
            "name": getattr(inv, "title", "") or investigation_uid,
            "description": getattr(inv, "description", None),
            "dateCreated": getattr(inv, "created_at", None),
            "dateModified": getattr(inv, "updated_at", None),
            "hasPart": has_part,
        }
    )

    return {
        "schema_version": RO_CRATE_EXPORT_SCHEMA_VERSION,
        "schema_doc": "https://github.com/chronicle-app/chronicle/blob/main/docs/ro-crate-export.md",
        "@context": ["https://w3id.org/ro/crate/1.2/context", {"chronicle": "https://w3id.org/chronicle/ns#"}],
        "@graph": graph,
    }


def build_generic_export_csv_zip(
    read_model: ReadModelLike,
    investigation_uid: str,
) -> bytes:
    """Build a ZIP containing investigations.csv, claims.csv, evidence.csv, tensions.csv. Phase 7.1."""
    inv = read_model.get_investigation(investigation_uid)
    if inv is None:
        raise ValueError("Investigation not found")
    claims = read_model.list_claims_by_type(investigation_uid=investigation_uid, limit=10_000)
    evidence = read_model.list_evidence_by_investigation(investigation_uid)
    tensions = read_model.list_tensions(investigation_uid, limit=5000)

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        # investigations (one row)
        inv_dict = _row_to_dict(inv)
        if inv_dict:
            out = io.StringIO()
            w = csv.DictWriter(out, fieldnames=list(inv_dict.keys()), extrasaction="ignore")
            w.writeheader()
            w.writerow(inv_dict)
            zf.writestr("investigations.csv", out.getvalue())

        # claims
        keys = list(_row_to_dict(claims[0]).keys()) if claims else []
        if keys:
            out = io.StringIO()
            w = csv.DictWriter(out, fieldnames=keys, extrasaction="ignore")
            w.writeheader()
            for c in claims:
                w.writerow(_row_to_dict(c))
            zf.writestr("claims.csv", out.getvalue())

        # evidence
        keys = list(_row_to_dict(evidence[0]).keys()) if evidence else []
        if keys:
            out = io.StringIO()
            w = csv.DictWriter(out, fieldnames=keys, extrasaction="ignore")
            w.writeheader()
            for e in evidence:
                w.writerow(_row_to_dict(e))
            zf.writestr("evidence.csv", out.getvalue())

        # tensions
        keys = list(_row_to_dict(tensions[0]).keys()) if tensions else []
        if keys:
            out = io.StringIO()
            w = csv.DictWriter(out, fieldnames=keys, extrasaction="ignore")
            w.writeheader()
            for t in tensions:
                w.writerow(_row_to_dict(t))
            zf.writestr("tensions.csv", out.getvalue())

    return buf.getvalue()


# Phase 12: optional legal adapters (load file, exhibit list)

LOAD_FILE_COLUMNS = [
    "ControlNumber",
    "FilePath",
    "NativePath",
    "OriginalFileName",
    "FileSize",
    "Hash",
    "DocType",
    "CreatedAt",
]


def build_load_file_csv(
    read_model: ReadModelLike,
    investigation_uid: str,
) -> str:
    """Build a load-file-style CSV for e-discovery tools. Phase 12. One row per evidence; ControlNumber = evidence_uid."""
    inv = read_model.get_investigation(investigation_uid)
    if inv is None:
        raise ValueError("Investigation not found")
    evidence = read_model.list_evidence_by_investigation(investigation_uid)
    out = io.StringIO()
    w = csv.DictWriter(out, fieldnames=LOAD_FILE_COLUMNS, extrasaction="ignore")
    w.writeheader()
    for e in evidence:
        row = {
            "ControlNumber": getattr(e, "evidence_uid", ""),
            "FilePath": getattr(e, "uri", ""),
            "NativePath": getattr(e, "uri", ""),
            "OriginalFileName": getattr(e, "original_filename", ""),
            "FileSize": getattr(e, "file_size_bytes", 0),
            "Hash": getattr(e, "content_hash", ""),
            "DocType": getattr(e, "media_type", ""),
            "CreatedAt": getattr(e, "created_at", ""),
        }
        w.writerow(row)
    return out.getvalue()


EXHIBIT_LIST_COLUMNS = [
    "ExhibitNumber",
    "Type",
    "UID",
    "Label",
]


def build_exhibit_list_csv(
    read_model: ReadModelLike,
    investigation_uid: str,
) -> str:
    """Build an exhibit-list-style CSV for legal (evidence + claims). Phase 12. ExhibitNumber is 1-based sequential."""
    inv = read_model.get_investigation(investigation_uid)
    if inv is None:
        raise ValueError("Investigation not found")
    evidence = read_model.list_evidence_by_investigation(investigation_uid)
    claims = read_model.list_claims_by_type(investigation_uid=investigation_uid, limit=10_000)
    out = io.StringIO()
    w = csv.DictWriter(out, fieldnames=EXHIBIT_LIST_COLUMNS, extrasaction="ignore")
    w.writeheader()
    n = 1
    for e in evidence:
        label = getattr(e, "original_filename", "") or getattr(e, "evidence_uid", "")
        if len(label) > 120:
            label = label[:117] + "..."
        w.writerow(
            {
                "ExhibitNumber": n,
                "Type": "evidence",
                "UID": getattr(e, "evidence_uid", ""),
                "Label": label,
            }
        )
        n += 1
    for c in claims:
        if getattr(c, "current_status", "") == "WITHDRAWN":
            continue
        label = (getattr(c, "claim_text", "") or "")[:120]
        if len(getattr(c, "claim_text", "") or "") > 120:
            label = label + "..."
        w.writerow(
            {
                "ExhibitNumber": n,
                "Type": "claim",
                "UID": getattr(c, "claim_uid", ""),
                "Label": label,
            }
        )
        n += 1
    return out.getvalue()


# Phase E.2: GRC export (optional format for compliance/GRC platforms)

GRC_CONTROLS_COLUMNS = [
    "control_uid",
    "control_text",
    "claim_type",
    "status",
    "created_at",
    "updated_at",
]

GRC_EVIDENCE_COLUMNS = [
    "evidence_uid",
    "original_filename",
    "content_hash",
    "media_type",
    "created_at",
    "integrity_status",
]

GRC_EXCEPTIONS_COLUMNS = [
    "tension_uid",
    "status",
    "due_date",
    "assigned_to",
    "remediation_type",
    "created_at",
    "notes",
]


def build_grc_export_zip(
    read_model: ReadModelLike,
    investigation_uid: str,
) -> bytes:
    """Build a ZIP with GRC-oriented CSVs: controls (claims), evidence, exceptions (tensions). Phase E.2. See docs/GRC_EXPORT.md."""
    inv = read_model.get_investigation(investigation_uid)
    if inv is None:
        raise ValueError("Investigation not found")
    claims = read_model.list_claims_by_type(investigation_uid=investigation_uid, limit=10_000)
    evidence = read_model.list_evidence_by_investigation(investigation_uid)
    tensions = read_model.list_tensions(investigation_uid, limit=5000)

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        out = io.StringIO()
        w = csv.DictWriter(out, fieldnames=GRC_CONTROLS_COLUMNS, extrasaction="ignore")
        w.writeheader()
        for c in claims:
            w.writerow(
                {
                    "control_uid": getattr(c, "claim_uid", ""),
                    "control_text": (getattr(c, "claim_text", "") or "")[:2000],
                    "claim_type": getattr(c, "claim_type", "") or "",
                    "status": getattr(c, "current_status", ""),
                    "created_at": getattr(c, "created_at", ""),
                    "updated_at": getattr(c, "updated_at", ""),
                }
            )
        zf.writestr("controls.csv", out.getvalue())

        out = io.StringIO()
        w = csv.DictWriter(out, fieldnames=GRC_EVIDENCE_COLUMNS, extrasaction="ignore")
        w.writeheader()
        for e in evidence:
            w.writerow(
                {
                    "evidence_uid": getattr(e, "evidence_uid", ""),
                    "original_filename": getattr(e, "original_filename", ""),
                    "content_hash": getattr(e, "content_hash", ""),
                    "media_type": getattr(e, "media_type", ""),
                    "created_at": getattr(e, "created_at", ""),
                    "integrity_status": getattr(e, "integrity_status", ""),
                }
            )
        zf.writestr("evidence.csv", out.getvalue())

        out = io.StringIO()
        w = csv.DictWriter(out, fieldnames=GRC_EXCEPTIONS_COLUMNS, extrasaction="ignore")
        w.writeheader()
        for t in tensions:
            w.writerow(
                {
                    "tension_uid": getattr(t, "tension_uid", ""),
                    "status": getattr(t, "status", ""),
                    "due_date": getattr(t, "due_date", "") or "",
                    "assigned_to": getattr(t, "assigned_to", "") or "",
                    "remediation_type": getattr(t, "remediation_type", "") or "",
                    "created_at": getattr(t, "created_at", ""),
                    "notes": getattr(t, "notes", "") or "",
                }
            )
        zf.writestr("exceptions.csv", out.getvalue())

    return buf.getvalue()
