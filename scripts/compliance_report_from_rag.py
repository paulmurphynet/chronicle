"""
Sample compliance report from a RAG run (B.4).

Run from repo root:

  pip install chronicle-standard
  PYTHONPATH=. python3 scripts/compliance_report_from_rag.py --mode session --output-dir ./compliance_run

Runs either a LangChain-backed flow or a pure Chronicle session flow, then generates
a minimal "audit report" showing what a compliance consumer would receive: evidence UIDs,
claim UID, defensibility score, reasoning brief path, and optional audit-export path.
Writes the reasoning brief and (optionally) the audit-export JSON to an output directory
so the report references real artifacts.
"""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path
from typing import Any

DOCS = [
    "The company reported revenue of $1.2M in Q1 2024.",
    "Growth was driven by enterprise contracts.",
]

QUESTION = "What was the revenue in Q1 2024?"
ANSWER = "Revenue in Q1 2024 was $1.2M (from context)."


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate a compliance-style report from a Chronicle run."
    )
    parser.add_argument(
        "--mode",
        choices=("auto", "langchain", "session"),
        default="auto",
        help="Execution mode (default: auto)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help=(
            "Directory to persist artifacts. If omitted, a temporary directory is used and "
            "removed after run."
        ),
    )
    parser.add_argument(
        "--stdout-json",
        action="store_true",
        help="Print final report JSON to stdout.",
    )
    return parser.parse_args(argv)


def _run_session_mode(project_path: Path) -> str:
    from chronicle.store.session import ChronicleSession

    with ChronicleSession(project_path) as session:
        _, inv_uid = session.create_investigation(
            "RAG run for compliance sample",
            actor_id="rag-compliance-sample",
            actor_type="tool",
        )
        for i, doc in enumerate(DOCS):
            _, evidence_uid = session.ingest_evidence(
                inv_uid,
                doc.encode("utf-8"),
                "text/plain",
                original_filename=f"context_{i}.txt",
                actor_id="rag-compliance-sample",
                actor_type="tool",
            )
            _, span_uid = session.anchor_span(
                inv_uid,
                evidence_uid,
                "text_offset",
                {"start_char": 0, "end_char": len(doc)},
                quote=doc[:160],
                actor_id="rag-compliance-sample",
                actor_type="tool",
            )
            if i == 0:
                _, claim_uid = session.propose_claim(
                    inv_uid,
                    ANSWER,
                    actor_id="rag-compliance-sample",
                    actor_type="tool",
                )
            session.link_support(
                inv_uid,
                span_uid,
                claim_uid,
                actor_id="rag-compliance-sample",
                actor_type="tool",
            )
    return inv_uid


def _run_langchain_mode(project_path: Path) -> str:
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
            return ChatResult(generations=[ChatGeneration(message=AIMessage(content=ANSWER))])

    handler = ChronicleCallbackHandler(
        project_path,
        investigation_title="RAG run for compliance sample",
        actor_id="rag-compliance-sample",
        actor_type="tool",
    )
    docs = [Document(page_content=d) for d in DOCS]
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
        {"question": QUESTION},
        config={"callbacks": [handler]},
    )
    inv_uid = handler._investigation_uid
    if not inv_uid:
        raise RuntimeError("No investigation created by LangChain workflow")
    return inv_uid


def _build_report(
    project_path: Path, inv_uid: str, report_dir: Path
) -> tuple[dict[str, Any], Path]:
    from chronicle.store.commands.reasoning_brief import reasoning_brief_to_html
    from chronicle.store.session import ChronicleSession

    report_dir.mkdir(parents=True, exist_ok=True)
    with ChronicleSession(project_path) as session:
        evidence = session.read_model.list_evidence_by_investigation(inv_uid)
        claims = session.read_model.list_claims_by_type(
            investigation_uid=inv_uid, include_withdrawn=False, limit=10
        )

        evidence_uids = [ev.evidence_uid for ev in evidence]
        report_claims = []
        reasoning_brief_paths = []

        for c in claims:
            sc = session.get_defensibility_score(c.claim_uid)
            report_claims.append(
                {
                    "claim_uid": c.claim_uid,
                    "defensibility": sc.provenance_quality if sc else None,
                    "corroboration": sc.corroboration if sc else None,
                }
            )
            brief = session.get_reasoning_brief(c.claim_uid, limit=500)
            if brief is not None:
                safe_uid = "".join(x if x.isalnum() or x in "_-" else "_" for x in c.claim_uid)[:32]
                brief_path = report_dir / f"reasoning_brief_{safe_uid}.html"
                brief_path.write_text(reasoning_brief_to_html(brief), encoding="utf-8")
                reasoning_brief_paths.append(str(brief_path))

        audit_export_path = report_dir / "audit_export.json"
        try:
            bundle = session.get_audit_export_bundle(inv_uid, limit_claims=50)
            audit_export_path.write_text(json.dumps(bundle, indent=2), encoding="utf-8")
        except Exception as e:
            audit_export_path = None
            print(f"(Audit export skipped: {e})", file=sys.stderr)

        report = {
            "investigation_uid": inv_uid,
            "evidence_uids": evidence_uids,
            "claims": report_claims,
            "reasoning_brief_paths": reasoning_brief_paths,
            "audit_export_path": str(audit_export_path) if audit_export_path else None,
        }
        report_path = report_dir / "audit_report.json"
        report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report, report_path


def _run_once(project_path: Path, report_dir: Path, mode: str) -> tuple[dict[str, Any], Path, str]:
    from chronicle.store.project import create_project

    create_project(project_path)

    execution_mode = mode
    if mode == "langchain":
        inv_uid = _run_langchain_mode(project_path)
    elif mode == "session":
        inv_uid = _run_session_mode(project_path)
    else:
        try:
            inv_uid = _run_langchain_mode(project_path)
            execution_mode = "langchain"
        except ImportError as e:
            print(f"langchain-core unavailable; falling back to session mode: {e}", file=sys.stderr)
            inv_uid = _run_session_mode(project_path)
            execution_mode = "session"

    report, report_path = _build_report(project_path, inv_uid, report_dir)
    return report, report_path, execution_mode


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)

    if args.output_dir:
        run_root = args.output_dir.resolve()
        run_root.mkdir(parents=True, exist_ok=True)
        project_path = run_root / "project"
        report_dir = run_root / "report"
        report, report_path, execution_mode = _run_once(project_path, report_dir, args.mode)
    else:
        with tempfile.TemporaryDirectory(prefix="chronicle_compliance_") as tmp:
            run_root = Path(tmp)
            project_path = run_root / "project"
            report_dir = run_root / "report"
            report, report_path, execution_mode = _run_once(project_path, report_dir, args.mode)
            # Preserve a copy if caller wants to inspect ephemeral mode output.
            if args.stdout_json:
                pass

    output = {
        "execution_mode": execution_mode,
        "question": QUESTION,
        "report_path": str(report_path),
        "report": report,
    }

    print("=== Sample compliance audit report (from RAG run) ===\n")
    print("Investigation UID:", report["investigation_uid"])
    print("Evidence UIDs:", report["evidence_uids"])
    print("\nClaims and defensibility:")
    for r in report["claims"]:
        print(f"  Claim: {r['claim_uid']} | defensibility: {r['defensibility']}")
    print("\nReasoning brief path(s):", report["reasoning_brief_paths"] or "(none)")
    if report["audit_export_path"]:
        print("Audit export path:", report["audit_export_path"])
    print("\nFull report (JSON):", str(report_path))

    if args.stdout_json:
        print(json.dumps(output, indent=2))
    if args.output_dir is None:
        print(
            "\nNote: output directory was temporary and has been cleaned up. "
            "Use --output-dir to persist artifacts."
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
