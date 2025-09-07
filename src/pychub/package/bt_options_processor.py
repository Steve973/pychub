from __future__ import annotations

import sys
from importlib.metadata import PackageNotFoundError, version as get_version
from pathlib import Path

from .chubproject import load_chubproject, save_chubproject
from .packager import build_chub
from ..model.chubproject_model import ChubProject


def parse_chubproject(chubproject_path: Path) -> ChubProject | None:
    if not chubproject_path.is_file():
        raise FileNotFoundError(f"Chub project file not found: {chubproject_path}")
    try:
        return load_chubproject(chubproject_path)
    except ImportError:
        print("pychub: (not installed)")


def process_chubproject(chubproject_path: Path):
    chubproject = parse_chubproject(chubproject_path)
    build_chub(chubproject)


def process_options(args):
    if args.version:
        print(f"Python: {sys.version.split()[0]}")
        try:
            version = get_version("pychub")
        except PackageNotFoundError:
            version = "(source)"
        print(f"pychub: {version}")
        return

    chubproject = None
    if args.chubproject:
        chubproject_path = Path(args.chubproject).expanduser().resolve()
        chubproject = parse_chubproject(chubproject_path)

    build_args = ChubProject.override_from_cli_args(chubproject, vars(args)) if chubproject else ChubProject.from_cli_args(vars(args))

    if args.chubproject_save:
        chubproject_path = Path(args.chubproject_save).expanduser().resolve()
        save_chubproject(build_args, chubproject_path, overwrite=True, make_parents=True)

    build_chub(build_args)


