from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from argparse import Namespace
from datetime import datetime, UTC
from importlib.metadata import version as get_version
from pathlib import Path

from appdirs import user_cache_dir

from pychub.model.build_event import audit
from pychub.model.buildplan_model import BuildPlan
from pychub.model.chubproject_model import ChubProject
from pychub.package.cli import create_arg_parser


@audit("INIT", "check_python_version")
def check_python_version(build_plan: BuildPlan):
    if sys.version_info < (3, 9):
        raise Exception("Must be using Python 3.9 or higher")


@audit("INIT", "verify_pip")
def verify_pip(build_plan: BuildPlan) -> None:
    """Ensure pip is available for the current Python.

    We verify `python -m pip --version` instead of relying on a `pip` script on
    PATH.
    """
    code = subprocess.call([sys.executable, "-m", "pip", "--version"])  # noqa: S603
    if code != 0:
        raise RuntimeError(
            "pip not found. Ensure 'python -m pip' works in this environment.")

@audit("INIT", "create_project_hash")
def project_hash(build_plan: BuildPlan, chubproject: ChubProject) -> str:
    """
    Compute a deterministic short hash of the ChubProject's canonical data.
    This defines the cache identity for all downstream phases.
    """
    data = chubproject.to_json()
    cp_hash = hashlib.sha512(data.encode()).hexdigest()[:16]
    build_plan.project_hash = cp_hash
    return cp_hash


@audit("INIT", "create_project_cache")
def cache_project(build_plan: BuildPlan, chubproject: ChubProject) -> Path:
    """Write the chubproject and metadata under a hash-named cache directory."""
    staging_dir = Path(user_cache_dir("pychub"))
    build_plan.staging_dir = staging_dir
    h = project_hash(build_plan, chubproject)
    cache_dir = staging_dir / h
    cache_dir.mkdir(parents=True, exist_ok=True)

    # write chubproject.toml
    project_path = cache_dir / "chubproject.toml"
    ChubProject.save_file(chubproject, path=project_path, overwrite=True)

    # write meta.json
    meta = {
        "pychub_version": get_version("pychub"),
        "created_at": datetime.now(UTC).replace(microsecond=0).isoformat(),
        "hash": h,
    }
    (cache_dir / "meta.json").write_text(json.dumps(meta, indent=2))

    return cache_dir


@audit("INIT", "parse_chubproject")
def process_chubproject(build_plan: BuildPlan, chubproject_path: Path) -> ChubProject | None:
    if not chubproject_path.is_file():
        raise FileNotFoundError(f"Chub project file not found: {chubproject_path}")
    try:
        chubproject = ChubProject.load_file(chubproject_path)
        build_plan.project = chubproject
        return chubproject
    except ImportError:
        print("pychub: (not installed)")


@audit("INIT", "process_cli_options")
def process_options(build_plan: BuildPlan, args, other_args) -> ChubProject:
    if args.chubproject:
        chubproject_path = Path(args.chubproject).expanduser().resolve()
        chubproject = process_chubproject(build_plan, chubproject_path)
        chubproject = ChubProject.override_from_cli_args(chubproject, vars(args))
    else:
        chubproject = ChubProject.from_cli_args(vars(args))
    chubproject.entrypoint_args = other_args
    return chubproject


@audit("INIT", "parse_cli")
def parse_cli(build_plan: BuildPlan) -> tuple[Namespace, list[str]]:
    parser = create_arg_parser()
    return parser.parse_known_args()


@audit("INIT")
def init_project(build_plan: BuildPlan, chubproject_path: Path | None = None) -> Path:
    check_python_version(build_plan)
    verify_pip(build_plan)
    namespace, other_args = parse_cli(build_plan)
    if chubproject_path:
        chubproject = process_chubproject(build_plan, chubproject_path)
    else:
        chubproject = process_options(build_plan, namespace, other_args)
    return cache_project(build_plan, chubproject)
