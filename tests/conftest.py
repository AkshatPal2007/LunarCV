"""Allow legacy geography tests to exercise the maintained backend package."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"backend"))
