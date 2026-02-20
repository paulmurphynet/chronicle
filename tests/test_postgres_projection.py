"""Unit tests for SQLite->Postgres projection SQL translation helpers."""

from chronicle.store.postgres_projection import translate_sqlite_to_postgres_sql


def test_translate_insert_or_ignore_to_on_conflict_do_nothing() -> None:
    sql = """
        INSERT OR IGNORE INTO processed_event (projection_name, event_id, processed_at)
        VALUES (?, ?, ?)
    """
    out = translate_sqlite_to_postgres_sql(sql)
    assert "INSERT INTO processed_event" in out
    assert "ON CONFLICT DO NOTHING" in out
    assert out.count("%s") == 3


def test_translate_insert_or_replace_retraction_to_upsert() -> None:
    sql = "INSERT OR REPLACE INTO evidence_link_retraction (link_uid, retracted_at, rationale) VALUES (?, ?, ?)"
    out = translate_sqlite_to_postgres_sql(sql)
    assert "INSERT INTO evidence_link_retraction" in out
    assert "ON CONFLICT (link_uid) DO UPDATE SET" in out
    assert "retracted_at = EXCLUDED.retracted_at" in out
    assert out.count("%s") == 3


def test_translate_date_now_and_preserve_quoted_question_mark() -> None:
    sql = "SELECT '?' AS literal WHERE due_date < date('now') AND id = ?"
    out = translate_sqlite_to_postgres_sql(sql)
    assert "CURRENT_DATE" in out
    assert "'?'" in out
    assert out.count("%s") == 1
