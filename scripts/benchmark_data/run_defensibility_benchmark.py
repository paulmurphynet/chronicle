"""
Run a fixed set of queries through a Chronicle-backed RAG pipeline and record defensibility per answer (D.4).

Run from repo root (requires chronicle-standard and langchain-core):

  pip install chronicle-standard langchain-core
  PYTHONPATH=. python3 scripts/benchmark_data/run_defensibility_benchmark.py

  Optional: --output results.json   (default: benchmark_defensibility_results.json in repo root)
  Optional: --stdout                 (print JSON to stdout instead of writing a file)

Uses the same LangChain + Chronicle pattern as the eval harness adapter. Each query runs in its own investigation; one claim per answer; defensibility metrics are recorded. See docs/benchmark.md and docs/eval-and-benchmarking.md.
"""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent

# Fixed benchmark query set: (query_id, question). Same small corpus for all (see DOCS below).
BENCHMARK_QUERIES = [
    ("q1", "What was the revenue in Q1 2024?"),
    ("q2", "What drove growth?"),
    ("q3", "Summarize the key figures from the context."),
]

# Corpus used by the mock retriever (same for all queries in this benchmark).
DOCS = [
    "The company reported revenue of $1.2M in Q1 2024.",
    "Growth was driven by enterprise contracts.",
]


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run fixed queries through Chronicle-backed RAG and record defensibility per answer."
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=REPO_ROOT / "benchmark_defensibility_results.json",
        help="Output JSON file path (default: repo root / benchmark_defensibility_results.json)",
    )
    parser.add_argument(
        "--stdout",
        action="store_true",
        help="Print JSON to stdout instead of writing to --output",
    )
    args = parser.parse_args()

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

    with tempfile.TemporaryDirectory(prefix="chronicle_benchmark_") as tmp:
        path = Path(tmp)
        create_project(path)

        documents = [Document(page_content=d) for d in DOCS]
        retriever = MockRetriever(docs=documents)
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

        results: list[dict] = []

        for query_id, question in BENCHMARK_QUERIES:
            handler = ChronicleCallbackHandler(
                path,
                investigation_title=f"Defensibility benchmark: {query_id}",
                actor_id="benchmark-run",
                actor_type="tool",
                investigation_key=f"benchmark_{query_id}",
            )

            chain.invoke(
                {"question": question},
                config={"callbacks": [handler]},
            )

            session = handler._get_session()
            inv_uid = handler._investigation_uid
            row: dict = {
                "query_id": query_id,
                "query": question,
                "claim_uid": None,
                "investigation_uid": inv_uid,
                "metrics": None,
                "error": None,
            }

            if not inv_uid:
                row["error"] = "no_investigation"
                results.append(row)
                continue

            claims = session.read_model.list_claims_by_type(
                investigation_uid=inv_uid,
                include_withdrawn=False,
                limit=5,
            )
            if not claims:
                row["error"] = "no_claim"
                results.append(row)
                continue

            claim_uid = claims[-1].claim_uid
            row["claim_uid"] = claim_uid
            metrics = defensibility_metrics_for_claim(session, claim_uid)
            if metrics is None:
                row["error"] = "no_defensibility_score"
            else:
                row["metrics"] = metrics

            results.append(row)

        payload = {
            "benchmark": "run_defensibility_benchmark",
            "queries": BENCHMARK_QUERIES,
            "results": results,
        }

        out_json = json.dumps(payload, indent=2)

        if args.stdout:
            print(out_json)
        else:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(out_json, encoding="utf-8")
            print(f"Wrote {len(results)} results to {args.output}", file=sys.stderr)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
