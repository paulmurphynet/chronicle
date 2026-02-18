"""User-facing errors: validation, missing project, permission, etc. Caught by CLI for clean messages."""


class ChronicleError(Exception):
    """Base for Chronicle errors."""


class ChronicleUserError(ChronicleError):
    """Error that should be shown to the user as a message; not a bug. E.g. validation, missing entity, policy rules."""


class ChronicleProjectNotFoundError(ChronicleUserError):
    """Raised when the project path does not contain a Chronicle project (e.g. no chronicle.db). CLI → exit 1; API → 404."""


class ChronicleIdempotencyCapacityError(ChronicleUserError):
    """Raised when the idempotency-key event cap is reached. API maps to 429. See CHRONICLE_MAX_IDEMPOTENCY_KEY_EVENTS."""
