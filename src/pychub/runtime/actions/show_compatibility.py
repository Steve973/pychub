from __future__ import annotations

from pathlib import Path
from typing import Iterable

from packaging.tags import sys_tags

from .chubconfig import load_chubconfig


def _print_lines(lines: Iterable[str]) -> None:
    for line in lines:
        print(line)


def show_compatibility(bundle_root: Path) -> None:
    """
    List supported targets from .chubconfig.
    """
    cfg = load_chubconfig(bundle_root)
    current_tags = {f"{tag.interpreter}-{tag.abi}-{tag.platform}" for tag in sys_tags()}
    lines: list[str] = ["Supported targets:"]
    compatibility_detected = False
    if cfg and cfg.compatibility["targets"]:
        for target in cfg.compatibility["targets"]:
            if target == "py3-none-any":
                lines.append(" - universal (py3-none-any)")
                compatibility_detected = True
            else:
                if target in current_tags:
                    lines.append(f" - {target} (detected compatibility)")
                    compatibility_detected = True
                else:
                    lines.append(f" - {target}")
    if len(lines) == 1:
        lines.append(" - No supported targets found!")
    if not compatibility_detected:
        lines.append(" - No target compatibility detected!")
    _print_lines(lines)
    return
