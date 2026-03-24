"""
Example: LangChain RAG with Chronicle as the epistemic backend.

Run from repo root (with langchain-core and chronicle-standard installed):

  pip install chronicle-standard langchain-core
  PYTHONPATH=. python3 scripts/langchain_rag_chronicle.py

This builds a minimal RAG chain (retriever + LLM), runs one query with the
Chronicle callback handler attached, then prints defensibility and claim UID.
"""

from __future__ import annotations

import tempfile
from pathlib import Path


def main() -> None:
    try:
        from langchain_core.documents import Document
        from langchain_core.language_models import BaseChatModel
        from langchain_core.messages import AIMessage
        from langchain_core.output_parsers import StrOutputParser
        from langchain_core.outputs import ChatGeneration, ChatResult
        from langchain_core.prompts import ChatPromptTemplate
        from langchain_core.retrievers import BaseRetriever
        from langchain_core.runnables import RunnableLambda, RunnablePassthrough
        from pydantic import ConfigDict
    except ImportError as e:
        raise SystemExit(
            "This example requires langchain-core. Install with: pip install langchain-core"
        ) from e

    from chronicle.integrations.langchain import ChronicleCallbackHandler
    from chronicle.store.project import create_project

    # In-memory retriever (no API keys)
    class MockRetriever(BaseRetriever):
        docs: list[Document]

        model_config = ConfigDict(arbitrary_types_allowed=True)

        def _get_relevant_documents(self, query: str, *, run_manager=None) -> list[Document]:
            return self.docs

    class MockLLM(BaseChatModel):
        @property
        def _llm_type(self) -> str:
            return "mock"

        def _generate(self, messages, stop=None, run_manager=None, **kwargs):
            return ChatResult(
                generations=[
                    ChatGeneration(message=AIMessage(content="Revenue in Q1 2024 was $1.2M."))
                ]
            )

    # Create a temp Chronicle project
    with tempfile.TemporaryDirectory(prefix="chronicle_lc_") as tmp:
        path = Path(tmp)
        create_project(path)

        handler = ChronicleCallbackHandler(
            path,
            investigation_title="LangChain RAG example",
            actor_id="langchain-example",
            actor_type="tool",
        )

        docs = [
            Document(page_content="The company reported revenue of $1.2M in Q1 2024."),
            Document(page_content="Growth was driven by enterprise contracts."),
        ]
        retriever = MockRetriever(docs=docs)
        prompt = ChatPromptTemplate.from_messages(
            [("human", "Answer based only on this context:\n{context}\n\nQuestion: {question}")]
        )
        llm = MockLLM()

        def format_docs(docs_list: list[Document]) -> str:
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

        # One query with handler so retriever + chain end are written to Chronicle
        result = chain.invoke(
            {"question": "What was the revenue in Q1 2024?"},
            config={"callbacks": [handler]},
        )

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
                print("Answer:", (result[:200] + "...") if len(str(result)) > 200 else result)
                if scorecard:
                    print("Defensibility:", scorecard.provenance_quality)
                    print("  Corroboration:", scorecard.corroboration)
                else:
                    print("Defensibility: (no scorecard)")
            else:
                print("No claims in Chronicle.")
        else:
            print("No investigation created.")

    print("\nDone. See docs/integrations/langchain.md for more.")


if __name__ == "__main__":
    main()
