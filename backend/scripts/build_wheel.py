"""Build a local wheel from clean temporary staging and audit packaged source.

Never publishes. Avoid setuptools reusing stale files in an old build/lib tree.
"""

import argparse
import shutil
import subprocess
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out-dir", type=Path, default=ROOT / "outputs/artifacts/local-unpublished"
    )
    args = parser.parse_args()
    output = args.out_dir.resolve()
    output.mkdir(parents=True, exist_ok=True)
    uv = shutil.which("uv")
    if not uv:
        raise RuntimeError("uv is required")
    with tempfile.TemporaryDirectory(prefix="lunarcv-wheel-") as directory:
        staging = Path(directory)
        for name in ("pyproject.toml", "uv.lock", "README.md"):
            shutil.copy2(ROOT / "backend" / name, staging / name)
        for name in ("app", "lunarcv"):
            shutil.copytree(
                ROOT / "backend" / name,
                staging / name,
                ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
            )
        # Only the local uv executable and literal argv; no shell interpolation.
        subprocess.run(  # noqa: S603
            [uv, "build", str(staging), "--wheel", "--out-dir", str(output)], check=True
        )
        for wheel in output.glob("lunarcv-*.whl"):
            with zipfile.ZipFile(wheel) as archive:
                expected = {
                    path.relative_to(staging).as_posix()
                    for package in ("app", "lunarcv")
                    for path in (staging / package).rglob("*.py")
                }
                actual = {name for name in archive.namelist() if name.endswith(".py")}
                if actual != expected:
                    raise RuntimeError(
                        f"Wheel module inventory mismatch: {actual ^ expected}"
                    )
                for name in expected:
                    if archive.read(name) != (staging / name).read_bytes():
                        raise RuntimeError(f"Stale packaged source: {name}")
                if (
                    archive.read("lunarcv/model_assets.json")
                    != (staging / "lunarcv/model_assets.json").read_bytes()
                ):
                    raise RuntimeError("Model asset manifest mismatch")
                print(
                    f"Verified {len(expected)} Python modules and model manifest: {wheel}"
                )


if __name__ == "__main__":
    main()
