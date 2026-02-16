"""
Example: Haystack RAG pipeline with Chronicle as the epistemic backend.

Run from repo root (with haystack-ai and chronicle-standard installed):

  pip install chronicle-standard haystack-ai
  PYTHONPATH=. python3 scripts/haystack_rag_chronicle.py

This builds a minimal pipeline (BM25 retriever + Chronicle writer), runs one query,
passes the retrieved documents to Chronicle as evidence and an optional claim
string, then prints defensibility. No LLM or API keys required.
"""

from __future__ import annotations

import tempfile
from pathlib import Path


def main() -> None:
    try:
        from haystack import Pipeline
        from haystack.dataclasses import Document
        from haystack.document_stores.in_memory import InMemoryDocumentStore
        from haystack.components.retrievers.in_memory import InMemoryBM25Retriever
    except ImportError as e:
        raise SystemExit(
            "This example requires haystack-ai. Install with: pip install haystack-ai"
        ) from e

    from chronicle.store.project import create_project
    from chronicle.integrations.haystack import ChronicleEvidenceWriter

    with tempfile.TemporaryDirectory(prefix="chronicle_hs_") as tmp:
        path = Path(tmp)
        create_project(path)

        document_store = InMemoryDocumentStore()
        document_store.write_documents(
            documents=[
                Document(content="The company reported revenue of $1.2M in Q1 2024."),
                Document(content="Growth was driven by enterprise contracts."),
            ]
        )

        retriever = InMemoryBM25Retriever(document_store=document_store)
        chronicle_writer = ChronicleEvidenceWriter(
            path,
            investigation_title="Haystack RAG example",
            actor_id="haystack-example",
            actor_type="tool",
        )

        pipeline = Pipeline()
        pipeline.add_component(instance=retriever, name="retriever")
        pipeline.add_component(instance=chronicle_writer, name="chronicle_writer")
        pipeline.connect("retriever.documents", "chronicle_writer.documents")

        # Run: pass query and optional claim_text (e.g. from your generator in a full RAG setup)
        result = pipeline.run(
            data={
                "retriever": {"query": "What was the revenue in Q1 2024?", "top_k": 2},
                "chronicle_writer": {"claim_text": "Revenue in Q1 2024 was $1.2M."},
            }
        )

        writer_out = result.get("chronicle_writer", {})
        documents = writer_out.get("documents", [])
        print("Retrieved documents written to Chronicle:", len(documents))

        if chronicle_writer._investigation_uid:
            session = chronicle_writer._get_session()
            claims = session.read_model.list_claims_by_type(
                investigation_uid=chronicle_writer._investigation_uid,
                include_withdrawn=False,
                limit=5,
            )
            if claims:
                claim_uid = claims[-1].claim_uid
                scorecard = session.get_defensibility_score(claim_uid)
                print("Chronicle investigation:", chronicle_writer._investigation_uid)
                print("Claim:", claim_uid)
                if scorecard:
                    print("Defensibility:", scorecard.provenance_quality)
                    print("  Corroboration:", scorecard.corroboration)
                else:
                    print("Defensibility: (no scorecard)")
            else:
                print("No claims in Chronicle.")
        else:
            print("No investigation created.")

    print("\nDone. See docs/integrations/haystack.md for more.")


if __name__ == "__main__":
    main()
