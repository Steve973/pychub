from __future__ import annotations

import shutil
from pathlib import Path

from pychub.model.build_event import audit, StageType
from pychub.package.lifecycle.execute.bundler import _get_build_plan


@audit(stage=StageType.EXECUTE, substage="copy_wheels")
def copy_wheels_into_libs() -> list[Path]:
    """
    Copies all wheel files from the staged directory into the directory of bundled libraries.

    This function retrieves the build plan and identifies the staged wheels directory and the
    target-bundled libraries directory. It ensures that the directory containing the staged
    wheel files exists, then iterates through all the `.whl` files in the directory, copying
    each one into the target-bundled libraries directory. It also ensures that the required
    directories in the target location are created if they do not already exist. The function
    returns a sorted list of paths to the copied wheel files.

    Returns:
        list[Path]: A sorted list of paths to the copied wheel files.

    Raises:
        FileNotFoundError: If the directory containing the staged wheel files does not exist.
    """
    plan = _get_build_plan()
    staged_root = plan.staged_wheels_dir
    libs_dir = plan.bundled_libs_dir

    if not staged_root.exists():
        raise FileNotFoundError(f"Missing staged wheels at {staged_root}")

    copied: list[Path] = []
    for wheel_path in staged_root.rglob("*.whl"):
        dest = libs_dir / wheel_path.name
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(wheel_path, dest)
        copied.append(dest)

    return sorted(copied)
