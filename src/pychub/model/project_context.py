from __future__ import annotations

from dataclasses import field
from pathlib import Path
from typing import Any, Optional, Dict, List, Tuple

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from dataclasses import dataclass as dataclass
else:
    from .dataclass_shim import dataclass


@dataclass(slots=True, frozen=True)
class ProjectContext:
    project_dir: Path
    entrypoint: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    wheel_paths: List[Path] = field(default_factory=list)
    post_scripts: List[Tuple[Path, str]] = field(default_factory=list)
    pre_scripts: List[Tuple[Path, str]] = field(default_factory=list)
    includes: List[str] = field(default_factory=list)
