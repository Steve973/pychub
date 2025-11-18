from __future__ import annotations

from pathlib import Path
from typing import Iterable

from .chubconfig import load_chubconfig


def _print_lines(lines: Iterable[str]) -> None:
    for line in lines:
        print(line)


def list_wheels(bundle_root: Path, *, quiet: bool = False, verbose: bool = False) -> None:
    """list bundled wheels from .chubconfig (preferred) or libs/ fallback.

    Output contract (simple, stable):
    - Each top-level wheel on its own line ending with ':'
    - Dependencies listed as indented '- <wheel>' lines beneath it
    - Preserves insertion order from the config
    - When no config, falls back to scanning bundle_root / 'libs'
    - Quiet mode: emit nothing if there is nothing to list
    """
    cfg = load_chubconfig(bundle_root)

    # Preferred: read the resolved closure from the config
    if cfg and cfg.pinned_wheels:
        lines: list[str] = []
        if quiet:
            for wheel in cfg.pinned_wheels:
                lines.append(f"w:{wheel}")
        else:
            for wheel in cfg.pinned_wheels:  # preserves insertion order
                if verbose:
                    lines.append(f"Wheel: {wheel}")
                else:
                    lines.append(f"{wheel}")
        if lines:
            _print_lines(lines)
        elif not quiet:
            print("(no wheels found)")
        return

    # Fallback: scan libs/ for loose wheels when config is absent
    libs_dir = bundle_root / "libs"
    wheels = sorted(p.name for p in libs_dir.glob("*.whl"))
    if not wheels:
        if not quiet:
            print("(no wheels found)")
        return
    _print_lines(wheels)
