"""Allow running as python -m tools.verify_chronicle file.chronicle."""

import sys

from .verify_chronicle import main

sys.exit(main())
