"""Fetch official permissive model assets once, then verify recorded checksums."""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from lunarcv.engine import _identity, _matcher

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--features", choices=["disk", "aliked", "sift"], default="aliked"
    )
    features = parser.parse_args().features
    _matcher("lightglue", 1024, 2048, features)
    _identity(features, "lightglue")
    print(f"Verified official {features}/LightGlue assets available in the Torch cache")
