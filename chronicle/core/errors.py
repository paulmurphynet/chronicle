"""User-facing errors: validation, missing project, permission, etc. Caught by CLI for clean messages."""


class ChronicleError(Exception):
    """Base for Chronicle errors."""


class ChronicleUserError(ChronicleError):
    """Error that should be shown to the user as a message; not a bug. E.g. validation, missing project."""


class ChronicleIdempotencyCapacityError(ChronicleUserError):
    """Raised when the idempotency-key event cap is reached. API maps to 429. See CHRONICLE_MAX_IDEMPOTENCY_KEY_EVENTS."""
