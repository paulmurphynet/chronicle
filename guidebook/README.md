# Chronicle guidebook

The **narrative** of Chronicle: the problem we’re trying to address, why it exists, how we’re tackling it, where the challenges are, and how you can help. This guidebook is for **everyone**—contributors, partners, researchers, and anyone curious—not only software engineers.

## How to read the guidebook

- **Start with [The problem we’re solving](01-the-problem.md).** It sets the scene: why “defensibility” and “show your work” matter.
- Then read in order: **Why this problem exists**, **How we’re solving it**, **Where the challenges are**, and **How you can help**.
- If you want to go deeper on the technical side, the repo has a [Technical report](../docs/technical-report.md) and [lessons](../lessons/README.md) for developers.
- **Before relying on scores or verification,** read the [critical areas](../critical_areas/README.md): they explain what defensibility and “verified” do *not* guarantee, so the system isn’t over-trusted.

## Contents (narrative arc)

| Chapter | Title | What it covers |
|---------|--------|----------------|
| [01](01-the-problem.md) | The problem we’re solving | Why answers need to be defensible; what goes wrong when they aren’t. |
| [02](02-why-this-problem-exists.md) | Why this problem exists | Forces that created the problem: scale of content, AI, trust, and evals. |
| [03](03-how-we-are-solving-it.md) | How we’re solving it | Our approach: evidence, claims, defensibility score, .chronicle format, verifier. |
| [04](04-where-challenges-remain.md) | Where challenges remain | What’s hard, what’s incomplete, and what we’re still figuring out. |
| [05](05-how-you-can-help.md) | How you can help | Ways to contribute: code, docs, testing, feedback, sharing the story. |

## One-paragraph summary

We live in a world where **content is abundant and trust is scarce**. AI and RAG systems give answers, but it’s hard to know how well those answers are supported by evidence. **Chronicle** is our response: we don’t try to say what’s “true”—we help people see **how defensible** a claim is given the evidence and the rules they care about. We do that with a **defensibility score**, a portable **.chronicle** format, and a **verifier** so anyone can check “show your work” without running our full stack. This guidebook tells that story and invites you to be part of it.
