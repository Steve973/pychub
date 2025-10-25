from pathlib import Path
from typing import List
from .base import PathDepStrategy


class PdmPathDepStrategy(PathDepStrategy):
    """Extracts path dependencies from [tool.pdm.dependencies]."""

    @staticmethod
    def label() -> str:
        return "PDM"

    @staticmethod
    def can_handle(data: dict) -> bool:
        tool = data.get("tool", {}) or {}
        tool_pdm = tool.get("pdm", {}) or {}
        return "dependencies" in tool_pdm

    @staticmethod
    def extract_paths(data: dict, project_root: Path) -> List[Path]:
        tool = data.get("tool", {}) or {}
        tool_pdm = tool.get("pdm", {}) or {}
        tool_pdm_dependencies = tool_pdm.get("dependencies", {}) or {}
        out: List[Path] = []
        for _, val in tool_pdm_dependencies.items():
            if isinstance(val, dict) and "path" in val:
                out.append((project_root / val["path"]).resolve())
        return out
