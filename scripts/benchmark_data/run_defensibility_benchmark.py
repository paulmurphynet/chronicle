"""
Run a fixed set of queries through a Chronicle-backed RAG pipeline and record defensibility per answer (D.4).

Run from repo root:

  pip install chronicle-standard
  PYTHONPATH=. python3 scripts/benchmark_data/run_defensibility_benchmark.py

  Optional: --output results.json   (default: benchmark_defensibility_results.json in repo root)
  Optional: --stdout                 (print JSON to stdout instead of writing a file)
  Optional: --mode langchain|session|auto (default: auto)

In `auto` mode, the script tries LangChain first and falls back to a pure Chronicle session flow
if langchain-core is not installed. Each query runs in its own investigation; one claim per answer;
defensibility metrics are recorded. See docs/benchmark.md and docs/eval-and-benchmarking.md.
"""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path
from typing import Any

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


def _run_with_langchain(path: Path) -> list[dict[str, Any]]:
    from chronicle.eval_metrics import defensibility_metrics_for_claim
    from chronicle.integrations.langchain import ChronicleCallbackHandler
    from langchain_core.documents import Document
    from langchain_core.language_models import BaseChatModel
    from langchain_core.messages import AIMessage
    from langchain_core.output_parsers import StrOutputParser
    from langchain_core.outputs import ChatGeneration, ChatResult
    from langchain_core.prompts import ChatPromptTemplate
    from langchain_core.retrievers import BaseRetriever
    from langchain_core.runnables import RunnableLambda, RunnablePassthrough
    from pydantic import ConfigDict

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

    results: list[dict[str, Any]] = []

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
        row: dict[str, Any] = {
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

    return results


def _run_with_session(path: Path) -> list[dict[str, Any]]:
    from chronicle.eval_metrics import defensibility_metrics_for_claim
    from chronicle.store.session import ChronicleSession

    results: list[dict[str, Any]] = []
    with ChronicleSession(path) as session:
        for query_id, question in BENCHMARK_QUERIES:
            _, inv_uid = session.create_investigation(
                f"Defensibility benchmark: {query_id}",
                actor_id="benchmark-run",
                actor_type="tool",
                investigation_key=f"benchmark_{query_id}",
            )
            row: dict[str, Any] = {
                "query_id": query_id,
                "query": question,
                "claim_uid": None,
                "investigation_uid": inv_uid,
                "metrics": None,
                "error": None,
            }
            span_uids: list[str] = []
            for i, doc in enumerate(DOCS):
                _, evidence_uid = session.ingest_evidence(
                    inv_uid,
                    doc.encode("utf-8"),
                    "text/plain",
                    original_filename=f"{query_id}_doc_{i}.txt",
                    actor_id="benchmark-run",
                    actor_type="tool",
                )
                _, span_uid = session.anchor_span(
                    inv_uid,
                    evidence_uid,
                    "text_offset",
                    {"start_char": 0, "end_char": len(doc)},
                    quote=doc[:160],
                    actor_id="benchmark-run",
                    actor_type="tool",
                )
                span_uids.append(span_uid)

            _, claim_uid = session.propose_claim(
                inv_uid,
                "Revenue in Q1 2024 was $1.2M (from context).",
                actor_id="benchmark-run",
                actor_type="tool",
            )
            row["claim_uid"] = claim_uid

            for span_uid in span_uids:
                session.link_support(
                    inv_uid,
                    span_uid,
                    claim_uid,
                    actor_id="benchmark-run",
                    actor_type="tool",
                )

            metrics = defensibility_metrics_for_claim(session, claim_uid)
            if metrics is None:
                row["error"] = "no_defensibility_score"
            else:
                row["metrics"] = metrics
            results.append(row)
    return results


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run fixed queries through Chronicle-backed benchmark flow and record defensibility."
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
    parser.add_argument(
        "--mode",
        choices=("auto", "langchain", "session"),
        default="auto",
        help="Execution mode (default: auto)",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)

    from chronicle.store.project import create_project

    execution_mode = args.mode
    with tempfile.TemporaryDirectory(prefix="chronicle_benchmark_") as tmp:
        path = Path(tmp)
        create_project(path)
        try:
            if args.mode == "langchain":
                results = _run_with_langchain(path)
            elif args.mode == "session":
                results = _run_with_session(path)
            else:
                try:
                    results = _run_with_langchain(path)
                    execution_mode = "langchain"
                except ImportError as e:
                    print(
                        f"langchain-core unavailable; falling back to session mode: {e}",
                        file=sys.stderr,
                    )
                    results = _run_with_session(path)
                    execution_mode = "session"
        except ImportError as e:
            print(json.dumps({"error": "dependency_missing", "message": str(e)}), file=sys.stderr)
            return 1

        payload: dict[str, Any] = {
            "benchmark": "run_defensibility_benchmark",
            "queries": BENCHMARK_QUERIES,
            "execution_mode": execution_mode,
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
    raise SystemExit(main(sys.argv[1:]))
