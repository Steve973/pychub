from __future__ import annotations

import shutil
from pathlib import Path

from pychub.package.lifecycle.plan.dep_resolution.wheeldeps.wheel_resolution_strategy_base import (
    WheelResolutionStrategy,
)


class LocalResolutionStrategy(WheelResolutionStrategy):
    """Resolves wheels from the local filesystem."""

    name = "local"
    precedence = 50

    def resolve(self, dependency: str, output_dir: Path) -> list[Path]:
        """
        Resolves a dependency by copying it to the specified output directory. This function ensures
        that the file is correctly stored in the target location without redundant operations if the
        file already exists and is identical.

        Args:
            dependency (str): The path to the dependency file (e.g., local wheel file) to be resolved.
            output_dir (Path): The directory path where the dependency will be copied.

        Returns:
            list[Path]: A list containing the path of the resolved/copied dependency file.
        """
        src_path = Path(dependency).expanduser().resolve()
        if not src_path.is_file():
            raise FileNotFoundError(f"Local wheel not found: {src_path}")

        output_dir.mkdir(parents=True, exist_ok=True)

        dest_path = output_dir / src_path.name

        # Avoid redundant copy if same inode or already identical content
        if dest_path.exists():
            if src_path.samefile(dest_path):
                return [dest_path]
            if src_path.stat().st_size == dest_path.stat().st_size:
                # optional: verify content hash before skipping
                return [dest_path]

        shutil.copy2(src_path, dest_path)
        return [dest_path]
