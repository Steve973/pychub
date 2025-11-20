from pathlib import Path

from .project_path_strategy_base import ProjectPathStrategy


class PdmProjectPathStrategy(ProjectPathStrategy):
    """
    Represents a strategy for extracting project paths specific to PDM (Python Dependency Manager).

    This class provides methods to determine if PDM dependencies are present in a given project
    configuration and extract dependency paths relative to the project root. The strategies
    defined here are specific to the structure used by PDM in the "tool.pdm" section of project
    metadata.

    Attributes:
        name (str): The name of the strategy, set to "pdm".
        precedence (int): Determines the priority of the strategy. Lower values mean higher
            precedence, with the default value set to 70.
    """

    name = "pdm"
    precedence = 70  # lower value = higher precedence

    @staticmethod
    def can_handle(data: dict) -> bool:
        """
        Determines if the given input data can be handled based on the presence
        of "dependencies" within the "pdm" section of the "tool" dictionary.

        Args:
            data (dict): The input data dictionary to be evaluated.

        Returns:
            bool: True if the input data contains "dependencies" under the "pdm"
                section of the "tool" dictionary, False otherwise.
        """
        tool = data.get("tool", {}) or {}
        tool_pdm = tool.get("pdm", {}) or {}
        return "dependencies" in tool_pdm

    @staticmethod
    def extract_paths(data: dict, project_root: Path) -> list[Path]:
        """
        Extracts dependency paths specified in a dictionary structure.

        This function parses a nested dictionary structure to extract paths to
        dependencies defined under "tool.pdm.dependencies". When a dependency is a
        dictionary and contains a "path" key, the path is resolved relative to the
        `project_root` and added to the output list.

        Args:
            data (dict): A dictionary containing project configuration, potentially
                including dependency information under the keys "tool.pdm.dependencies".
            project_root (Path): The root directory of the project as a Path object,
                used to resolve relative paths to absolute paths.

        Returns:
            list[Path]: A list of absolute paths corresponding to the dependencies
            defined with paths in the input `data`.

        """
        tool = data.get("tool", {}) or {}
        tool_pdm = tool.get("pdm", {}) or {}
        tool_pdm_dependencies = tool_pdm.get("dependencies", {}) or {}
        out: list[Path] = []
        for _, val in tool_pdm_dependencies.items():
            if isinstance(val, dict) and "path" in val:
                out.append((project_root / val["path"]).resolve())
        return out
