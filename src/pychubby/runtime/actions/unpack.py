from pathlib import Path
import shutil

def unpack_wheels(libs_dir: Path, dest: Path) -> None:
    dest.mkdir(parents=True, exist_ok=True)
    copied = 0
    for w in libs_dir.glob("*.whl"):
        shutil.copy2(w, dest / w.name)
        copied += 1
    print(f"unpacked {copied} wheels to {dest}")
