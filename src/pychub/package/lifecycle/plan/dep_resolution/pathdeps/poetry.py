from pathlib import Path
from typing import List
from .path_dep_strategy_base import PathDepStrategy

class PoetryPathDepStrategy(PathDepStrategy):

    @staticmethod
    def label() -> str:
        return "Poetry"

    @staticmethod
    def can_handle(data: dict) -> bool:
        return "poetry" in (data.get("tool", {}) or {})

    @staticmethod
    def extract_paths(data: dict, project_root: Path) -> List[Path]:
        tool = data.get("tool", {}) or {}
        tool_poetry = tool.get("poetry", {}) or {}
        tool_poetry_dependencies = tool_poetry.get("dependencies", {}) or {}
        return [
            (project_root / val["path"]).resolve()
            for _, val in tool_poetry_dependencies.items()
            if isinstance(val, dict) and "path" in val
        ]
