"""
Sample compliance report from a RAG run (B.4).

Run from repo root (requires chronicle-standard and langchain-core):

  pip install chronicle-standard langchain-core
  PYTHONPATH=. python3 scripts/compliance_report_from_rag.py

Runs one LangChain RAG flow, then generates a minimal "audit report" showing what a
compliance consumer would receive: evidence UIDs, claim UID, defensibility score,
reasoning brief path, and optional audit-export path. Writes the reasoning brief
and (optionally) the audit-export JSON to an output directory so the report
references real artifacts.
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path


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
            return ChatResult(
                generations=[
                    ChatGeneration(
                        message=AIMessage(content="Revenue in Q1 2024 was $1.2M (from context).")
                    )
                ]
            )

    with tempfile.TemporaryDirectory(prefix="chronicle_compliance_") as tmp:
        path = Path(tmp)
        create_project(path)
        report_dir = path / "compliance_report"
        report_dir.mkdir(exist_ok=True)

        handler = ChronicleCallbackHandler(
            path,
            investigation_title="RAG run for compliance sample",
            actor_id="rag-compliance-sample",
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
            print("No investigation created. Cannot generate report.")
            return

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
                from chronicle.store.commands.reasoning_brief import reasoning_brief_to_html

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
            bundle = None
            print(f"(Audit export skipped: {e})", file=__import__("sys").stderr)

        report = {
            "investigation_uid": inv_uid,
            "evidence_uids": evidence_uids,
            "claims": report_claims,
            "reasoning_brief_paths": reasoning_brief_paths,
            "audit_export_path": str(audit_export_path) if audit_export_path else None,
        }
        report_path = report_dir / "audit_report.json"
        report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

        print("=== Sample compliance audit report (from RAG run) ===\n")
        print("Investigation UID:", inv_uid)
        print("Evidence UIDs:", evidence_uids)
        print("\nClaims and defensibility:")
        for r in report_claims:
            print(f"  Claim: {r['claim_uid']} | defensibility: {r['defensibility']}")
        print("\nReasoning brief path(s):", reasoning_brief_paths or "(none)")
        if report["audit_export_path"]:
            print("Audit export path:", report["audit_export_path"])
        print("\nFull report (JSON):", str(report_path))
        print("\nDone. See docs/verticals/compliance/rag-compliance-checklist.md.")


if __name__ == "__main__":
    main()
