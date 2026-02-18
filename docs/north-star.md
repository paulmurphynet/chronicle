# North star: Chronicle’s ultimate potential

This document is Chronicle’s **north star**: where we are headed at full potential. It guides product, ecosystem, and design choices. We don’t promise to reach it by a date—we use it to decide what to build and what to say no to.

---

## Core identity (unchanging)

Chronicle is and remains the **epistemic layer**: evidence → claims → support/challenge → defensibility → verifiable artifact. We never decide “true” or “false”; we make **how well a claim is supported** visible, scoreable, and verifiable. That boundary is non-negotiable.

---

## Ultimate potential: where we grow

### 1. Shared infrastructure for “show your work”

Defensibility and “verify it yourself” become **default expectations** wherever answers must be backed by evidence: RAG and agent evals, fact-checking, audits, legal, research, compliance. The **.chronicle format and verifier** are the portable norm; dashboards, review UIs, and pipelines consume or produce .chronicle. Chronicle is the standard everyone plugs into when they care how they know what they claim.

### 2. One model from napkin to courtroom

The same investigation moves from **Spark** (scratchpad, weak anchoring) through **Forge** (typed and scoped, tensions acknowledged) to **Vault** (MES, checkpoints, submission)—no re-entry, no “now put it in the real system.” The Reference UI (and vendor UIs) make that path smooth; the backend already supports it. Human lawyers, journalists, and researchers get one workspace that can mature in place into something auditable and shareable.

### 3. Human and machine in one ledger

RAG and agents write as **tool**; humans confirm, dismiss, or override. **Propose–Confirm** and **dismissal-as-data** make “who stood behind what” explicit. As-of defensibility and reasoning trails answer “what did we know when?” and “who said so?”—the basis for accountability and for surviving scrutiny (legal, editorial, audit).

### 4. Policy as data, domains as profiles

One kernel, many domains: journalism, legal, academic, compliance (and others) are **policy profiles**, not separate products. Same events, same .chronicle; different MES, admissibility, and tension rules. Sharing an investigation across domains surfaces **policy compatibility** (“built under Journalism, viewed under Legal—here are the deltas”). Community or vertical-specific profiles extend the standard without forking it.

### 5. Ecosystem, not just product

Vendors build **their** UIs (legal, GRC, newsroom, research) on the same API and format. Labs and eval frameworks treat **defensibility as a standard metric**. Training and alignment pipelines consume **Chronicle-shaped data** (claims, evidence, links) for SFT or preference learning. The verifier and the contract live in Chronicle; the rest is integration. Growth is adoption and interoperability, not one app doing everything.

### 6. Time and knowability as first-class

“When could we first defend this?” and “what did we know at date D?” are already in the model. At full potential they are **visible in the product**: as-of defensibility views, knowability in the scorecard, and briefs that make the timeline of support and challenge obvious—for legal, regulatory, and any domain where timing of knowledge matters.

### 7. Stress-test by default

Defensibility already includes **weakest link** and **contradiction handling**. At full potential that’s the default posture: “What would contradict this? What’s the one thing that would most strengthen it?” The system helps people **prepare for challenge**, not only report a score.

---

## What stays out of scope (by design)

- **Truth or factuality** — We don’t assert what’s true; we track structure and support.
- **Verified independence or entailment** — Sources and support are “as modeled” or “as recorded”; we don’t promise to have verified the world or NLI.
- **Replacing lineage or ML provenance** — We complement them; we don’t become a general data-lineage or experiment-tracking tool.

See [Critical areas](../critical_areas/README.md) and [Epistemology scope](epistemology-scope.md) for the full boundaries.

---

## One sentence

**North star:** Chronicle becomes the **default standard and infrastructure for defensible, auditable claims**—for humans and AI—with one model from exploration to publication, one format and verifier, and an ecosystem of tools and domains built on the same epistemic layer.

---

## How we use this

- **Roadmap and to-do** — Features and docs that move us toward this north star get priority; work that doesn’t serve it is deprioritized or declined.
- **Scope** — When we’re unsure if something belongs, we ask: does it strengthen the epistemic layer, the format, the verifier, or the ecosystem? If not, it stays out.
- **Messaging** — We describe Chronicle in terms of defensibility, verification, and “show your work,” not truth or guarantees we don’t provide.

**← [Docs index](README.md)** | **[Story](story/README.md)** | **[Critical areas](../critical_areas/README.md)**
