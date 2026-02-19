# Case Study: Lizzie Borden Inquest (Data Quality and Trust Evaluation)

This case study explains why Chronicle includes a historical inquest transcript dataset (`test_data/lb_inquest/inquest.csv`) and how to use it responsibly.

## Scope and tone

This project does not use this material for narrative retelling or sensational treatment of a homicide case. The purpose is technical: evaluate whether evidence-linked reasoning performs better than unsupported model output.

## Why this dataset is useful

### 1. Controlled primary-source corpus

The inquest transcript provides a bounded corpus with explicit speaker turns and stable ordering (`id` sequence). That structure is useful for:

1. Tracking who made each statement.
2. Tracking when each statement appears in the record.
3. Evaluating whether later claims are supported by earlier evidence.

### 2. Sworn-testimony focus

For this case study, Chronicle scopes analysis to the inquest transcript as the primary sworn-testimony source for Lizzie Borden in the project dataset. This keeps evaluation anchored to a clearly defined evidentiary record instead of mixed secondary retellings.

### 3. Good stress test for modern LLM trust

General-purpose LLMs are trained on broad web corpora that include conflicting summaries, folklore, and repeated inaccuracies about historical cases. This creates a realistic trust problem:

1. The model may produce fluent but weakly supported statements.
2. Citations may be missing, vague, or disconnected from claims.
3. Temporal sequencing ("who knew what, when") is often inconsistent.

Chronicle is designed for exactly this gap: not deciding ultimate truth, but exposing support quality, contradictions, and provenance quality claim-by-claim.

## What we are and are not claiming

Chronicle does not claim to resolve the case or establish legal truth. In this context, Chronicle provides:

1. Structured claim/evidence linkage.
2. Defensibility metrics over that structure.
3. Reproducible artifacts (`.chronicle`) that others can verify.

## Recommended evaluation design

Use this dataset as a comparative benchmark:

1. Baseline: ask an LLM case questions without Chronicle context.
2. Chronicle run: ingest transcript rows into Chronicle and require claim-evidence linkage.
3. Compare:
   - Unsupported assertion rate.
   - Citation quality (specific and checkable vs generic).
   - Temporal consistency (order of testimony and knowledge-state transitions).
   - Contradiction handling (whether tensions are surfaced and tracked).

## Data handling guidance

1. Keep language factual and neutral.
2. Avoid speculative or sensational framing in prompts and docs.
3. Distinguish direct transcript statements from downstream interpretation.
4. Treat this as an evidence-quality benchmark, not a historical adjudication tool.

## How this maps to current tooling

1. Ingest CSV transcript: `scripts/ingest_transcript_csv.py`
2. Export/import and verification: `.chronicle` + `chronicle-verify`
3. Optional graph projection for analysis: Neo4j sync/export tooling
4. Optional tension suggestion workflows: heuristic or LLM-assisted scripts

See also:

1. [Ingesting transcripts](ingesting-transcripts.md)
2. [Chronicle file format](chronicle-file-format.md)
3. [Trust metrics](trust-metrics.md)
4. [Verification guarantees](verification-guarantees.md)
