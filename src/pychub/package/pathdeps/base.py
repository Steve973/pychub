from abc import ABC, abstractmethod
from pathlib import Path
from typing import List


class PathDepStrategy(ABC):
    @staticmethod
    @abstractmethod
    def label() -> str: ...

    @staticmethod
    @abstractmethod
    def can_handle(data: dict) -> bool: ...

    @staticmethod
    @abstractmethod
    def extract_paths(data: dict, project_root: Path) -> List[Path]: ...
