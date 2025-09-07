from __future__ import annotations

from pathlib import Path

def discover_wheels(libs_dir: Path) -> list[Path]:
    libs_dir.mkdir(parents=True, exist_ok=True)
    wheels = sorted(libs_dir.glob("*.whl"))
    return wheels
