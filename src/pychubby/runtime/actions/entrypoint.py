from __future__ import annotations

import importlib
import importlib.metadata as im
import runpy
import sys

from ..utils import die


def _select_console_entrypoint(name: str):
    eps = im.entry_points()
    try:
        cands = list(eps.select(group="console_scripts"))
    except Exception:
        cands = [ep for ep in eps if ep.group == "console_scripts"]
    for ep in cands:
        if ep.name == name:
            return ep
    return None


def _run_module_func(entrypoint: str, args: list[str]) -> bool:
    """Try to run entrypoint in form 'module:func'."""
    if ":" not in entrypoint:
        return False
    mod_name, func_name = entrypoint.split(":", 1)
    try:
        module = importlib.import_module(mod_name)
        func = getattr(module, func_name)
    except (ImportError, AttributeError) as e:
        die(f"Failed to load entrypoint '{entrypoint}': {e}")
    sys.argv = [entrypoint] + args
    func()
    return True


def _run_console_script(entrypoint: str, args: list[str]) -> bool:
    """Try to run console_scripts entry point."""
    ep = _select_console_entrypoint(entrypoint)
    if not ep:
        return False
    func = ep.load()
    sys.argv = [entrypoint] + args
    func()
    return True


def _run_module_main(entrypoint: str, args: list[str]) -> bool:
    """Fallback: attempt to run the module like `python -m module`."""
    try:
        sys.argv = [entrypoint] + args
        runpy.run_module(entrypoint, run_name="__main__")
        return True
    except Exception as e:
        die(f"Could not run module '{entrypoint}' as a script: {e}")


def run_entrypoint(entrypoint: str, args: list[str]) -> None:
    if _run_module_func(entrypoint, args):
        return
    if _run_console_script(entrypoint, args):
        return
    if _run_module_main(entrypoint, args):
        return
    die(f"Could not resolve or execute entrypoint '{entrypoint}'")


def maybe_run_entrypoint(run_arg: str | None, baked_entrypoint: str | None, extra_args: list[str]) -> None:
    if run_arg:
        run_entrypoint(run_arg, extra_args)
    elif baked_entrypoint:
        run_entrypoint(baked_entrypoint, extra_args)
