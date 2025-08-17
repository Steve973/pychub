from pathlib import Path

def discover_wheels(libs_dir: Path, only: str | None) -> list[Path]:
    libs_dir.mkdir(parents=True, exist_ok=True)
    wheels = sorted(libs_dir.glob("*.whl"))
    if only:
        prefs = tuple(x.strip() for x in only.split(",") if x.strip())
        wheels = [w for w in wheels if w.name.startswith(prefs)]
    return wheels
