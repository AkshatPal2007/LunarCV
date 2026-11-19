"""Report publication blockers; never upload or publish data automatically."""

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


if __name__ == "__main__":
    blockers = []
    if not (ROOT / "LICENSE").is_file():
        blockers.append("Choose and approve a license for original project code")
    if not any(
        (ROOT / "backend/lunarcv/third_party/rift2" / name).is_file()
        for name in ("LICENSE", "LICENSE.txt", "COPYING")
    ):
        blockers.append(
            "Resolve provenance and redistribution license of bundled RIFT2 wrapper/descriptor implementation"
        )
    tracked = subprocess.run(
        [
            "/usr/bin/git",
            "ls-files",
            "data/sample_pairs",
            "data/raw",
            "data/processed",
            "frontend/public/assets",
            "outputs",
            "data/results",
            "data/Comparative_Evaluation_of_Traditional_and_Deep_Lea.pdf",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.splitlines()
    tracked = [path for path in tracked if not path.endswith("/.gitkeep")]
    if tracked:
        blockers.append(
            "Review rights for tracked mission-derived images/results and the paper; do not assume download access permits redistribution"
        )
    report = {
        "public_release_ready": not blockers,
        "blockers": blockers,
        "tracked_assets_requiring_review": tracked,
        "scientific_status": "independent registration accuracy not established",
    }
    print(json.dumps(report, indent=2))
    sys.exit(1 if blockers else 0)
