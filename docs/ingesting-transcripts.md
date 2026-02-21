# Ingesting transcripts (e.g. Lizzie Borden inquest) from CSV

You have a transcript in a structured CSV format. This doc explains ingestion readiness and the tools required.

For rationale and evaluation framing specific to the Lizzie dataset, see [Lizzie Borden case study](case-study-lizzie-borden.md).

---

## What Chronicle needs

1. **Evidence** — Each piece of source text (e.g. a statement, a Q&A turn) as an evidence item. We can ingest text via `session.ingest_evidence(inv_uid, text.encode("utf-8"), "text/plain")`.
2. **Spans** — Optional but useful: character ranges inside evidence so we can say "this claim is supported by this span." For a transcript, each row can be one evidence item; then the span is the whole content (0 to len), or we store one big evidence (whole transcript) and many spans (one per statement).
3. **Claims** — Assertions we care about. For a transcript, the minimal approach: each statement is also treated as a claim (e.g. "Witness said: …"). Then we can link that evidence span to that claim. So the graph has "who said what" and we can later add tensions when two claims conflict.
4. **Attribution** — We can set `actor_id` when ingesting or proposing (e.g. speaker name) so the graph has "Lizzie Borden" as the actor for her statements.
5. **Tensions** — When two claims contradict (e.g. two witnesses disagree), we call `declare_tension`. That can be manual, or we can use an LLM/heuristic to suggest conflicts.

---

## How far off

| Piece | Status | Notes |
|-------|--------|--------|
| CSV → evidence | Ready | Script below: read CSV, create investigation, ingest each row (or each logical chunk) as evidence. Column names configurable. |
| Spans | Ready | One row = one evidence → one span (whole content). Or one big evidence + spans per row if you prefer. |
| Claims per statement | Ready | For each row: propose_claim(row_text) and link_support(span, claim). So "statement as claim" is in the box. |
| Speaker as actor | Ready | If your CSV has a speaker column, set `actor_id=speaker` when ingesting/proposing so the graph has attribution. |
| Export to .chronicle / Aura | Ready | Same as synthetic pipeline: export investigation, run ingest_chronicle_to_aura. |
| Factual claim extraction | Optional | "From this statement, what factual claims are made?" (e.g. "I was in the barn at 11am") → separate claims with links. Needs an LLM pass or manual curation. |
| Contradiction / tension detection | Optional | Compare claims across witnesses and suggest tensions. We have contradiction tooling (LLM-based); could be run over transcript-derived claims. |

So: ingesting the transcript as evidence and as statement-level claims, with speaker attribution, is one script away. Factual extraction and automatic tension detection are the next step if you want them.

---

## Tools you need

1. **CSV → Chronicle loader** — A script that:
   - Reads your CSV (column names/configurable).
   - Creates a Chronicle project and one investigation (e.g. "Lizzie Borden inquest").
   - For each row: ingest evidence (row text), anchor one span (whole text), propose one claim (same text or "Speaker: text"), link_support(span, claim). If you have a speaker column, use it as `actor_id`.
   - Exports the investigation to a `.chronicle` file.
   - You run `ingest_chronicle_to_aura.py` on that file to push to the graph.

2. **Optional: factual claim extraction** — An LLM (or manual) pass over segments: "What factual claims are asserted here?" then create claims and link to the relevant span(s). Would need character offsets or row IDs to create spans.

3. **Optional: tension detection** — Run contradiction/tension detection over the set of claims (e.g. by witness pair or by topic) and call `declare_tension` for suggested conflicts. Our existing tools could be adapted.

4. **No new infra** — Python stdlib `csv` (or pandas), the Chronicle session API, and your existing Aura pipeline. No new services.

---

## CSV shape we assume

The script below assumes your CSV has at least:

- A text column (the statement or line).
- Optional: speaker (or similar) for attribution.
- Optional: line, page, or date for ordering or metadata.

You pass column names via flags so we don’t hardcode "Lizzie Borden"–specific headers.

---

## Next step

Use `scripts/ingest_transcript_csv.py`. Run it on your CSV; it creates a project, loads evidence and statement-level claims, exports `.chronicle`. Then ingest that `.chronicle` into your graph with `ingest_chronicle_to_aura.py`.

Example (Lizzie Borden inquest; your column names may differ):

```bash
# If your CSV has columns "text" and "speaker":
PYTHONPATH=. python3 scripts/ingest_transcript_csv.py /path/to/lizzie_inquest.csv \
  --text-col "text" --speaker-col "speaker" \
  --title "Lizzie Borden inquest" --out lizzie_borden.chronicle

# If your CSV has "testimony" and "speaker" (e.g. Lizzie Borden inquest):
PYTHONPATH=. python3 scripts/ingest_transcript_csv.py test_data/lb_inquest/inquest.csv \
  --text-col "testimony" --speaker-col "speaker" \
  --title "Lizzie Borden inquest" --out test_data/lb_inquest/lizzie_borden.chronicle

# Then push to Aura (or a dedicated project):
CHRONICLE_GRAPH_PROJECT=test_data/lb_inquest/neo4j_project PYTHONPATH=. python3 scripts/ingest_chronicle_to_aura.py test_data/lb_inquest/lizzie_borden.chronicle
```

To suggest tensions (heuristic or LLM) after ingesting, use `scripts/suggest_tensions_with_llm.py`; see [Using Ollama locally](using-ollama-locally.md). Options: `--encoding`, `--delimiter` (e.g. `--delimiter '\\t'` for tab). See `scripts/ingest_transcript_csv.py --help`.

If you want one big document with many spans instead of one row = one evidence, we can add a second mode to the script.
