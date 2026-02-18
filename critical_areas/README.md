# Critical areas

This folder documents the **areas of Chronicle that most affect epistemological and practical risk**. The goal is to make limits explicit so that defensibility scores and the verifier are **not over-trusted**.

Chronicle is built to help people see how well a claim is supported by evidence—not to certify truth, verify real-world facts, or guarantee that “support” means logical entailment. These documents explain **what the system does and does not do** in the places where misunderstanding would be most dangerous. Each document combines **narrative** (why this matters, what the risk is) with **technical** pointers (where in the code this shows up) so that both decision-makers and engineers can align on the boundaries.

**On GitHub:** Use the table below. Each document has **← Critical areas index** and **Next →** at the bottom so you can read in order or jump back to this index.

---

## Who this is for

- **Anyone using defensibility scores** (evals, dashboards, pipelines): so you know what the numbers mean and what they don’t.
- **Engineers** integrating or extending Chronicle: so you don’t inadvertently promise more than the design supports.
- **Reviewers, auditors, and partners**: so “verified” and “defensibility” are interpreted correctly.

---

## Critical areas (list)

| Document | Risk addressed | One-line summary |
|----------|----------------|------------------|
| [01 — Defensibility is not truth](01-defensibility-is-not-truth.md) | Treating a “strong” score as “true.” | Defensibility is structural and policy-relative; we never assert truth. |
| [02 — Source independence is not verified](02-source-independence-is-not-verified.md) | Assuming “N independent sources” means N actually independent sources. | Independence is as modeled by the user; we do not verify it in the real world. |
| [03 — What the verifier does and does not check](03-what-the-verifier-checks.md) | Assuming “verified” means content is correct or trustworthy. | Verified = structural integrity, schema, hashes; not semantics, truth, or independence. |
| [04 — Evidence–claim linking: how it works and its limits](04-evidence-claim-linking.md) | Assuming “support” implies entailment or that we validated the link. | We record that a link exists; we do not model *why* or verify that evidence actually supports the claim. |
| [05 — Policy and thresholds](05-policy-and-thresholds.md) | Treating policy thresholds as domain-validated or scientifically grounded. | Policy drives scores; thresholds are configurable and not empirically validated per domain. |

---

## How to use these documents

- **Before relying on scores or verification:** Read at least 01, 02, and 03. They cover the three most common over-trust risks (truth, independence, verifier scope).
- **Before designing evals or integrations:** Read 04 and 05 so you know how linking and policy affect the numbers.
- **When documenting or presenting Chronicle:** Point stakeholders and users to this folder so “defensibility” and “verified” are understood within these boundaries.

---

## Relationship to other docs

- **[Epistemology scope](../docs/epistemology-scope.md)** — Full list of what we cover and what we don’t; critical_areas zooms in on the **highest-risk** boundaries and ties them to code.
- **[Technical report](../docs/technical-report.md)** — Defensibility definition and schema; critical_areas explains **limits** of that definition.
- **[Story](../story/README.md)** — The Chronicle story (mission, vision, narrative); critical_areas is the “handle with care” layer that keeps that story honest.
