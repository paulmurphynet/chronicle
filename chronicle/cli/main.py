"""CLI entry point for Chronicle."""

from __future__ import annotations

import argparse
import os
import sqlite3
import sys
from pathlib import Path

from chronicle.cli.dispatch import dispatch_command
from chronicle.cli.parser import build_parser
from chronicle.core.errors import ChronicleUserError

# User-facing errors: show message and exit 1. All other exceptions propagate (e.g. for pytest).
_USER_ERRORS = (ValueError, FileNotFoundError, OSError, sqlite3.Error, ChronicleUserError)


def _path_arg(s: str) -> Path:
    return Path(s).resolve()


def _actor_from_args(args: argparse.Namespace) -> tuple[str, str]:
    """Resolve actor identity from args or environment."""
    aid = getattr(args, "actor_id", None) or os.environ.get("CHRONICLE_ACTOR_ID") or "default"
    atype = getattr(args, "actor_type", None) or os.environ.get("CHRONICLE_ACTOR_TYPE") or "human"
    return (aid or "default", atype or "human")


def _load_dotenv_if_available() -> None:
    """Load .env from cwd and repo root when python-dotenv is installed."""
    try:
        import logging

        from dotenv import load_dotenv

        logging.getLogger("dotenv").setLevel(logging.ERROR)  # avoid parse warnings to stderr
        load_dotenv()  # cwd first
        project_root = Path(__file__).resolve().parent.parent.parent  # cli -> chronicle -> repo
        env_file = project_root / ".env"
        if env_file.is_file():
            load_dotenv(env_file)
    except ImportError:
        pass


def main() -> int:
    """Parse CLI args and dispatch to command handlers."""
    _load_dotenv_if_available()
    parser = build_parser(_path_arg)
    args = parser.parse_args()
    try:
        actor_id, actor_type = _actor_from_args(args)
        return dispatch_command(args, actor_id, actor_type)
    except _USER_ERRORS as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
