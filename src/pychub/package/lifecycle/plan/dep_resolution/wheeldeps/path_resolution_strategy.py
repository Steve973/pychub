import shutil
from pathlib import Path

from pychub.package.lifecycle.plan.dep_resolution.path_deps_resolver import collect_path_dependencies
from pychub.package.lifecycle.plan.dep_resolution.wheeldeps.wheel_resolution_strategy_base import \
    WheelResolutionStrategy


class PathResolutionStrategy(WheelResolutionStrategy):
    """Resolves wheels from local path dependencies (Poetry, PDM, Hatch, etc.)."""

    name = "path"
    precedence = 60

    def resolve(self, dependency: str, output_dir: Path) -> list[Path]:
        """
        Given a project path (with a pyproject.toml), collect all nested path
        dependencies and copy their built wheels into output_dir.

        Returns the path to the root project's wheel.
        """
        output_dir.mkdir(parents=True, exist_ok=True)

        project_root = Path(dependency).resolve()
        pyproject_path = (
            project_root if project_root.name == "pyproject.toml"
            else project_root / "pyproject.toml"
        )
        if not pyproject_path.is_file():
            raise FileNotFoundError(f"No pyproject.toml found at {pyproject_path}")

        # Use your existing recursive collector
        path_map: dict[Path, str] = collect_path_dependencies(pyproject_path)

        wheel_paths = []
        for proj_path, label in path_map.items():
            dist_dir = proj_path / "dist"
            for wheel in dist_dir.glob("*.whl"):
                dst = output_dir / wheel.name
                if not dst.exists():
                    shutil.copy2(wheel, dst)
                wheel_paths.append(dst)

        if not wheel_paths:
            raise RuntimeError(f"No wheels found in path dependencies for {project_root}")

        # For now, return the root project wheel
        # (later the planner may attach all of them)
        return [wheel_paths[0].resolve()]
