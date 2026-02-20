"""Optional claim embedding store for semantic similarity. Uses same SQLite DB as read model. VECTOR_PROJECTION.md."""

import sqlite3
import struct
from pathlib import Path

from chronicle.store.schema import CLAIM_EMBEDDING_DDL


def _blob_to_vec(blob: bytes) -> list[float]:
    n = len(blob) // 4
    return list(struct.unpack(f"{n}f", blob))


def _vec_to_blob(vec: list[float]) -> bytes:
    return struct.pack(f"{len(vec)}f", *vec)


def _cosine_sim(a: list[float], b: list[float]) -> float:
    if not a or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b, strict=True))
    na = sum(x * x for x in a) ** 0.5
    nb = sum(x * x for x in b) ** 0.5
    if na == 0 or nb == 0:
        return 0.0
    return float(dot / (na * nb))


class ClaimEmbeddingStore:
    """Store and query claim embeddings (same DB as project). Optional; table created on first use."""

    def __init__(self, db_path: Path | str) -> None:
        self._path = Path(db_path)
        self._conn: sqlite3.Connection | None = None

    def _connection(self) -> sqlite3.Connection:
        if self._conn is None:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            self._conn = sqlite3.connect(str(self._path), check_same_thread=False)
            self._conn.executescript(CLAIM_EMBEDDING_DDL)
            self._conn.commit()
        return self._conn

    def get(self, claim_uid: str) -> list[float] | None:
        row = (
            self._connection()
            .execute("SELECT embedding FROM claim_embedding WHERE claim_uid = ?", (claim_uid,))
            .fetchone()
        )
        if row is None:
            return None
        return _blob_to_vec(row[0])

    def set(self, claim_uid: str, embedding: list[float], updated_at: str) -> None:
        conn = self._connection()
        conn.execute(
            "INSERT OR REPLACE INTO claim_embedding (claim_uid, embedding, updated_at) VALUES (?, ?, ?)",
            (claim_uid, _vec_to_blob(embedding), updated_at),
        )
        conn.commit()

    def similar(
        self, source_uid: str, candidate_uids: list[str], limit: int
    ) -> list[tuple[str, float]]:
        """Return (claim_uid, cosine_similarity) for candidates, sorted by similarity descending."""
        if not candidate_uids or limit <= 0:
            return []
        source_vec = self.get(source_uid)
        if source_vec is None:
            return []
        conn = self._connection()
        placeholders = ",".join("?" * len(candidate_uids))
        rows = conn.execute(
            f"SELECT claim_uid, embedding FROM claim_embedding WHERE claim_uid IN ({placeholders})",  # nosec B608
            candidate_uids,
        ).fetchall()
        scored: list[tuple[str, float]] = []
        for uid, blob in rows:
            if uid == source_uid:
                continue
            vec = _blob_to_vec(blob)
            sim = _cosine_sim(source_vec, vec)
            scored.append((uid, sim))
        scored.sort(key=lambda x: -x[1])
        return scored[:limit]
