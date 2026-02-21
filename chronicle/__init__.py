"""Chronicle — event-sourced epistemic ledger for investigations."""

import logging

__version__ = "0.9.0"

# Use this logger for store/commands (errors, rebuild, import). CLI stays print-based.
log = logging.getLogger("chronicle")
