# Why this problem exists

The need for defensibility didn’t come out of nowhere. Several forces pushed it to the front.

---

## Scale of content and sources

There’s more information available than any person or team can fully absorb or validate. Answers often pull from many sources—documents, databases, APIs—and the path from “raw source” to “final answer” is long and opaque. At that scale, trust can’t rest on “I read everything”; it has to rest on **structure**: evidence, links, and a way to see how the answer was built.

---

## AI and RAG in the loop

AI systems and RAG (retrieval-augmented generation) pipelines produce answers by combining retrieval and generation. That’s powerful, but it makes the old question—“where did this come from?”—harder. The model doesn’t “cite” the way a human would unless we build that in. So we have to **design** for defensibility: record evidence, attach it to claims, and score how well the claim is supported. Without that, we’re back to trusting the output with no way to verify the work.

---

## Trust is scarce; verification is rare

In many domains—journalism, legal, compliance, research—trust is earned by showing your work and letting others check it. But most tools don’t make that first-class. They optimize for producing content, not for producing **auditable reasoning**. So the gap grows: more content, same or less ability to verify. Defensibility is our way of making “show your work” something you can actually **measure and verify**.

---

## Evals that don’t reward defensibility

Evaluation drives behavior. If evals only measure accuracy, speed, or relevance, systems optimize for those. If we want systems to **improve** at being defensible, we need evals that **include** defensibility. Today that’s missing in most pipelines—so the problem persists partly because the feedback loop (eval → improve → eval) doesn’t yet treat defensibility as an explicit signal. Together, scale, AI/RAG, trust, and evals make defensibility both essential and under-served.

---

**← Previous:** [01 — The problem](01-the-problem.md) | **Index:** [Story](README.md) | **Next →:** [03 — How we're solving it](03-how-we-are-solving-it.md)
