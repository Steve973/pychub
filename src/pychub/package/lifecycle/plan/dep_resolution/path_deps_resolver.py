from __future__ import annotations

from pathlib import Path
from typing import Dict, List

from pychub.package.lifecycle.plan.dep_resolution.pathdeps import load_strategies
from pychub.package.lifecycle.plan.dep_resolution.pathdeps.path_dep_strategy_base import PathDepStrategy

# --- reader: tomllib on 3.11+, tomli on 3.9–3.10 ---
try:  # pragma: no cover
    # noinspection PyCompatibility
    import tomllib  # Python 3.11+
except ModuleNotFoundError:  # pragma: no cover
    import tomli as tomllib  # type: ignore


def collect_path_dependencies(
    pyproject_path: Path,
    seen: Dict[Path, str] | None = None,
    depth: int = 0) -> Dict[Path, str]:
    """
    Recursively collect all project roots for path dependencies, mapped to
    the strategy label that handled them (e.g. "Poetry", "Hatch", "PDM", "Default").
    """
    if seen is None:
        seen = {}

    pyproject_path = pyproject_path.resolve()
    project_root = pyproject_path.parent

    if project_root in seen:
        return seen

    with pyproject_path.open("rb") as f:
        data = tomllib.load(f)

    strategies: List[PathDepStrategy] = load_strategies()
    claimed = [s for s in strategies if s.can_handle(data)]

    if not claimed:
        # fallback to Default (import here to avoid circular import)
        from pychub.package.lifecycle.plan.dep_resolution.pathdeps.default_strategy import DefaultPathDepStrategy
        strat: PathDepStrategy = DefaultPathDepStrategy()
    elif len(claimed) > 1:
        raise RuntimeError(f"Multiple strategies matched {project_root}")
    else:
        strat = claimed[0]

    label = strat.label()
    seen[project_root] = label

    dep_paths = strat.extract_paths(data, project_root)
    print(f"{'  '*depth}[{label:<6}] {project_root.name} -> {len(dep_paths)} deps")

    for dep_path in dep_paths:
        dep_py = dep_path / "pyproject.toml"
        if not dep_py.is_file():
            raise FileNotFoundError(
                f"[{label}] {dep_path} missing pyproject.toml")
        collect_path_dependencies(dep_py, seen, depth + 1)

    return seen
