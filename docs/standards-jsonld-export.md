# Standards JSON-LD export (S-02)

Chronicle provides a standards-oriented JSON-LD export profile for one investigation, with PROV-compatible mappings for core entities and relations.

## API

`chronicle.store.commands.generic_export.build_standards_jsonld_export(read_model, investigation_uid, *, claim_limit=10000, include_withdrawn=True)`

Validation API:

`chronicle.store.commands.generic_export.validate_standards_jsonld_export(payload)`

Returns a JSON object containing:

- `@context` with Chronicle and PROV prefixes
- `@type` bundle metadata
- `@graph` with investigation, claims, evidence, evidence spans, evidence links, tensions, sources, and evidence-source links
- `schema_version` and `chronicle_context_version` for compatibility checks

## Mapping intent

- Investigation -> `prov:Bundle` + `chronicle:Investigation`
- Claim/evidence/span -> `prov:Entity` + Chronicle profile types
- Support/challenge links -> `prov:Influence` + `chronicle:EvidenceLink`
- Tensions -> `prov:Influence` + `chronicle:Tension`
- Sources -> `prov:Agent` + `chronicle:Source`
- Evidence-source links -> `prov:Attribution` + `chronicle:EvidenceSourceLink`

Chronicle-specific fields stay namespaced under `chronicle:*`.

## Example (shape)

```json
{
  "@context": {
    "prov": "http://www.w3.org/ns/prov#",
    "chronicle": "https://w3id.org/chronicle/ns#"
  },
  "schema_version": 1,
  "chronicle_context_version": 1,
  "@type": ["prov:Bundle", "chronicle:InvestigationBundle"],
  "@graph": [
    {
      "@id": "urn:chronicle:claim:claim_123",
      "@type": ["prov:Entity", "chronicle:Claim"],
      "chronicle:text": "Example claim",
      "prov:wasDerivedFrom": [{"@id": "urn:chronicle:evidence:evidence_abc"}]
    }
  ]
}
```

## Notes

- This export is an interoperability profile; Chronicle's canonical artifact remains `.chronicle`.
- Semantic compatibility does not imply cryptographic verification.
- C2PA / VC / RO-Crate / ClaimReview compatibility layers are tracked separately in the standards program.

## PROV-required invariants (S-03)

The validator enforces minimum PROV-aligned mapping rules:

1. `chronicle:Claim`, `chronicle:EvidenceItem`, `chronicle:EvidenceSpan` include `prov:Entity`.
2. `chronicle:Source` includes `prov:Agent`.
3. `chronicle:EvidenceLink` includes `prov:Influence` and has resolvable `prov:entity` and `prov:influenced`.
4. `chronicle:EvidenceSourceLink` includes `prov:Attribution` and has resolvable `prov:entity` and `prov:agent`.
5. `chronicle:Tension` includes `prov:Influence` and has resolvable `prov:influencer` and `prov:influenced` pointing to claims.

Use this validator in tests or integration gates to ensure mapping regressions are caught early.
