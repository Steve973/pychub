from pathlib import Path

from .project_path_strategy_base import ProjectPathStrategy


class PoetryProjectPathStrategy(ProjectPathStrategy):
    """
    Represents a strategy for handling project paths specific to the poetry configuration.

    This class specializes in determining whether a given project configuration
    is compatible with Poetry and extracting paths defined under the Poetry configuration.
    It provides methods to validate and extract dependencies paths relative to the project root.

    Attributes:
        name (str): The name of the strategy.
        precedence (int): The precedence level of this strategy, with lower values indicating
            higher priority.
    """

    name = "poetry"
    precedence = 50  # lower value = higher precedence

    @staticmethod
    def can_handle(data: dict) -> bool:
        """
        Determines if the given data dictionary contains "poetry" as part of its configuration.

        The method checks if the "poetry" key is present within the "tool" key of the provided
        dictionary and returns a boolean indicating whether it can handle the provided data.

        Args:
            data (dict): A dictionary to inspect, expected to have a "tool" key containing
                nested configuration data.

        Returns:
            bool: True if the "poetry" key exists in the "tool" section of the dictionary,
            otherwise False.
        """
        return "poetry" in (data.get("tool", {}) or {})

    @staticmethod
    def extract_paths(data: dict, project_root: Path) -> list[Path]:
        """
        Extracts and resolves paths for dependencies defined in a given configuration.

        This method extracts the file paths of dependencies from a specific configuration
        (`tool.poetry.dependencies`) in the provided data dictionary. It then resolves these
        paths based on the project root. This is primarily intended to handle dependencies
        with a "path" attribute.

        Args:
            data (dict): A dictionary containing configuration data, typically including
                `tool.poetry.dependencies` where dependencies and their paths are defined.
            project_root (Path): The root directory of the project, used to resolve relative
                dependency paths.

        Returns:
            list[Path]: A list of resolved file paths for dependencies that include a "path"
                attribute in the configuration.
        """
        tool = data.get("tool", {}) or {}
        tool_poetry = tool.get("poetry", {}) or {}
        tool_poetry_dependencies = tool_poetry.get("dependencies", {}) or {}
        return [
            (project_root / val["path"]).resolve()
            for _, val in tool_poetry_dependencies.items()
            if isinstance(val, dict) and "path" in val
        ]
