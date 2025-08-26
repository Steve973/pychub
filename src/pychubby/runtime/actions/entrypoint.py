from __future__ import annotations

import os
import sys
from pathlib import Path


def _run_entrypoint_with_python(
        python: Path,
        entrypoint: str | None,
        argv: list[str],) -> int:
    """Run entrypoint under a specific interpreter.

    Entry point forms supported by README:
      1) module:function
      2) console-script name
    """
    if entrypoint is None:
        # Per README: warn and exit 0 when there's nothing to run
        sys.stderr.write("pychubby: no entrypoint to run; installation complete.\n")
        return 0

    if ":" in entrypoint:
        mod, func = entrypoint.split(":", 1)
        code = (
            "import importlib, sys;"
            f"mod=importlib.import_module({mod!r});"
            f"fn=getattr(mod,{func!r});"
            "rv=fn(*sys.argv[1:]);"
            "import builtins;"
            "sys.exit(int(rv) if isinstance(rv,int) else 0)")
        return os.spawnv(os.P_WAIT, str(python), [str(python), "-c", code, *argv])

    # console script path in that interpreter's environment
    script = entrypoint
    if python.parent.name in ("bin", "Scripts"):
        cand = python.parent / script
        if os.name == "nt":
            # Prefer .exe if present
            exe = cand.with_suffix(".exe")
            if exe.exists():
                cand = exe
        if cand.exists():
            return os.spawnv(os.P_WAIT, str(cand), [str(cand), *argv])
    # Fallback: rely on PATH of the current process
    return os.spawnvp(os.P_WAIT, script, [script, *argv])
