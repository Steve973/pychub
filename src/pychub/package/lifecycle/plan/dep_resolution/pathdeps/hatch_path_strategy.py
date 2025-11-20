from pathlib import Path

from .project_path_strategy_base import ProjectPathStrategy


class HatchProjectPathStrategy(ProjectPathStrategy):
    """
    Defines a strategy for handling project configurations specifically related to projects
    that use the Hatch tool. This strategy evaluates and processes configuration data
    for such projects.

    Attributes:
        name (str): The name of the strategy, used to identify it as "hatch".
        precedence (int): A numeric value indicating the priority of this strategy. Lower
            values signify higher precedence when multiple strategies are considered.
    """

    name = "hatch"
    precedence = 60  # lower value = higher precedence

    @staticmethod
    def can_handle(data: dict) -> bool:
        """
        Determines if the provided data dictionary can be handled by verifying the existence
        of a specific section (`hatch`) in the `[tool]` section and a `dependencies` section in
        the `[project]` section.

        Args:
            data (dict): A dictionary containing project configuration data.

        Returns:
            bool: True if the data contains a `hatch` section in `tool` and `dependencies`
            in `project`, otherwise False.
        """
        # Hatch projects must have a [tool.hatch] section, but deps live in [project]
        tool = data.get("tool", {}) or {}
        project = data.get("project", {}) or {}
        return "hatch" in tool and "dependencies" in project

    @staticmethod
    def extract_paths(data: dict, project_root: Path) -> list[Path]:
        """
        Extract paths from project dependencies specified in the given data.

        This method processes the dependencies of a project defined within the `data`
        dictionary. Each dependency may include a "path" key specifying a relative
        path. The method resolves these paths against the given `project_root` and
        returns a list of absolute `Path` objects.

        Args:
            data (dict): The dictionary containing project data. It is expected to
                have a "project" key with a "dependencies" subkey, which is a list
                of dependency objects.
            project_root (Path): The root path of the project, used as the base
                directory to resolve relative paths of dependencies.

        Returns:
            list[Path]: A list of resolved absolute `Path` objects representing the
            paths of the project dependencies.
        """
        project = data.get("project", {}) or {}
        project_deps = project.get("dependencies", []) or []
        out: list[Path] = []
        for dep in project_deps:
            if isinstance(dep, dict) and "path" in dep:
                out.append((project_root / dep["path"]).resolve())
        return out
