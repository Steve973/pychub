from __future__ import annotations

import json
import sys
from argparse import Namespace
from pathlib import Path

from appdirs import user_cache_dir

from pychub.model.build_event import audit, BuildEvent, StageType, EventType
from pychub.model.chubproject_model import ChubProject
from pychub.model.chubproject_provenance_model import SourceKind
from pychub.package.cli import create_arg_parser
from pychub.package.constants import CHUBPROJECT_FILENAME
from pychub.package.context_vars import current_build_plan
from pychub.package.lifecycle.execute import executor


@audit(StageType.INIT, "check_immediate_operations")
def check_immediate_operations(args: Namespace, chubproject: ChubProject) -> bool:
    """Check if any immediate operations are requested.
       If True is returned, the program must exit. False indicates
       that the program can continue."""
    build_plan = current_build_plan.get()
    if args.analyze_compatibility:
        executor.execute_analyze_compatibility(chubproject)
        build_plan.audit_log.append(
            BuildEvent.make(
                StageType.INIT,
                EventType.ACTION,
                message="Invoked immediate action: analyze compatibility."))
        return True
    elif args.chubproject_save:
        executor.execute_chubproject_save(chubproject, args.chubproject_save)
        build_plan.audit_log.append(
            BuildEvent.make(
                StageType.INIT,
                EventType.ACTION,
                message="Invoked immediate action: chubproject save."))
        return False
    elif args.version:
        executor.execute_version()
        build_plan.audit_log.append(
            BuildEvent.make(
                StageType.INIT,
                EventType.ACTION,
                message="Invoked immediate action: version."))
        return True
    return False


@audit(StageType.INIT, "create_project_cache")
def cache_project(chubproject: ChubProject) -> Path:
    """
    Initialize the BuildPlan's cache-related fields and write the
    chubproject and metadata under the hash-named project staging dir.
    """
    build_plan = current_build_plan.get()

    # Ensure cache_root is set (falls back to user_cache_dir if still default)
    if not getattr(build_plan, "cache_root", None) or not str(build_plan.cache_root):
        build_plan.cache_root = Path(user_cache_dir("pychub"))

    # Compute a stable semantic hash from the ChubProject
    build_plan.project_hash = chubproject.mapping_hash()

    # Ensure the BuildPlan's staging dir exists
    project_staging_dir = build_plan.project_staging_dir
    project_staging_dir.mkdir(parents=True, exist_ok=True)

    # Write chubproject.toml using the model's own save logic
    project_path = project_staging_dir / CHUBPROJECT_FILENAME
    ChubProject.save_file(chubproject, path=project_path, overwrite=True)

    # Write a small meta.json that reflects the BuildPlan state
    (project_staging_dir / "meta.json").write_text(json.dumps(build_plan.meta_json, indent=2))

    return project_staging_dir


@audit(StageType.INIT, "parse_chubproject")
def process_chubproject(chubproject_path: Path) -> ChubProject:
    if not chubproject_path.is_file():
        raise FileNotFoundError(f"Chub project file not found: {chubproject_path}")
    return ChubProject.load_from_toml(chubproject_path)


@audit(StageType.INIT, "process_cli_options")
def process_options(args, other_args) -> ChubProject:
    cli_mapping = ChubProject.cli_to_mapping(args, other_args)
    cli_details = {"argv": sys.argv[1:]}
    if args.chubproject:
        chubproject_path = Path(args.chubproject).expanduser().resolve()
        chubproject = process_chubproject(chubproject_path)
        chubproject.merge_from_mapping(
            cli_mapping,
            source=SourceKind.CLI,
            details=cli_details)
        return chubproject
    else:
        return ChubProject.from_mapping(
            cli_mapping,
            source=SourceKind.CLI,
            details=cli_details)


@audit(StageType.INIT, "parse_cli")
def parse_cli() -> tuple[Namespace, list[str]]:
    parser = create_arg_parser()
    return parser.parse_known_args()


@audit(StageType.INIT)
def init_project(chubproject_path: Path | None = None) -> tuple[Path, bool]:
    build_plan = current_build_plan.get()
    namespace, other_args = parse_cli()
    if chubproject_path:
        chubproject = process_chubproject(chubproject_path)
    else:
        chubproject = process_options(namespace, other_args)
    build_plan.project = chubproject
    project_cache_path = cache_project(chubproject)
    must_exit = check_immediate_operations(namespace, chubproject)
    return project_cache_path, must_exit
