"""
Example: LlamaIndex RAG with Chronicle as the epistemic backend.

Run from repo root (with llama-index-core and chronicle-standard installed):

  pip install chronicle-standard llama-index-core
  PYTHONPATH=. python3 scripts/llamaindex_rag_chronicle.py

This builds a small VectorStoreIndex, runs one query with the Chronicle callback
handler attached, then prints defensibility and claim UID from Chronicle.
"""

from __future__ import annotations

import tempfile
from pathlib import Path


def main() -> None:
    try:
        from llama_index.core import VectorStoreIndex
        from llama_index.core.callbacks import CallbackManager
    except ImportError as e:
        raise SystemExit(
            "This example requires llama-index-core. Install with: pip install llama-index-core"
        ) from e

    from chronicle.store.project import create_project
    from chronicle.integrations.llamaindex import ChronicleCallbackHandler

    # Create a temp Chronicle project
    with tempfile.TemporaryDirectory(prefix="chronicle_llama_") as tmp:
        path = Path(tmp)
        create_project(path)

        # Handler: write retrievals and response to Chronicle
        handler = ChronicleCallbackHandler(
            path,
            investigation_title="LlamaIndex RAG example",
            actor_id="llamaindex-example",
            actor_type="tool",
        )
        callback_manager = CallbackManager([handler])

        # Minimal index from in-memory documents (MockEmbedModel = no API key required)
        from llama_index.core import Document, Settings
        from llama_index.core.embeddings import MockEmbedding
        from llama_index.core.llms import MockLLM

        Settings.embed_model = MockEmbedding(embed_dim=64)
        Settings.llm = MockLLM()
        docs = [
            Document(text="The company reported revenue of $1.2M in Q1 2024."),
            Document(text="Growth was driven by enterprise contracts."),
        ]
        index = VectorStoreIndex.from_documents(
            docs,
            callback_manager=callback_manager,
            show_progress=False,
        )
        # Use the same callback manager so retrieve + synthesize events reach Chronicle
        query_engine = index.as_query_engine()

        # One query: retrieval + synthesis will be written to Chronicle
        response = query_engine.query("What was the revenue in Q1 2024?")
        answer = str(response) if response else ""

        # Read back from Chronicle: get the latest claim and defensibility
        session = handler._get_session()
        inv_uid = handler._investigation_uid
        if inv_uid:
            claims = session.read_model.list_claims_by_type(
                investigation_uid=inv_uid,
                include_withdrawn=False,
                limit=5,
            )
            if claims:
                claim_uid = claims[-1].claim_uid
                scorecard = session.get_defensibility_score(claim_uid)
                print("Chronicle investigation:", inv_uid)
                print("Claim:", claim_uid)
                print("Answer:", answer[:200] + ("..." if len(answer) > 200 else ""))
                if scorecard:
                    print("Defensibility:", scorecard.provenance_quality)
                    print("  Corroboration:", scorecard.corroboration)
                else:
                    print("Defensibility: (no scorecard)")
            else:
                print("No claims in Chronicle (handler may not have received SYNTHESIZE).")
        else:
            print("No investigation created.")

    print("\nDone. See docs/integrations/llamaindex.md for more.")


if __name__ == "__main__":
    main()
