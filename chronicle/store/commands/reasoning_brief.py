"""Reasoning brief: one shareable artifact per claim (claim + defensibility + evidence + tensions + trail)."""

import html as html_module
from dataclasses import asdict
from datetime import UTC, datetime
from typing import Any

from chronicle.core.validation import MAX_LIST_LIMIT
from chronicle.store.commands.audit_trail import get_dismissals_relevant_to_claim
from chronicle.store.commands.claims import get_defensibility_score, get_weakest_link
from chronicle.store.commands.defensibility_as_of import get_defensibility_as_of
from chronicle.store.commands.reasoning_trail import get_reasoning_trail_claim
from chronicle.store.commands.sources import get_sources_backing_claim
from chronicle.store.protocols import EventStore, ReadModel


def assemble_reasoning_brief(
    store: EventStore,
    read_model: ReadModel,
    claim_uid: str,
    limit: int | None = None,
    *,
    as_of_date: str | None = None,
    as_of_event_id: str | None = None,
) -> dict[str, Any] | None:
    """Assemble all data for a claim's reasoning brief. Returns None if claim not found. B.2: When as_of_date or as_of_event_id is set, defensibility is at that point in time."""
    claim = read_model.get_claim(claim_uid)
    if claim is None:
        return None

    trail = get_reasoning_trail_claim(store, read_model, claim_uid, limit=limit)
    scorecard = get_defensibility_score(read_model, claim_uid)
    defensibility_as_of_label: str | None = None
    brief_defensibility: dict[str, Any] | None = asdict(scorecard) if scorecard else None
    if as_of_date is not None or as_of_event_id is not None:
        if as_of_date is not None and as_of_event_id is not None:
            raise ValueError("At most one of as_of_date or as_of_event_id may be set")
        as_of_result = get_defensibility_as_of(
            store,
            read_model,
            claim.investigation_uid,
            as_of_date=as_of_date,
            as_of_event_id=as_of_event_id,
        )
        if as_of_result:
            defensibility_as_of_label = as_of_result.get("as_of")
            for item in as_of_result.get("claims") or []:
                if item.get("claim_uid") == claim_uid:
                    defn = item.get("defensibility")
                    if defn is not None:
                        brief_defensibility = dict(defn)
                    break
    weakest = get_weakest_link(read_model, claim_uid)

    support_with_inherited = read_model.get_support_for_claim_including_inherited(claim_uid)
    supporting: list[dict[str, Any]] = []
    for link, inherited in support_with_inherited:
        span = read_model.get_evidence_span(link.span_uid)
        ev_item = read_model.get_evidence_item(span.evidence_uid) if span else None
        supporting.append(
            {
                "link_uid": link.link_uid,
                "span_uid": link.span_uid,
                "evidence_uid": span.evidence_uid if span else None,
                "original_filename": ev_item.original_filename if ev_item else None,
                "uri": ev_item.uri if ev_item else None,
                "inherited": inherited,
                "strength": getattr(link, "strength", None),
                "rationale": getattr(link, "rationale", None),
                "integrity_status": getattr(ev_item, "integrity_status", "UNVERIFIED")
                if ev_item
                else None,
                "last_verified_at": getattr(ev_item, "last_verified_at", None) if ev_item else None,
            }
        )

    challenge_with_inherited = read_model.get_challenges_for_claim_including_inherited(claim_uid)
    challenges: list[dict[str, Any]] = []
    for link, inherited in challenge_with_inherited:
        span = read_model.get_evidence_span(link.span_uid)
        ev_item = read_model.get_evidence_item(span.evidence_uid) if span else None
        challenges.append(
            {
                "link_uid": link.link_uid,
                "span_uid": link.span_uid,
                "evidence_uid": span.evidence_uid if span else None,
                "original_filename": ev_item.original_filename if ev_item else None,
                "uri": ev_item.uri if ev_item else None,
                "inherited": inherited,
                "strength": getattr(link, "strength", None),
                "rationale": getattr(link, "rationale", None),
                "integrity_status": getattr(ev_item, "integrity_status", "UNVERIFIED")
                if ev_item
                else None,
                "last_verified_at": getattr(ev_item, "last_verified_at", None) if ev_item else None,
            }
        )

    # Epistemology red team #4: evidence linked both as support and challenge
    support_evidence_uids = {s["evidence_uid"] for s in supporting if s.get("evidence_uid")}
    challenge_evidence_uids = {c["evidence_uid"] for c in challenges if c.get("evidence_uid")}
    support_and_challenge_same_evidence = list(support_evidence_uids & challenge_evidence_uids)

    # E6.2: Correction trail — supersessions for evidence that supports or challenges this claim
    evidence_uids_for_claim = support_evidence_uids | challenge_evidence_uids
    seen_supersession_uids: set[str] = set()
    correction_trail: list[dict[str, Any]] = []
    for ev_uid in evidence_uids_for_claim:
        for sup in read_model.list_supersessions_for_evidence(ev_uid):
            if sup.supersession_uid in seen_supersession_uids:
                continue
            seen_supersession_uids.add(sup.supersession_uid)
            prior_item = read_model.get_evidence_item(sup.prior_evidence_uid)
            new_item = read_model.get_evidence_item(sup.new_evidence_uid)
            correction_trail.append(
                {
                    "supersession_uid": sup.supersession_uid,
                    "prior_evidence_uid": sup.prior_evidence_uid,
                    "new_evidence_uid": sup.new_evidence_uid,
                    "supersession_type": sup.supersession_type,
                    "reason": sup.reason,
                    "created_at": sup.created_at,
                    "prior_display": (
                        prior_item.original_filename or prior_item.uri or sup.prior_evidence_uid
                    )
                    if prior_item
                    else sup.prior_evidence_uid,
                    "new_display": (
                        new_item.original_filename or new_item.uri or sup.new_evidence_uid
                    )
                    if new_item
                    else sup.new_evidence_uid,
                }
            )
    correction_trail.sort(key=lambda x: x["created_at"] or "")

    tensions_raw = read_model.get_tensions_for_claim(claim_uid)
    tensions: list[dict[str, Any]] = []
    for t in tensions_raw:
        other_uid = t.claim_b_uid if t.claim_a_uid == claim_uid else t.claim_a_uid
        other_claim = read_model.get_claim(other_uid)
        tensions.append(
            {
                "tension_uid": t.tension_uid,
                "other_claim_uid": other_uid,
                "other_claim_text": (other_claim.claim_text or "")[:200] if other_claim else None,
                "tension_kind": t.tension_kind,
                "status": t.status,
                "rationale_or_notes": t.notes,
                "created_at": t.created_at,
                "updated_at": t.updated_at,
            }
        )

    dismissals = get_dismissals_relevant_to_claim(
        store, read_model, claim.investigation_uid, claim_uid
    )

    retracted_links = read_model.get_retracted_links_for_claim(claim_uid)

    effective_limit = min(limit, MAX_LIST_LIMIT) if limit is not None else MAX_LIST_LIMIT
    sources_backing_claim = get_sources_backing_claim(read_model, claim_uid)

    # EC-2-opt: Claim set consistency (open vs resolved tension counts for the investigation).
    inv_tensions = read_model.list_tensions(claim.investigation_uid, limit=MAX_LIST_LIMIT)
    open_count = sum(1 for t in inv_tensions if t.status == "OPEN")
    claim_set_consistency = {
        "open_count": open_count,
        "resolved_count": len(inv_tensions) - open_count,
        "total": len(inv_tensions),
    }

    out = {
        "claim_uid": claim_uid,
        "investigation_uid": claim.investigation_uid,
        "claim_set_consistency": claim_set_consistency,
        "claim": {
            "claim_text": claim.claim_text,
            "claim_type": claim.claim_type,
            "current_status": claim.current_status,
            "created_at": claim.created_at,
        },
        "defensibility": brief_defensibility,
        "weakest_link": asdict(weakest) if weakest else None,
        "supporting_evidence": supporting,
        "sources_backing_claim": sources_backing_claim,
        "challenges": challenges,
        "support_and_challenge_same_evidence": support_and_challenge_same_evidence,
        "correction_trail": correction_trail,
        "tensions": tensions,
        "suggestions_dismissed": dismissals,
        "retracted_links": retracted_links,
        "reasoning_trail": trail,
        "events_limit": effective_limit,
    }
    if defensibility_as_of_label is not None:
        out["defensibility_as_of"] = defensibility_as_of_label
    return out


def reasoning_brief_to_html(
    brief: dict[str, Any],
    *,
    identity_assurance: str | None = None,
) -> str:
    """Render reasoning brief as a single HTML document. Clean typography, sections per REASONING_BRIEF.md. Phase 5.6: optional identity_assurance badge."""
    claim_info = brief.get("claim") or {}
    claim_text = (claim_info.get("claim_text") or "").strip()
    claim_type = claim_info.get("claim_type") or "—"
    claim_status = claim_info.get("current_status") or "—"
    esc = html_module.escape

    blocks: list[str] = []
    blocks.append(
        "<!DOCTYPE html><html><head><meta charset='utf-8'><title>Reasoning brief</title>"
        "<style>"
        "body{font-family:system-ui,sans-serif;max-width:720px;margin:2rem auto;padding:0 1rem;line-height:1.5;color:#1e293b;} "
        "h1{font-size:1.25rem;margin-top:1.5rem;margin-bottom:0.5rem;color:#0f172a;} "
        "h2{font-size:1rem;margin-top:1.25rem;margin-bottom:0.35rem;color:#334155;} "
        "p,ul,ol{margin:0.35rem 0;} "
        "ul,ol{padding-left:1.5rem;} "
        ".meta{color:#64748b;font-size:0.875rem;} "
        ".weakest{background:#fef3c7;padding:0.5rem 0.75rem;border-radius:0.25rem;} "
        "</style></head><body>"
    )
    generated_at = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    blocks.append(
        f"<p class='meta' style='margin-bottom:1rem;'>Generated at {esc(generated_at)}. "
        "This brief reflects the current state of the claim plus any retracted links listed below. "
        "<button type='button' onclick='window.print()' style='margin-left:0.5rem;padding:0.25rem 0.5rem;cursor:pointer;font-size:0.875rem;'>Print or Save as PDF</button></p>"
    )

    blocks.append("<h1>Claim</h1>")
    if claim_status == "WITHDRAWN":
        blocks.append(
            "<p style='background:#fef2f2;color:#991b1b;padding:0.5rem 0.75rem;border-radius:0.25rem;margin-bottom:1rem;'><strong>This claim has been withdrawn.</strong> The following is for the record only and does not represent current stance.</p>"
        )
    blocks.append(f"<p>{esc(claim_text) or '(no text)'}</p>")
    blocks.append(
        f"<p class='meta'>Type: {esc(str(claim_type))} · Status: {esc(str(claim_status))}</p>"
    )
    if claim_type == "OPEN_QUESTION":
        blocks.append(
            "<p class='meta'>This claim is marked as an <strong>open question</strong> (under inquiry; no conclusion yet).</p>"
        )

    # Phase C.2: optional methodology section (academic submission narrative)
    methodology = brief.get("methodology")
    if methodology and isinstance(methodology, dict):
        blocks.append("<h2>Methodology</h2>")
        if methodology.get("research_question"):
            blocks.append(
                f"<p><strong>Research question:</strong> {esc(str(methodology['research_question']))}</p>"
            )
        if methodology.get("method"):
            blocks.append(f"<p><strong>Method:</strong> {esc(str(methodology['method']))}</p>")
        if methodology.get("limitations"):
            blocks.append(
                f"<p><strong>Limitations:</strong> {esc(str(methodology['limitations']))}</p>"
            )
        as_of = methodology.get("as_of")
        if as_of:
            blocks.append(f"<p class='meta'>As of: {esc(str(as_of))}</p>")

    defensibility_as_of = brief.get("defensibility_as_of")
    if defensibility_as_of:
        blocks.append(
            f"<p class='meta'>Defensibility as of: {esc(str(defensibility_as_of))} (point-in-time snapshot for audit)</p>"
        )
    scorecard = brief.get("defensibility")
    if scorecard:
        blocks.append("<h2>Defensibility at a glance</h2>")
        # Phase 5 (source-independence): prominent epistemic limit in reviewer's words
        blocks.append(
            "<p class='meta'>Distinct sources and provenance are as you have modeled them; "
            "the system does not verify independence.</p>"
        )
        # Phase 1.3: Prominent evidence-integrity warning when claim looks strong but evidence is unverified
        prov = scorecard.get("provenance_quality", "")
        ev_integrity = scorecard.get("evidence_integrity")
        if prov in ("strong", "medium") and ev_integrity and ev_integrity != "verified":
            blocks.append(
                f"<p style='background:#fef3c7;border:1px solid #f59e0b;border-radius:0.25rem;padding:0.5rem 0.75rem;margin-bottom:1rem;'><strong>Evidence integrity issue:</strong> "
                f"This claim appears well-supported (provenance {esc(prov)}) but at least one supporting evidence item is {esc(ev_integrity)}. "
                f"Verify or re-ingest evidence before relying on this claim.</p>"
            )
        blocks.append(
            f"<p>Provenance: <strong>{esc(scorecard.get('provenance_quality', ''))}</strong> "
            f"(based on support count and distinct sources linked; not independently verified).</p>"
        )
        corr = scorecard.get("corroboration") or {}
        blocks.append(
            f"<p>Support: {corr.get('support_count', 0)} · "
            f"Challenges: {corr.get('challenge_count', 0)} · "
            f"Distinct sources (as you have modeled them; not independently verified): {corr.get('independent_sources_count', 0)}</p>"
        )
        blocks.append(
            "<p class='meta'>Distinct sources are as you have modeled them; not independently verified.</p>"
        )
        # Phase 1.2: Attribution and decomposition as recorded
        attr = scorecard.get("attribution_posture", "")
        decomp = scorecard.get("decomposition_precision", "")
        if attr or decomp:
            blocks.append(
                f"<p>Attribution posture: {esc(attr)} · Decomposition precision: {esc(decomp)} "
                f"<span class='meta'>(as recorded; not independently verified)</span></p>"
            )
        if (
            scorecard.get("evidence_integrity")
            and scorecard.get("evidence_integrity") != "verified"
        ):
            blocks.append(
                f"<p class='meta'>Evidence integrity: <strong>{esc(scorecard.get('evidence_integrity', ''))}</strong> — run verify or re-ingest.</p>"
            )
        blocks.append(
            f"<p>Contradiction status: {esc(scorecard.get('contradiction_status', ''))}</p>"
        )
    # EC-2-opt: Claim set consistency (open vs resolved tensions in this investigation).
    consistency = brief.get("claim_set_consistency")
    if consistency and isinstance(consistency, dict):
        open_c = consistency.get("open_count", 0)
        resolved_c = consistency.get("resolved_count", 0)
        blocks.append(
            "<h2>Claim set consistency</h2>"
            f"<p class='meta'>Open tensions: {open_c}; Resolved: {resolved_c}.</p>"
        )
    scorecard = brief.get("defensibility")
    if scorecard:
        know = scorecard.get("knowability") or {}
        known_as_of = know.get("known_as_of")
        if known_as_of:
            blocks.append(
                f"<p class='meta'>Establishable from evidence as of: {esc(known_as_of)}</p>"
            )

    weakest = brief.get("weakest_link")
    if weakest and weakest.get("dimension") != "none":
        blocks.append("<h2>Weakest link</h2>")
        blocks.append(
            f"<div class='weakest'><strong>{esc(weakest.get('label', ''))}</strong> "
            f"Action: {esc(weakest.get('action_hint', ''))}</div>"
        )

    # Phase 3 (source-independence): Sources backing this claim — who backs the claim and independence rationale
    sources_backing = brief.get("sources_backing_claim") or []
    blocks.append("<h2>Sources backing this claim</h2>")
    blocks.append(
        "<p class='meta'>Distinct sources are as you have modeled them; not independently verified.</p>"
    )
    # Phase 6: notice when 2+ sources but none have independence rationale
    if sources_backing and len(sources_backing) >= 2:
        has_rationale = any(
            s.get("independence_notes") and str(s.get("independence_notes", "")).strip()
            for s in sources_backing
        )
        if not has_rationale:
            blocks.append(
                "<p class='meta'>Notice: No independence rationale recorded for the sources above. "
                "For high-stakes use, add rationale on the Sources page (or in the project).</p>"
            )
    if not sources_backing:
        blocks.append("<p>None linked.</p>")
    else:
        blocks.append("<ul>")
        for src in sources_backing:
            name = src.get("display_name") or src.get("source_uid") or "—"
            notes = src.get("independence_notes")
            if notes and str(notes).strip():
                line = f"{esc(str(name))} — Independence rationale: {esc(str(notes).strip())}"
            else:
                line = f"{esc(str(name))} — No independence rationale recorded."
            blocks.append(f"<li>{line}</li>")
        blocks.append("</ul>")
    # One-sidedness visibility (EC-1, Phase 6): surface when one source only or no challenges
    challenges = brief.get("challenges") or []
    if len(sources_backing) == 1 or len(challenges) == 0:
        parts = []
        if len(sources_backing) == 1:
            parts.append("One source only.")
        if len(challenges) == 0:
            parts.append("No recorded challenges.")
        if parts:
            blocks.append(f"<p class='meta'>{' '.join(parts)}</p>")

    supporting = brief.get("supporting_evidence") or []
    blocks.append("<h2>Supporting evidence</h2>")
    if not supporting:
        blocks.append("<p>None linked.</p>")
    else:
        blocks.append("<ul>")
        for s in supporting:
            name = s.get("original_filename") or s.get("evidence_uid") or s.get("span_uid") or "—"
            inherited = " (inherited)" if s.get("inherited") else ""
            strength = s.get("strength")
            strength_note = f" — strength: {strength}" if strength is not None else ""
            integrity = s.get("integrity_status")
            last_verified = s.get("last_verified_at")
            integrity_note = f" — integrity: {esc(integrity or 'UNVERIFIED')}" + (
                f" (verified {esc(last_verified or '')})" if last_verified else ""
            )
            blocks.append(f"<li>{esc(str(name))}{inherited}{strength_note}{integrity_note}</li>")
        blocks.append("</ul>")

    challenges = brief.get("challenges") or []
    retracted_links = brief.get("retracted_links") or []
    if retracted_links:
        blocks.append("<h2>Retracted links</h2>")
        blocks.append(
            "<p class='meta'>The following support or challenge links were later retracted. They are listed for the record and are not included in defensibility.</p><ul>"
        )
        for r in retracted_links:
            link_type = (
                (r.get("link_type") or "")
                .replace("SUPPORTS", "support")
                .replace("CHALLENGES", "challenge")
            )
            display = (
                r.get("original_filename")
                or r.get("uri")
                or r.get("evidence_uid")
                or r.get("link_uid")
                or "—"
            )
            retracted_at = r.get("retracted_at") or ""
            rationale = (r.get("rationale") or "").strip()
            line = f"{esc(link_type)}: {esc(str(display))} (retracted {esc(retracted_at)})"
            if rationale:
                line += f". Rationale: {esc(rationale[:120])}{'…' if len(rationale) > 120 else ''}"
            blocks.append(f"<li>{line}</li>")
        blocks.append("</ul>")

    blocks.append("<h2>Challenges</h2>")
    if not challenges:
        blocks.append("<p>None.</p>")
    else:
        blocks.append("<ul>")
        for c in challenges:
            name = c.get("original_filename") or c.get("evidence_uid") or c.get("span_uid") or "—"
            inherited = " (inherited)" if c.get("inherited") else ""
            strength = c.get("strength")
            strength_note = f" — strength: {strength}" if strength is not None else ""
            integrity = c.get("integrity_status")
            last_verified = c.get("last_verified_at")
            integrity_note = f" — integrity: {esc(integrity or 'UNVERIFIED')}" + (
                f" (verified {esc(last_verified or '')})" if last_verified else ""
            )
            blocks.append(f"<li>{esc(str(name))}{inherited}{strength_note}{integrity_note}</li>")
        blocks.append("</ul>")

    same_evidence = brief.get("support_and_challenge_same_evidence") or []
    if same_evidence:
        blocks.append(
            "<p class='meta'>Note: The following evidence is linked both as support and as challenge: "
            + esc(", ".join(str(uid) for uid in same_evidence[:5]))
            + ("…" if len(same_evidence) > 5 else "")
            + "</p>"
        )

    tensions = brief.get("tensions") or []
    blocks.append("<h2>Tensions</h2>")
    if not tensions:
        blocks.append("<p>None.</p>")
    else:
        blocks.append("<ul>")
        for t in tensions:
            other = t.get("other_claim_uid") or "—"
            status = t.get("status") or "—"
            rationale = (t.get("rationale_or_notes") or "").strip()
            resolved_like = status in ("RESOLVED", "ACK", "INTRACTABLE", "SUPERSEDED")
            if resolved_like and not rationale:
                status_display = f"{status} (no rationale recorded)"
            else:
                status_display = status
            line = f"With claim {esc(other)}: {esc(status_display)}"
            if rationale:
                line += f". {esc(rationale[:150])}{'…' if len(rationale) > 150 else ''}"
            blocks.append(f"<li>{line}</li>")
        blocks.append("</ul>")

    suggestions_dismissed = brief.get("suggestions_dismissed") or []
    blocks.append("<h2>Suggestions considered and dismissed</h2>")
    if not suggestions_dismissed:
        blocks.append("<p>None.</p>")
    else:
        blocks.append("<ul>")
        for d in suggestions_dismissed:
            st = esc(d.get("suggestion_type", ""))
            ref = esc((d.get("suggestion_ref") or "")[:80])
            rationale = (d.get("rationale") or "").strip()
            rec = esc(d.get("recorded_at", ""))
            line = f"Type: {st} · Ref: {ref} · {rec}"
            if rationale:
                line += f" · Rationale: {esc(rationale[:120])}{'…' if len(rationale) > 120 else ''}"
            blocks.append(f"<li>{line}</li>")
        blocks.append("</ul>")

    # E6.2: Corrections and errata (evidence supersessions)
    correction_trail = brief.get("correction_trail") or []
    blocks.append("<h2>Corrections and errata</h2>")
    if not correction_trail:
        blocks.append("<p>None.</p>")
    else:
        blocks.append(
            "<p class='meta'>Evidence supersessions (correction, enhancement, or replacement) for evidence linked to this claim.</p><ul>"
        )
        for ct in correction_trail:
            stype = esc(ct.get("supersession_type", ""))
            prior_raw = (ct.get("prior_display") or ct.get("prior_evidence_uid") or "")[:60]
            new_raw = (ct.get("new_display") or ct.get("new_evidence_uid") or "")[:60]
            prior = esc(prior_raw)
            new = esc(new_raw)
            created = esc(ct.get("created_at", ""))
            blocks.append(
                f"<li><strong>{prior}</strong> superseded by <strong>{new}</strong> ({stype}) · {created}</li>"
            )
        blocks.append("</ul>")

    trail = brief.get("reasoning_trail") or {}
    events = trail.get("events") or []
    blocks.append("<h2>Reasoning trail</h2><ol>")
    for ev in events:
        et = ev.get("event_type", "")
        occ = ev.get("occurred_at", "")
        payload = ev.get("payload") or {}
        if et == "ClaimProposed":
            text = (payload.get("claim_text") or "")[:120]
            blocks.append(
                f"<li><strong>Claim proposed</strong> ({esc(occ)}). {esc(text)}{'…' if len(text) >= 120 else ''}</li>"
            )
        elif et == "SupportLinked":
            blocks.append(f"<li><strong>Support linked</strong> ({esc(occ)}).</li>")
        elif et == "ChallengeLinked":
            blocks.append(f"<li><strong>Challenge linked</strong> ({esc(occ)}).</li>")
        elif et == "ClaimTyped":
            blocks.append(
                f"<li><strong>Claim typed</strong> ({esc(occ)}). Type: {esc(str(payload.get('claim_type', '')))}.</li>"
            )
        elif et == "ClaimTemporalized":
            blocks.append(f"<li><strong>Claim temporalized</strong> ({esc(occ)}).</li>")
        elif et == "ClaimAsserted":
            blocks.append(f"<li><strong>Claim asserted</strong> ({esc(occ)}).</li>")
        elif et == "TensionDeclared":
            blocks.append(f"<li><strong>Tension declared</strong> ({esc(occ)}).</li>")
        elif et == "TensionStatusUpdated":
            blocks.append(f"<li><strong>Tension status updated</strong> ({esc(occ)}).</li>")
        else:
            blocks.append(f"<li><strong>{esc(et)}</strong> ({esc(occ)}).</li>")
    blocks.append("</ol>")

    footer = (
        f"Claim: {esc(brief.get('claim_uid', ''))} · "
        f"Investigation: {esc(brief.get('investigation_uid', ''))} · "
        f"Generated: {esc(generated_at)}. "
        "To verify the project: <code>chronicle verify path/to/project</code>. "
        "To verify a .chronicle export: <code>chronicle-verify path/to/file.chronicle</code>. "
        "This brief can be regenerated from the same project to confirm consistency."
    )
    if identity_assurance and identity_assurance.strip():
        footer += f". Actor identities: {esc(identity_assurance.strip())}"
    footer += "."
    blocks.append(
        f"<p class='meta' style='margin-top:2rem;padding-top:1rem;border-top:1px solid #e2e8f0;'>{footer}</p>"
    )
    blocks.append("</body></html>")
    return "\n".join(blocks)
