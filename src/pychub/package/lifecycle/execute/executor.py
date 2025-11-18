import sys
from importlib.metadata import PackageNotFoundError, version as get_version
from pathlib import Path

from pychub.model.build_event import audit, StageType
from pychub.model.chubproject_model import ChubProject
from pychub.package.lifecycle.execute.bundler import bundle_chub


@audit(StageType.EXECUTE, substage="execute_analyze_compatibility")
def execute_analyze_compatibility(chubproject: ChubProject):
    raise NotImplementedError("This feature is not yet implemented.")


@audit(StageType.EXECUTE, substage="execute_chubproject_save")
def execute_chubproject_save(chubproject: ChubProject, path: Path | str):
    ChubProject.save_file(chubproject, path, overwrite=True, make_parents=True)


@audit(StageType.EXECUTE, substage="execute_version")
def execute_version():
    print(f"Python: {sys.version.split()[0]}")
    try:
        version = get_version("pychub")
    except PackageNotFoundError:
        version = "(source)"
    print(f"pychub: {version}")


@audit(StageType.EXECUTE)
def execute_build() -> Path:
    return bundle_chub()
