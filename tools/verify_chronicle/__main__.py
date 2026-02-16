"""Allow running as python -m tools.verify_chronicle file.chronicle."""
from .verify_chronicle import main
import sys
sys.exit(main())
