from __future__ import annotations

import os
import time
from pathlib import Path
from typing import TypedDict

import pytest
from chronicle.store.neo4j_sync import sync_project_to_neo4j
from chronicle.store.project import create_project
from chronicle.store.session import ChronicleSession

try:
    from neo4j import GraphDatabase  # type: ignore[import-not-found]
except ImportError:
    pytest.skip(
        "neo4j Python driver not installed. Install with -e '.[neo4j]' to run live Neo4j tests.",
        allow_module_level=True,
    )

pytestmark = pytest.mark.neo4j_live


class Neo4jConfig(TypedDict):
    uri: str
    user: str
    password: str
    database: str | None


def _truthy(value: str) -> bool:
    return value.strip().lower() in {"1", "true", "yes"}


def _session_kwargs(cfg: Neo4jConfig) -> dict[str, str]:
    if cfg["database"]:
        return {"database": cfg["database"]}
    return {}


def _with_driver(cfg: Neo4jConfig):
    return GraphDatabase.driver(cfg["uri"], auth=(cfg["user"], cfg["password"]))


def _clear_graph(cfg: Neo4jConfig) -> None:
    driver = _with_driver(cfg)
    try:
        with driver.session(**_session_kwargs(cfg)) as session:
            session.run("MATCH (n) DETACH DELETE n")
    finally:
        driver.close()


def _count_nodes(cfg: Neo4jConfig, label: str) -> int:
    driver = _with_driver(cfg)
    try:
        with driver.session(**_session_kwargs(cfg)) as session:
            row = session.run(f"MATCH (n:{label}) RETURN count(n) AS c").single()
            assert row is not None
            return int(row["c"])
    finally:
        driver.close()


def _count_relationships(cfg: Neo4jConfig, rel_type: str) -> int:
    driver = _with_driver(cfg)
    try:
        with driver.session(**_session_kwargs(cfg)) as session:
            row = session.run(f"MATCH ()-[r:{rel_type}]->() RETURN count(r) AS c").single()
            assert row is not None
            return int(row["c"])
    finally:
        driver.close()


def _supports_stats(cfg: Neo4jConfig) -> tuple[int, int, int]:
    driver = _with_driver(cfg)
    try:
        with driver.session(**_session_kwargs(cfg)) as session:
            row = session.run(
                """
                MATCH ()-[r:SUPPORTS]->()
                RETURN
                  count(r) AS edge_count,
                  count(DISTINCT r.link_uid) AS distinct_link_uids,
                  sum(CASE WHEN r.retracted_at IS NULL THEN 0 ELSE 1 END) AS retracted_count
                """
            ).single()
            assert row is not None
            return (
                int(row["edge_count"]),
                int(row["distinct_link_uids"]),
                int(row["retracted_count"]),
            )
    finally:
        driver.close()


def _claim_uid_sample(cfg: Neo4jConfig) -> str:
    driver = _with_driver(cfg)
    try:
        with driver.session(**_session_kwargs(cfg)) as session:
            row = session.run("MATCH (c:Claim) RETURN c.uid AS uid ORDER BY uid LIMIT 1").single()
            assert row is not None
            return str(row["uid"])
    finally:
        driver.close()


def _seed_project(project_path: Path) -> None:
    create_project(project_path)
    with ChronicleSession(project_path) as session:
        _, inv_a = session.create_investigation("Neo4j live A", actor_id="test", actor_type="tool")
        _, ev_a = session.ingest_evidence(
            inv_a,
            b"Shared evidence bytes",
            "text/plain",
            original_filename="shared-a.txt",
            actor_id="test",
            actor_type="tool",
        )
        _, span_a = session.anchor_span(
            inv_a,
            ev_a,
            "text_offset",
            {"start_char": 0, "end_char": 6},
            quote="Shared",
            actor_id="test",
            actor_type="tool",
        )
        _, claim_a = session.propose_claim(
            inv_a,
            "Same claim text across investigations.",
            actor_id="test",
            actor_type="tool",
        )
        _, support_a1 = session.link_support(
            inv_a, span_a, claim_a, actor_id="test", actor_type="tool"
        )
        session.link_support(inv_a, span_a, claim_a, actor_id="test", actor_type="tool")
        session.link_challenge(inv_a, span_a, claim_a, actor_id="test", actor_type="tool")
        session.retract_support(
            support_a1, actor_id="test", actor_type="tool", rationale="Live test"
        )

        _, inv_b = session.create_investigation("Neo4j live B", actor_id="test", actor_type="tool")
        _, ev_b = session.ingest_evidence(
            inv_b,
            b"Shared evidence bytes",
            "text/plain",
            original_filename="shared-b.txt",
            actor_id="test",
            actor_type="tool",
        )
        _, span_b = session.anchor_span(
            inv_b,
            ev_b,
            "text_offset",
            {"start_char": 0, "end_char": 6},
            quote="Shared",
            actor_id="test",
            actor_type="tool",
        )
        _, claim_b = session.propose_claim(
            inv_b,
            "Same claim text across investigations.",
            actor_id="test",
            actor_type="tool",
        )
        session.link_support(inv_b, span_b, claim_b, actor_id="test", actor_type="tool")


def _snapshot_counts(cfg: Neo4jConfig) -> dict[str, int]:
    supports_total, supports_distinct_uids, supports_retracted = _supports_stats(cfg)
    return {
        "claims": _count_nodes(cfg, "Claim"),
        "evidence_items": _count_nodes(cfg, "EvidenceItem"),
        "supports": supports_total,
        "supports_distinct_link_uids": supports_distinct_uids,
        "supports_retracted": supports_retracted,
        "challenges": _count_relationships(cfg, "CHALLENGES"),
        "contains": _count_relationships(cfg, "CONTAINS"),
        "contains_claim": _count_relationships(cfg, "CONTAINS_CLAIM"),
        "contains_evidence": _count_relationships(cfg, "CONTAINS_EVIDENCE"),
    }


@pytest.fixture(scope="module")
def neo4j_live_config() -> Neo4jConfig:
    if not _truthy(os.environ.get("CHRONICLE_RUN_NEO4J_LIVE_TESTS", "")):
        pytest.skip("Neo4j live tests disabled. Set CHRONICLE_RUN_NEO4J_LIVE_TESTS=1 to run.")
    uri = os.environ.get("NEO4J_URI", "").strip()
    user = (os.environ.get("NEO4J_USER", "neo4j") or "neo4j").strip()
    password = os.environ.get("NEO4J_PASSWORD", "")
    database = (os.environ.get("NEO4J_DATABASE", "") or "").strip() or None
    if not uri:
        pytest.fail("NEO4J_URI is required when CHRONICLE_RUN_NEO4J_LIVE_TESTS=1.")
    if not password:
        pytest.fail("NEO4J_PASSWORD is required when CHRONICLE_RUN_NEO4J_LIVE_TESTS=1.")
    cfg: Neo4jConfig = {"uri": uri, "user": user, "password": password, "database": database}
    last_error: Exception | None = None
    for _ in range(45):
        driver = _with_driver(cfg)
        try:
            driver.verify_connectivity()
            with driver.session(**_session_kwargs(cfg)) as session:
                session.run("RETURN 1 AS ok").single()
            return cfg
        except Exception as e:
            last_error = e
            time.sleep(1)
        finally:
            driver.close()
    pytest.fail(f"Neo4j live test connectivity failed: {last_error}")


@pytest.fixture(autouse=True)
def _clean_graph_between_tests(neo4j_live_config: Neo4jConfig) -> None:
    _clear_graph(neo4j_live_config)
    yield
    _clear_graph(neo4j_live_config)


def test_live_sync_non_dedupe_mode(tmp_path: Path, neo4j_live_config: Neo4jConfig) -> None:
    project_path = tmp_path / "non_dedupe"
    _seed_project(project_path)

    sync_project_to_neo4j(
        project_path,
        neo4j_live_config["uri"],
        neo4j_live_config["user"],
        neo4j_live_config["password"],
        dedupe_evidence_by_content_hash=False,
        database=neo4j_live_config["database"],
        max_retries=2,
    )
    first = _snapshot_counts(neo4j_live_config)
    assert first["claims"] == 2
    assert first["evidence_items"] == 2
    assert first["supports"] == 3
    assert first["supports_distinct_link_uids"] == 3
    assert first["supports_retracted"] == 1
    assert first["challenges"] == 1
    assert first["contains"] == 2
    assert first["contains_claim"] == 0
    assert first["contains_evidence"] == 0

    sync_project_to_neo4j(
        project_path,
        neo4j_live_config["uri"],
        neo4j_live_config["user"],
        neo4j_live_config["password"],
        dedupe_evidence_by_content_hash=False,
        database=neo4j_live_config["database"],
        max_retries=2,
    )
    second = _snapshot_counts(neo4j_live_config)
    assert second == first


def test_live_sync_dedupe_mode(tmp_path: Path, neo4j_live_config: Neo4jConfig) -> None:
    project_path = tmp_path / "dedupe"
    _seed_project(project_path)

    sync_project_to_neo4j(
        project_path,
        neo4j_live_config["uri"],
        neo4j_live_config["user"],
        neo4j_live_config["password"],
        dedupe_evidence_by_content_hash=True,
        database=neo4j_live_config["database"],
        max_retries=2,
    )
    first = _snapshot_counts(neo4j_live_config)
    assert first["claims"] == 1
    assert first["evidence_items"] == 1
    assert first["supports"] == 3
    assert first["supports_distinct_link_uids"] == 3
    assert first["supports_retracted"] == 1
    assert first["challenges"] == 1
    assert first["contains"] == 0
    assert first["contains_claim"] == 2
    assert first["contains_evidence"] == 2

    sample_uid = _claim_uid_sample(neo4j_live_config)
    assert len(sample_uid) == 64
    assert all(ch in "0123456789abcdef" for ch in sample_uid)

    sync_project_to_neo4j(
        project_path,
        neo4j_live_config["uri"],
        neo4j_live_config["user"],
        neo4j_live_config["password"],
        dedupe_evidence_by_content_hash=True,
        database=neo4j_live_config["database"],
        max_retries=2,
    )
    second = _snapshot_counts(neo4j_live_config)
    assert second == first
