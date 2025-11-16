from pathlib import Path

from .project_path_strategy_base import ProjectPathStrategy


class HatchProjectPathStrategy(ProjectPathStrategy):
    """Extracts path dependencies from [project.dependencies] (Hatch uses PEP 621)."""

    name = "hatch"
    precedence = 60

    @staticmethod
    def can_handle(data: dict) -> bool:
        # Hatch projects must have a [tool.hatch] section, but deps live in [project]
        tool = data.get("tool", {}) or {}
        project = data.get("project", {}) or {}
        return "hatch" in tool and "dependencies" in project

    @staticmethod
    def extract_paths(data: dict, project_root: Path) -> list[Path]:
        project = data.get("project", {}) or {}
        project_deps = project.get("dependencies", []) or []
        out: list[Path] = []
        for dep in project_deps:
            if isinstance(dep, dict) and "path" in dep:
                out.append((project_root / dep["path"]).resolve())
        return out
