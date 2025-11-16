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

    def resolve(self, dependency: str, output_dir: Path) -> Path:
        """
        Given a local wheel path, resolve it and copy it into output_dir.

        Returns the path to the wheel within output_dir.
        """
        src_path = Path(dependency).expanduser().resolve()
        if not src_path.is_file():
            raise FileNotFoundError(f"Local wheel not found: {src_path}")

        output_dir.mkdir(parents=True, exist_ok=True)

        dest_path = output_dir / src_path.name

        # Avoid redundant copy if same inode or already identical content
        if dest_path.exists():
            if src_path.samefile(dest_path):
                return dest_path
            if src_path.stat().st_size == dest_path.stat().st_size:
                # optional: verify content hash before skipping
                return dest_path

        shutil.copy2(src_path, dest_path)
        return dest_path
