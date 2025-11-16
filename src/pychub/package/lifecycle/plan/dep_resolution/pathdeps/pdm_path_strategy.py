from pathlib import Path

from .project_path_strategy_base import ProjectPathStrategy


class PdmProjectPathStrategy(ProjectPathStrategy):
    """Extracts path dependencies from [tool.pdm.dependencies]."""

    name = "pdm"
    precedence = 70

    @staticmethod
    def can_handle(data: dict) -> bool:
        tool = data.get("tool", {}) or {}
        tool_pdm = tool.get("pdm", {}) or {}
        return "dependencies" in tool_pdm

    @staticmethod
    def extract_paths(data: dict, project_root: Path) -> list[Path]:
        tool = data.get("tool", {}) or {}
        tool_pdm = tool.get("pdm", {}) or {}
        tool_pdm_dependencies = tool_pdm.get("dependencies", {}) or {}
        out: list[Path] = []
        for _, val in tool_pdm_dependencies.items():
            if isinstance(val, dict) and "path" in val:
                out.append((project_root / val["path"]).resolve())
        return out
