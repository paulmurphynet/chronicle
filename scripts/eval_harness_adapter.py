"""
Eval harness adapter: run one RAG pipeline with Chronicle and output claim_uid + metrics (D.2).

Run from repo root (requires chronicle-standard and langchain-core):

  pip install chronicle-standard langchain-core
  PYTHONPATH=. python3 scripts/eval_harness_adapter.py

Runs one LangChain RAG flow with the Chronicle callback handler, reads the
resulting claim UID and defensibility score, and prints a single JSON object
to stdout with claim_uid and the stable metrics (provenance_quality,
corroboration, contradiction_status, optional knowability). Eval frameworks
can run this script and parse the JSON as the hook for recording
defensibility per run. See docs/defensibility-metrics-schema.md.
"""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path


def main() -> int:
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
        print(json.dumps({"error": "langchain_core_required", "message": str(e)}), file=sys.stderr)
        return 1

    from chronicle.store.project import create_project
    from chronicle.integrations.langchain import ChronicleCallbackHandler
    from chronicle.eval_metrics import defensibility_metrics_for_claim

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
            return ChatResult(
                generations=[
                    ChatGeneration(
                        message=AIMessage(content="Revenue in Q1 2024 was $1.2M (from context).")
                    )
                ]
            )

    with tempfile.TemporaryDirectory(prefix="chronicle_eval_") as tmp:
        path = Path(tmp)
        create_project(path)

        handler = ChronicleCallbackHandler(
            path,
            investigation_title="Eval harness adapter run",
            actor_id="eval-adapter",
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

        chain.invoke(
            {"question": "What was the revenue in Q1 2024?"},
            config={"callbacks": [handler]},
        )

        session = handler._get_session()
        inv_uid = handler._investigation_uid
        if not inv_uid:
            out = {"claim_uid": None, "error": "no_investigation"}
            print(json.dumps(out))
            return 0

        claims = session.read_model.list_claims_by_type(
            investigation_uid=inv_uid,
            include_withdrawn=False,
            limit=5,
        )
        if not claims:
            out = {"claim_uid": None, "error": "no_claim", "investigation_uid": inv_uid}
            print(json.dumps(out))
            return 0

        claim_uid = claims[-1].claim_uid
        metrics = defensibility_metrics_for_claim(session, claim_uid)
        if metrics is None:
            out = {"claim_uid": claim_uid, "error": "no_defensibility_score", "metrics": None}
        else:
            out = metrics
        print(json.dumps(out))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
