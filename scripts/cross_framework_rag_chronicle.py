"""
Example: Same question through two RAG frameworks (LangChain + LlamaIndex) into one Chronicle project.

Run from repo root (requires chronicle-standard, langchain-core, and llama-index-core):

  pip install chronicle-standard langchain-core llama-index-core
  PYTHONPATH=. python3 scripts/cross_framework_rag_chronicle.py

Both runs use the same investigation_key so evidence and claims from both frameworks
land in one investigation. The script then lists claims and defensibility for each,
showing that Chronicle is the shared epistemic layer regardless of framework.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

QUESTION = "What was the revenue in Q1 2024?"
INVESTIGATION_KEY = "cross_framework_demo"
SAMPLE_DOCS = [
    "The company reported revenue of $1.2M in Q1 2024.",
    "Growth was driven by enterprise contracts.",
]


def run_langchain(path: Path) -> tuple[str | None, str]:
    """Run LangChain RAG; return (claim_uid or None, answer_snippet)."""
    try:
        from langchain_core.documents import Document
        from langchain_core.output_parsers import StrOutputParser
        from langchain_core.prompts import ChatPromptTemplate
        from langchain_core.runnables import RunnableLambda, RunnablePassthrough
        from langchain_core.language_models import BaseChatModel
        from langchain_core.messages import AIMessage
        from langchain_core.outputs import ChatGeneration, ChatResult
        from pydantic import ConfigDict
    except ImportError:
        return None, "(langchain-core not installed)"

    from chronicle.integrations.langchain import ChronicleCallbackHandler

    class MockRetriever:
        def __init__(self, docs: list[Document]):
            self.docs = docs

        def invoke(self, query: str) -> list[Document]:
            return self.docs

    class MockLLM(BaseChatModel):
        model_config = ConfigDict(arbitrary_types_allowed=True)

        @property
        def _llm_type(self) -> str:
            return "mock"

        def _generate(self, messages, stop=None, run_manager=None, **kwargs):
            return ChatResult(
                generations=[ChatGeneration(message=AIMessage(content="Revenue in Q1 2024 was $1.2M."))]
            )

    handler = ChronicleCallbackHandler(
        path,
        investigation_key=INVESTIGATION_KEY,
        investigation_title="Cross-framework RAG",
        actor_id="langchain",
        actor_type="tool",
    )
    docs = [Document(page_content=t) for t in SAMPLE_DOCS]
    retriever = MockRetriever(docs)
    prompt = ChatPromptTemplate.from_messages(
        [("human", "Answer based only on this context:\n{context}\n\nQuestion: {question}")]
    )
    llm = MockLLM()

    def format_docs(docs_list: list) -> str:
        return "\n\n".join(d.page_content for d in docs_list)

    from langchain_core.runnables import RunnablePassthrough

    chain = (
        RunnablePassthrough.assign(context=lambda x: retriever.invoke(x["question"]))
        | RunnableLambda(
            lambda x: {"context": format_docs(x["context"]), "question": x["question"]}
        )
        | prompt
        | llm
        | StrOutputParser()
    )
    result = chain.invoke(
        {"question": QUESTION},
        config={"callbacks": [handler]},
    )
    session = handler._get_session()
    claims = session.read_model.list_claims_by_type(
        investigation_uid=handler._investigation_uid,
        include_withdrawn=False,
        limit=10,
    )
    claim_uid = claims[-1].claim_uid if claims else None
    return claim_uid, (str(result)[:120] if result else "")


def run_llamaindex(path: Path) -> tuple[str | None, str]:
    """Run LlamaIndex RAG; return (claim_uid or None, answer_snippet)."""
    try:
        from llama_index.core import Document, VectorStoreIndex
        from llama_index.core.callbacks import CallbackManager
        from llama_index.core.embeddings import MockEmbedding
        from llama_index.core.llms import MockLLM
        from llama_index.core import Settings
    except ImportError:
        return None, "(llama-index-core not installed)"

    from chronicle.integrations.llamaindex import ChronicleCallbackHandler

    Settings.embed_model = MockEmbedding(embed_dim=64)
    Settings.llm = MockLLM()
    handler = ChronicleCallbackHandler(
        path,
        investigation_key=INVESTIGATION_KEY,
        investigation_title="Cross-framework RAG",
        actor_id="llamaindex",
        actor_type="tool",
    )
    callback_manager = CallbackManager([handler])
    docs = [Document(text=t) for t in SAMPLE_DOCS]
    index = VectorStoreIndex.from_documents(
        docs,
        callback_manager=callback_manager,
        show_progress=False,
    )
    query_engine = index.as_query_engine()
    response = query_engine.query(QUESTION)
    answer = str(response) if response else ""
    session = handler._get_session()
    claims = session.read_model.list_claims_by_type(
        investigation_uid=handler._investigation_uid,
        include_withdrawn=False,
        limit=10,
    )
    claim_uid = claims[-1].claim_uid if claims else None
    return claim_uid, (answer[:120] if answer else "")


def main() -> None:
    from chronicle.store.project import create_project

    with tempfile.TemporaryDirectory(prefix="chronicle_cross_") as tmp:
        path = Path(tmp)
        create_project(path)

        print("Question (same for both):", QUESTION)
        print("Investigation key:", INVESTIGATION_KEY)
        print()

        # Run LangChain first
        print("--- LangChain ---")
        lc_claim_uid, lc_answer = run_langchain(path)
        print("Answer:", lc_answer)
        print("Claim UID:", lc_claim_uid or "(none)")
        print()

        # Run LlamaIndex second (same investigation via key)
        print("--- LlamaIndex ---")
        li_claim_uid, li_answer = run_llamaindex(path)
        print("Answer:", li_answer)
        print("Claim UID:", li_claim_uid or "(none)")
        print()

        # Summary from Chronicle (one investigation, multiple claims)
        from chronicle.store.session import ChronicleSession

        session = ChronicleSession(path)
        invs = session.read_model.list_investigations()
        if not invs:
            print("No investigation in Chronicle.")
            return
        inv = invs[-1]
        inv_uid = inv.investigation_uid
        claims = session.read_model.list_claims_by_type(
            investigation_uid=inv_uid,
            include_withdrawn=False,
            limit=20,
        )
        evidence = session.read_model.list_evidence_by_investigation(inv_uid)

        print("=== Chronicle: one investigation, both frameworks ===")
        print("Investigation:", inv_uid)
        print("Claims in this investigation:", len(claims))
        print("Evidence items:", len(evidence))
        for i, c in enumerate(claims):
            sc = session.get_defensibility_score(c.claim_uid)
            support = session.read_model.get_support_for_claim(c.claim_uid)
            print(f"  Claim {i+1}: {c.claim_uid} | defensibility: {sc.provenance_quality if sc else 'N/A'} | support links: {len(support)}")

    print("\nDone. See docs/integrations/README.md and 'One investigation per key' in integrating-with-chronicle.md.")


if __name__ == "__main__":
    main()
