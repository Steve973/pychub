from pathlib import Path

from .project_path_strategy_base import ProjectPathStrategy


class PoetryProjectPathStrategy(ProjectPathStrategy):

    name = "poetry"
    precedence = 50

    @staticmethod
    def can_handle(data: dict) -> bool:
        return "poetry" in (data.get("tool", {}) or {})

    @staticmethod
    def extract_paths(data: dict, project_root: Path) -> list[Path]:
        tool = data.get("tool", {}) or {}
        tool_poetry = tool.get("poetry", {}) or {}
        tool_poetry_dependencies = tool_poetry.get("dependencies", {}) or {}
        return [
            (project_root / val["path"]).resolve()
            for _, val in tool_poetry_dependencies.items()
            if isinstance(val, dict) and "path" in val
        ]
