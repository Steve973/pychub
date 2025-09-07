from __future__ import annotations

import os
import sys
from pathlib import Path


def _run_entrypoint_with_python(
        python: Path,
        dry_run: bool,
        entrypoint: str | None,
        argv: list[str],) -> int:
    """Run entrypoint under a specific interpreter.

    Entry point forms supported by README:
      1) module:function
      2) console-script name
    """
    if dry_run:
        print("[dry-run] would run entrypoint:", entrypoint)
        return 0
    if entrypoint is None:
        # Per README: warn and exit 0 when there's nothing to run
        sys.stderr.write("pychub: no entrypoint to run; installation complete.\n")
        return 0

    if ":" in entrypoint:
        mod, func = entrypoint.split(":", 1)
        code = (
            "import importlib, sys, inspect\n"
            f"mod = importlib.import_module({mod!r})\n"
            f"fn = getattr(mod, {func!r})\n"
            "argv = list(sys.argv[1:])\n"
            "params = list(inspect.signature(fn).parameters.values())\n"
            "POS_ONLY = inspect.Parameter.POSITIONAL_ONLY\n"
            "POS_OR_KW = inspect.Parameter.POSITIONAL_OR_KEYWORD\n"
            "VAR_POSITIONAL = inspect.Parameter.VAR_POSITIONAL\n"
            "has_varargs = any(p.kind == VAR_POSITIONAL for p in params)\n"
            "positional = [p for p in params if p.kind in (POS_ONLY, POS_OR_KW)]\n"
            "required = [p for p in positional if p.default is inspect._empty]\n"
            "call_argv = argv if has_varargs else argv[:len(positional)]\n"
            "if (not has_varargs) and (len(call_argv) < len(required)):\n"
            "    call_argv = []\n"
            "rv = fn(*call_argv)\n"
            "sys.exit(int(rv) if isinstance(rv, int) else 0)\n"
        )
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
