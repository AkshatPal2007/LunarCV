"""Remove only known rebuildable caches; preserve data, models, runs and environments."""
from pathlib import Path
import shutil
ROOT=Path(__file__).resolve().parents[1]
for relative in ("frontend/dist","frontend/test-results","frontend/playwright-report","backend/.pytest_cache","backend/.ruff_cache",".pytest_cache"):
    target=(ROOT/relative).resolve()
    if not target.is_relative_to(ROOT) or target==ROOT:
        raise RuntimeError("Unsafe cleanup target")
    if target.is_dir():
        shutil.rmtree(target)
        print(f"Removed {relative}")
