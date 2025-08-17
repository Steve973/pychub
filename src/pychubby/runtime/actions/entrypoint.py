import importlib.metadata as im
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

def run_entrypoint(name: str, args: list[str]) -> None:
    ep = _select_console_entrypoint(name)
    if not ep:
        die(f"no console_scripts entry point named '{name}'")
    func = ep.load()
    sys.argv = [name] + list(args)
    func()

def maybe_run_entrypoint(run_arg: str | None, baked_entrypoint: str | None, extra_args: list[str]) -> None:
    if run_arg:
        run_entrypoint(run_arg, extra_args)
    elif baked_entrypoint:
        run_entrypoint(baked_entrypoint, extra_args)
