from abc import ABC, abstractmethod
from pathlib import Path


class WheelResolutionStrategy(ABC):
    """Resolve a dependency to a wheel file, downloading or copying as needed."""

    name: str
    precedence: int = 100  # lower value = higher precedence

    @abstractmethod
    def resolve(self, dependency: str, output_dir: Path) -> Path:
        """
        Resolve a single dependency as a wheel file on the local file system.

        Args:
            dependency: Canonicalized dependency name (e.g. "requests>=2.0").
            output_dir: Directory where the resolved wheel should be placed.

        Returns:
            Absolute Path to the resolved wheel (.whl).
        Raises:
            ResolutionError if the dependency could not be satisfied.
        """
        raise NotImplementedError
