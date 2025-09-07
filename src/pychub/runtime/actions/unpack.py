from __future__ import annotations

from pathlib import Path
import shutil

def _copy_tree(src: Path, dst: Path) -> int:
    if not src.exists():
        return 0
    count = 0
    for p in src.rglob("*"):
        if p.is_file():
            rel = p.relative_to(src)
            (dst / rel).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(p, dst / rel)
            count += 1
    return count

def unpack_chub(bundle_root: Path, dest: Path | None) -> None:
    dst = dest or (bundle_root.parent / (bundle_root.name + "_unpacked"))
    dst.mkdir(parents=True, exist_ok=True)
    total = 0
    total += _copy_tree(bundle_root / "libs", dst / "libs")
    total += _copy_tree(bundle_root / "scripts", dst / "scripts")
    total += _copy_tree(bundle_root / "includes", dst / "includes")
    cfg = bundle_root / ".chubconfig"
    if cfg.exists():
        dst.mkdir(parents=True, exist_ok=True)
        shutil.copy2(cfg, dst / ".chubconfig")
        total += 1
    print(f"unpacked {total} files to {dst}")
