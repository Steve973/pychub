from abc import ABC, abstractmethod
from pathlib import Path


class WheelResolutionStrategy(ABC):
    """Resolve a dependency to a wheel file, downloading or copying as needed."""

    name: str
    precedence: int = 100  # lower value = higher precedence

    @abstractmethod
    def resolve(self, dependency: str, output_dir: Path) -> list[Path]:
        """
        An abstract base class that defines the interface for resolving a dependency
        to its concrete output paths. Subclasses are expected to implement the abstract
        method `resolve` to provide specific resolution behavior.

        Args:
            dependency (str): The dependency identifier or name that needs to be
                resolved.
            output_dir (Path): The directory where the resolved dependencies should
                be placed.

        Returns:
            list[Path]: A list of resolved file paths for the given dependency.

        Raises:
            NotImplementedError: If the `resolve` method is not implemented by a
                subclass.
        """
        raise NotImplementedError
