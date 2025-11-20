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
        Resolves a dependency and copies relevant wheel files to the output directory.

        This method identifies the dependencies of a given project via its
        pyproject.toml file, collects wheel files from all associated paths, and
        places these wheel files into the defined output directory.

        Args:
            dependency (str): The path to the project or the `pyproject.toml` file
                containing the dependency definitions.
            output_dir (Path): The directory where the resolved wheel files will be
                copied.

        Returns:
            list[Path]: A list of resolved absolute paths for the wheel files.

        Raises:
            FileNotFoundError: If no `pyproject.toml` file is found at the specified
                dependency path.
            RuntimeError: If no wheel files are found in the path dependencies.
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
