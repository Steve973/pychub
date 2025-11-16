from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def build_test_wheel(test_proj_dir: Path) -> Path:
    """
    Build a wheel from the local test project so integration tests
    always use a fresh, local artifact.

    Returns the path to the built wheel.
    """
    test_proj_dir = Path(test_proj_dir).resolve()
    dist_dir = test_proj_dir / "dist"
    dist_dir.mkdir(parents=True, exist_ok=True)

    cmd = [sys.executable, "-m", "build", "--wheel", "--no-isolation"]
    result = subprocess.run(
        cmd,
        cwd=str(test_proj_dir),
        text=True,
        capture_output=True,
    )

    if result.returncode != 0:
        raise RuntimeError(f"Wheel build failed:\n{result.stdout}\n{result.stderr}")

    wheels = sorted(dist_dir.glob("*.whl"), key=lambda p: p.stat().st_mtime)
    if not wheels:
        raise FileNotFoundError(f"No wheel produced in {dist_dir}")

    return wheels[-1]
