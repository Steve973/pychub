from pathlib import Path

def list_wheels(libs_dir: Path) -> None:
    wheels = sorted(libs_dir.glob("*.whl"))
    if not wheels:
        print("(no wheels found)")
        return
    for w in wheels:
        print(w.name)
