# The Chronicle story

This is the **narrative** of Chronicle: the problem we’re addressing, why it exists, how we’re tackling it, where the challenges are, and how you can help. It’s written for **everyone**—contributors, partners, researchers, and anyone curious about how we evaluate and trust answers—not only software engineers.

---

## Mission

Our **mission** is to make defensibility a practical, verifiable part of how people evaluate and trust answers. We don't try to say what's "true"—we help people see **how defensible** a claim is given the evidence and the rules they care about, and we give them a way to **verify** that the work was actually shown.

---

## Vision

Our **vision** is a world where more answers can show their work and more people can check it. Defensibility can become a common metric in RAG and evals; the .chronicle format and verifier make "show your work" something you can verify (the package is well-formed), not just promise. Adoption means eval frameworks, labs, and tooling can use defensibility and the portable format—so the feedback loop (eval → improve → eval) better reflects evidence-backed answers.

---

## Who this is for

- **You care about trust and evidence.** You want answers that show their work, and you want a way to check that the work was actually done.
- **You build or evaluate RAG, search, or AI systems.** You’re looking for a defensibility metric and a portable format that fits into pipelines and evals.
- **You work in fact-checking, provenance, or compliance.** You need to link claims to evidence and to external systems without locking into a single vendor.
- **You’re new to Chronicle.** You want the big picture before diving into the [technical report](../docs/technical-report.md) or the [developer lessons](../lessons/README.md).

If that sounds like you, start with [Chapter 01: The problem we’re solving](01-the-problem.md) and read in order.

---

## What you’ll get from reading it

By the end you’ll understand:

- **Why defensibility matters** — What goes wrong when answers aren’t backed by visible evidence, and what we mean (and don’t mean) by “defensibility.”
- **Why the problem is here to stay** — The forces (scale, AI/RAG, trust, evals) that made “show your work” both essential and under-served.
- **How Chronicle addresses it** — Evidence and claims, a defensibility score, a portable .chronicle format, a verifier (with clear [verification guarantees](../docs/verification-guarantees.md)), and how we fit into your ecosystem: one-command RAG path, standalone scorer, POST /score (scorer-as-a-service), optional API and adapters, optional link rationale, defeater type, source reliability notes, epistemic stance, policy rationale, and Neo4j deduplication, and provenance recording.
- **What’s hard and what we don’t do** — Honest limits so you don’t over-trust the score or the verifier. The [critical areas](../critical_areas/README.md) spell these out.
- **How you can help** — Concrete ways to contribute code, docs, feedback, or simply spread the story.

---

## How to read the story

1. **Read in order.** [01](01-the-problem.md) → [02](02-why-this-problem-exists.md) → [03](03-how-we-are-solving-it.md) → [04](04-where-challenges-remain.md) → [05](05-how-you-can-help.md) → [06](06-epistemology-scope-tables.md). The chapters build on each other.
2. **On GitHub:** Each chapter has **← Previous | Index | Next →** at the bottom (chapter 06 has **End of story** instead of Next) so you can move without returning here.
3. **Before you rely on scores or verification,** read the [critical areas](../critical_areas/README.md). They spell out what defensibility and “verified” do *not* guarantee, so the system isn’t over-trusted.
4. **For technical depth,** use the [docs](../docs/README.md) and [lessons](../lessons/README.md). The story stays high-level; contracts, schemas, and code live there.

---

## Contents

| Chapter | Title | What it covers |
|--------|--------|----------------|
| [01](01-the-problem.md) | The problem we’re solving | Why answers need to be defensible; what goes wrong when they aren’t; what we mean by “defensibility.” |
| [02](02-why-this-problem-exists.md) | Why this problem exists | The forces that created the problem: scale of content, AI and RAG, trust and verification, and evals. |
| [03](03-how-we-are-solving-it.md) | How we’re solving it | Evidence, claims, defensibility score, .chronicle format, verifier, and fitting into your ecosystem. |
| [04](04-where-challenges-remain.md) | Where challenges remain | Adoption, what’s done and what’s left, scope and limits, and growing the ecosystem. |
| [05](05-how-you-can-help.md) | How you can help | Ways to contribute: code, docs, testing, feedback, sharing the story. |
| [06](06-epistemology-scope-tables.md) | Epistemology: what we implement and what we don’t | Canonical tables: what Chronicle implements (and why) and what we do not implement (and why not). |

**Where we're headed:** [North star](../docs/north-star.md) — Chronicle's long-term direction (shared infrastructure, one model from early draft to auditable package, ecosystem). Use it to guide roadmap and scope.

---

## One paragraph

We live in a world where **content is abundant and trust is scarce**. AI and RAG systems give answers, but it’s hard to know how well those answers are supported by evidence. **Chronicle** is our response: we don’t try to say what’s “true”—we help people see **how defensible** a claim is given the evidence and the rules they care about. We do that with a **defensibility score**, a portable **.chronicle** format, and a **verifier** so anyone can check “show your work” without running our full stack. This document tells that story and invites you to be part of it.
