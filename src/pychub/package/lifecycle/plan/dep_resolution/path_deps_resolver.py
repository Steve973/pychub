from __future__ import annotations

from pathlib import Path

from pychub.helper.toml_utils import load_toml_file
from pychub.package.lifecycle.plan.dep_resolution.pathdeps.project_path_strategy_base import ProjectPathStrategy
from pychub.package.lifecycle.plan.dep_resolution.pathdeps.project_path_strategy_registry import \
    load_strategies


def collect_path_dependencies(
        pyproject_path: Path,
        seen: dict[Path, str] | None = None,
        depth: int = 0) -> dict[Path, str]:
    """
    Collects and resolves path dependencies for a project by analyzing its
    pyproject.toml file and applying appropriate strategies.

    This function iteratively inspects the specified pyproject.toml file and
    recursively resolves dependencies based on the project structure. It supports
    multiple path resolution strategies and ensures each unique project root is
    processed only once.

    Args:
        pyproject_path (Path): The path to the pyproject.toml file to process.
        seen (dict[Path, str] | None): A dictionary to track already processed
            project roots and their corresponding resolution strategy labels. If
            None, a new dictionary will be initialized.
        depth (int): The current recursion depth used for logging purposes.

    Returns:
        dict[Path, str]: A dictionary containing resolved project roots as keys
        and their corresponding strategy labels as values.

    Raises:
        RuntimeError: If multiple strategies match the same project root.
        FileNotFoundError: If a discovered dependency lacks a pyproject.toml file.
    """
    if seen is None:
        seen = {}

    pyproject_path = pyproject_path.resolve()
    project_root = pyproject_path.parent

    if project_root in seen:
        return seen

    data = load_toml_file(pyproject_path)

    strategies: list[ProjectPathStrategy] = load_strategies()
    claimed = [s for s in strategies if s.can_handle(data)]

    if not claimed:
        # fallback to Default (import here to avoid circular import)
        from pychub.package.lifecycle.plan.dep_resolution.pathdeps.default_path_strategy import DefaultProjectPathStrategy
        strat: ProjectPathStrategy = DefaultProjectPathStrategy()
    elif len(claimed) > 1:
        raise RuntimeError(f"Multiple strategies matched {project_root}")
    else:
        strat = claimed[0]

    label = strat.name
    seen[project_root] = label

    dep_paths = strat.extract_paths(data, project_root)

    for dep_path in dep_paths:
        dep_py = dep_path / "pyproject.toml"
        if not dep_py.is_file():
            raise FileNotFoundError(
                f"[{label}] {dep_path} missing pyproject.toml")
        collect_path_dependencies(dep_py, seen, depth + 1)

    return seen
