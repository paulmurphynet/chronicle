"""Validation limits for free-text and resource bounds. Configurable via env."""

import logging
import os

from chronicle.core.errors import ChronicleUserError

log = logging.getLogger(__name__)


def _env_int(name: str, default: int) -> int:
    """Parse env var as int; return default on missing or invalid (avoids crash at import)."""
    raw = os.environ.get(name, "").strip()
    if not raw:
        return default
    try:
        val = int(raw)
        return val if val > 0 else default
    except ValueError:
        log.warning("Invalid %s=%r; using default %s", name, raw, default)
        return default


# Max lengths for stored text (characters). Override with CHRONICLE_MAX_* env vars.
MAX_TITLE_LENGTH = _env_int("CHRONICLE_MAX_TITLE_LENGTH", 2000)
MAX_DESCRIPTION_LENGTH = _env_int("CHRONICLE_MAX_DESCRIPTION_LENGTH", 50000)
MAX_CLAIM_TEXT_LENGTH = _env_int("CHRONICLE_MAX_CLAIM_TEXT_LENGTH", 100000)

# Max evidence file size (bytes). Default 100 MiB.
_DEFAULT_MAX_EVIDENCE_BYTES = 100 * 1024 * 1024
MAX_EVIDENCE_BYTES = _env_int(
    "CHRONICLE_MAX_EVIDENCE_BYTES",
    _DEFAULT_MAX_EVIDENCE_BYTES,
)

# Max limit for list/history query params (DoS protection). Override with CHRONICLE_MAX_LIST_LIMIT.
_DEFAULT_MAX_LIST_LIMIT = 1000
MAX_LIST_LIMIT = _env_int("CHRONICLE_MAX_LIST_LIMIT", _DEFAULT_MAX_LIST_LIMIT)

# Max .chronicle import file size (bytes). DoS mitigation for POST /project/import. Default 500 MiB.
_DEFAULT_MAX_IMPORT_BYTES = 500 * 1024 * 1024
MAX_IMPORT_BYTES = _env_int("CHRONICLE_MAX_IMPORT_BYTES", _DEFAULT_MAX_IMPORT_BYTES)

# Zip safety limits for import/verification (zip-bomb mitigation).
_DEFAULT_MAX_IMPORT_ARCHIVE_ENTRIES = 5000
MAX_IMPORT_ARCHIVE_ENTRIES = _env_int(
    "CHRONICLE_MAX_IMPORT_ARCHIVE_ENTRIES",
    _DEFAULT_MAX_IMPORT_ARCHIVE_ENTRIES,
)
_DEFAULT_MAX_IMPORT_ARCHIVE_UNCOMPRESSED_BYTES = 2 * 1024 * 1024 * 1024  # 2 GiB
MAX_IMPORT_ARCHIVE_UNCOMPRESSED_BYTES = _env_int(
    "CHRONICLE_MAX_IMPORT_ARCHIVE_UNCOMPRESSED_BYTES",
    _DEFAULT_MAX_IMPORT_ARCHIVE_UNCOMPRESSED_BYTES,
)
_DEFAULT_MAX_IMPORT_ARCHIVE_MEMBER_BYTES = 512 * 1024 * 1024  # 512 MiB
MAX_IMPORT_ARCHIVE_MEMBER_BYTES = _env_int(
    "CHRONICLE_MAX_IMPORT_ARCHIVE_MEMBER_BYTES",
    _DEFAULT_MAX_IMPORT_ARCHIVE_MEMBER_BYTES,
)
_DEFAULT_MAX_IMPORT_ARCHIVE_COMPRESSION_RATIO = 200
MAX_IMPORT_ARCHIVE_COMPRESSION_RATIO = _env_int(
    "CHRONICLE_MAX_IMPORT_ARCHIVE_COMPRESSION_RATIO",
    _DEFAULT_MAX_IMPORT_ARCHIVE_COMPRESSION_RATIO,
)

# Max FTS search query length (chars). Red team #15: limit abuse / DoS.
MAX_SEARCH_QUERY_LENGTH = _env_int("CHRONICLE_MAX_SEARCH_QUERY_LENGTH", 500)

# Max number of events that may have a non-null idempotency_key (0 = no limit). DoS mitigation: prevents
# unbounded growth from clients sending many unique Idempotency-Key headers. When at cap, append raises
# ChronicleIdempotencyCapacityError (API returns 429).
MAX_IDEMPOTENCY_KEY_EVENTS = _env_int("CHRONICLE_MAX_IDEMPOTENCY_KEY_EVENTS", 0)


# Allowed values for optional defeater_kind (rebutting | undercutting). We record, we don't verify semantics.
DEFEATER_KIND_VALID = frozenset({"rebutting", "undercutting"})


def validate_defeater_kind(defeater_kind: str | None) -> None:
    """Raise ChronicleUserError if defeater_kind is non-empty and not one of rebutting | undercutting."""
    if not defeater_kind or not str(defeater_kind).strip():
        return
    val = str(defeater_kind).strip().lower()
    if val not in DEFEATER_KIND_VALID:
        raise ChronicleUserError(
            f"defeater_kind must be one of {sorted(DEFEATER_KIND_VALID)}; got {defeater_kind!r}"
        )


def sanitize_fts_query(query: str) -> str:
    """Sanitize user input for FTS5 MATCH: trim, truncate, escape double-quotes. Red team #15."""
    if not query:
        return ""
    s = (query or "").strip()[:MAX_SEARCH_QUERY_LENGTH]
    # FTS5: double-quote is phrase delimiter; escape literal " by doubling
    return s.replace('"', '""')
