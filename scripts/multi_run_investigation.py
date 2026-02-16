"""
Example: Multiple RAG queries into one Chronicle investigation (multi-run accumulation).

Run from repo root (requires chronicle-standard and langchain-core):

  pip install chronicle-standard langchain-core
  PYTHONPATH=. python3 scripts/multi_run_investigation.py

Creates one investigation (via investigation_key), runs three different queries
through the same LangChain RAG chain, then prints evidence and claims accumulating
and defensibility over the combined set. Demonstrates the "append to investigation"
pattern for long-lived case files.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

INVESTIGATION_KEY = "multi_run_demo"
SAMPLE_DOCS = [
    "The company reported revenue of $1.2M in Q1 2024.",
    "Growth was driven by enterprise contracts.",
    "Enterprise segment grew 40% year-over-year.",
]
QUESTIONS = [
    "What was the revenue in Q1 2024?",
    "What drove growth?",
    "How did enterprise perform?",
]


def main() -> None:
    try:
        from langchain_core.documents import Document
        from langchain_core.output_parsers import StrOutputParser
        from langchain_core.prompts import ChatPromptTemplate
        from langchain_core.retrievers import BaseRetriever
        from langchain_core.runnables import RunnableLambda, RunnablePassthrough
        from langchain_core.language_models import BaseChatModel
        from langchain_core.messages import AIMessage
        from langchain_core.outputs import ChatGeneration, ChatResult
        from pydantic import ConfigDict
    except ImportError as e:
        raise SystemExit(
            "This example requires langchain-core. Install with: pip install langchain-core"
        ) from e

    from chronicle.store.project import create_project
    from chronicle.integrations.langchain import ChronicleCallbackHandler

    class MockRetriever(BaseRetriever):
        docs: list[Document]
        model_config = ConfigDict(arbitrary_types_allowed=True)

        def _get_relevant_documents(self, query: str, *, run_manager=None) -> list[Document]:
            return self.docs

    class MockLLM(BaseChatModel):
        model_config = ConfigDict(arbitrary_types_allowed=True)

        @property
        def _llm_type(self) -> str:
            return "mock"

        def _generate(self, messages, stop=None, run_manager=None, **kwargs):
            # Simple stub answer so we get a claim per query
            return ChatResult(
                generations=[
                    ChatGeneration(
                        message=AIMessage(
                            content="Answer based on the retrieved context (mock)."
                        )
                    )
                ]
            )

    with tempfile.TemporaryDirectory(prefix="chronicle_multi_") as tmp:
        path = Path(tmp)
        create_project(path)

        handler = ChronicleCallbackHandler(
            path,
            investigation_key=INVESTIGATION_KEY,
            investigation_title="Multi-run investigation example",
            actor_id="langchain-multi",
            actor_type="tool",
        )

        docs = [Document(page_content=t) for t in SAMPLE_DOCS]
        retriever = MockRetriever(docs=docs)
        prompt = ChatPromptTemplate.from_messages(
            [("human", "Answer based only on this context:\n{context}\n\nQuestion: {question}")]
        )
        llm = MockLLM()

        def format_docs(docs_list: list) -> str:
            return "\n\n".join(d.page_content for d in docs_list)

        chain = (
            RunnablePassthrough.assign(context=lambda x: retriever.invoke(x["question"]))
            | RunnableLambda(
                lambda x: {"context": format_docs(x["context"]), "question": x["question"]}
            )
            | prompt
            | llm
            | StrOutputParser()
        )

        # Run multiple queries; each appends evidence and one claim to the same investigation
        for i, question in enumerate(QUESTIONS):
            result = chain.invoke(
                {"question": question},
                config={"callbacks": [handler]},
            )
            print(f"Query {i + 1}: {question[:50]}{'...' if len(question) > 50 else ''}")
            print(f"  Answer (snippet): {str(result)[:60]}...")
        print()

        # Summary: one investigation, accumulated evidence and claims
        session = handler._get_session()
        inv_uid = handler._investigation_uid
        if not inv_uid:
            print("No investigation created.")
            return

        claims = session.read_model.list_claims_by_type(
            investigation_uid=inv_uid,
            include_withdrawn=False,
            limit=20,
        )
        evidence = session.read_model.list_evidence_by_investigation(inv_uid)

        print("=== Multi-run investigation: combined set ===")
        print("Investigation:", inv_uid)
        print("Evidence items (accumulated):", len(evidence))
        print("Claims (one per query):", len(claims))
        for i, c in enumerate(claims):
            sc = session.get_defensibility_score(c.claim_uid)
            support = session.read_model.get_support_for_claim(c.claim_uid)
            print(
                f"  Claim {i + 1}: {c.claim_uid} | defensibility: {sc.provenance_quality if sc else 'N/A'} | support links: {len(support)}"
            )

    print("\nDone. See docs/integrations (Appending to an existing investigation) and integrating-with-chronicle.md (One project, many stacks).")


if __name__ == "__main__":
    main()
