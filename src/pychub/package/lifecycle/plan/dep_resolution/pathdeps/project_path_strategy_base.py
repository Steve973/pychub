from abc import ABC, abstractmethod
from pathlib import Path


class ProjectPathStrategy(ABC):
    name: str
    precedence: int = 100  # lower value = higher precedence

    @staticmethod
    @abstractmethod
    def can_handle(data: dict) -> bool: ...

    @staticmethod
    @abstractmethod
    def extract_paths(data: dict, project_root: Path) -> list[Path]: ...
