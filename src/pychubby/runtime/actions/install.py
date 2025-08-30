from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from ..utils import pep668_blocked, die

def _pip_cmd(python: str | None = None) -> list[str]:
    return [(python or sys.executable), "-m", "pip"]

def install_wheels(
    wheels: list[Path],
    dry_run: bool = False,
    quiet: bool = False,
    verbose: bool = False,
    no_deps: bool = False,
    python: str | None = None) -> None:
    if dry_run:
        if not quiet:
            print("[dry-run] would install:")
            for w in wheels:
                print("  ", w.name)
        return

    cmd = _pip_cmd(python) + ["install"]
    if no_deps:
        cmd += ["--no-deps"]
    if quiet:
        cmd += ["-q"]
    elif verbose:
        cmd += ["-v"]
    cmd += [str(w) for w in wheels]

    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode and pep668_blocked(res.stderr):
        cmd = _pip_cmd(python) + ["install", "--break-system-packages"]
        if no_deps:
            cmd += ["--no-deps"]
        if quiet:
            cmd += ["-q"]
        elif verbose:
            cmd += ["-v"]
        cmd += [str(w) for w in wheels]
        res = subprocess.run(cmd, capture_output=True, text=True)

    if res.returncode:
        sys.stderr.write(res.stderr or "")
        die(res.returncode)

    if not quiet:
        print("Installed", len(wheels), "wheel(s) into", python or sys.executable)
