from abc import ABC, abstractmethod
from pathlib import Path


class ProjectPathStrategy(ABC):
    """
    Provides an abstract base class for implementing project path handling strategies.

    This class serves as a blueprint for defining behavior related to handling data
    and extracting paths based on specific criteria. Subclasses should implement the
    abstract methods to provide concrete functionality for assessing whether the strategy
    is applicable to particular data and extracting relevant paths accordingly.

    Attributes:
        name (str): The name of the strategy, identifying its purpose or role.
        precedence (int): A ranking used to determine the priority of the strategy. Lower
            values represent higher precedence.
    """

    name: str
    precedence: int = 100  # lower value = higher precedence

    @staticmethod
    @abstractmethod
    def can_handle(data: dict) -> bool:
        """
        Determines if a specific handler can process the given data.

        This abstract method should be implemented by subclasses to define the
        logic for determining whether the subclass can handle the provided data.

        Args:
            data (dict): The data to be analyzed by the handler.

        Returns:
            bool: True if the handler can process the given data, False otherwise.
        """
        ...

    @staticmethod
    @abstractmethod
    def extract_paths(data: dict, project_root: Path) -> list[Path]:
        """
        Extracts and returns a list of paths from the provided data structure.

        The method is designed to analyze the provided data dictionary and extract
        relevant paths relative to the project root. The output is a list of Path
        objects corresponding to the determined file or directory locations.

        Args:
            data (dict): A dictionary structure containing information from which
                paths are to be extracted. The actual keys and content depend on the
                specific implementation.
            project_root (Path): The root directory of the project. This path serves
                as the base for resolving relative paths from the data dictionary.

        Returns:
            list[Path]: A list of Path objects representing resolved paths extracted
            from the input data.

        """
        ...
