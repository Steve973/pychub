from __future__ import annotations

import shutil

from pychub.model.build_event import StageType, audit
from pychub.package.lifecycle.execute.bundler import _get_build_plan


@audit(stage=StageType.EXECUTE, substage="copy_runtime_files")
def copy_runtime_files() -> None:
    """
    Copies runtime resources from the staged directory to the bundled destination.

    This function retrieves the build plan, identifies the staged runtime resources
    directory, and copies its contents to the designated bundled runtime directory.
    If the staged runtime directory does not exist, it assumes that runtime resources
    are currently optional and exits without performing any operations.

    Returns:
        None
    """
    plan = _get_build_plan()
    staged_runtime = plan.staged_runtime_dir
    runtime_dest = plan.bundled_runtime_dir

    if not staged_runtime.exists():
        # Runtime resources are optional for now.
        return

    shutil.copytree(staged_runtime, runtime_dest, dirs_exist_ok=True)
