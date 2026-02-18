# Quiz 09: Epistemic tools

**Lesson:** [09-epistemic-tools.md](../09-epistemic-tools.md)

Answer these after reading the lesson and the tools. Try not to peek at the answer key until you've written your answers.

---

## Questions

1. What does the **decomposer** do? (One sentence.) What are the two modes (heuristic vs LLM)?

2. What does **suggest_tensions_heuristic** take as input and return? (Types or shape.)

3. Which **environment variable** must be set to use the LLM in Chronicle tools (decomposer, contradiction, type inference)?

4. What is the **default LLM provider** and **default model** in Chronicle? (So you can run “for free” locally.)

5. Which script runs **tension suggestion** (heuristic or LLM) over a project and can **apply** the suggested tensions? What flag applies them?

---

## Answer key

1. The **decomposer** determines whether a claim is one atomic fact or several, and if several, suggests split texts. **Heuristic** mode: split on conjunctions/sentence boundaries. **LLM** mode: ask the model to decide and suggest splits.

2. **Input**: a list of **(claim_uid, claim_text)** pairs. **Return**: a list of **TensionSuggestion** (claim_a_uid, claim_b_uid, suggested_tension_kind, confidence, rationale).

3. **CHRONICLE_LLM_ENABLED=1** (or true). Without it, the LLM path is not used; heuristics are used where available.

4. **Provider**: **ollama**. **Model**: **qwen2.5:7b** (default in llm_config). Base URL default is http://127.0.0.1:11434. So local Ollama with no API key.

5. **scripts/suggest_tensions_with_llm.py**. Flag **--apply** declares each suggested tension in the project (session.declare_tension).

---

**← Previous:** [quiz-08-cli](quiz-08-cli.md) | **Index:** [Quizzes](README.md) | **Next →:** [quiz-10-export-import-neo4j](quiz-10-export-import-neo4j.md)
