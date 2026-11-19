"""Repository adapter for the installed lunarcv-inspect command."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from lunarcv.audit import main

if __name__ == "__main__":
    main()
