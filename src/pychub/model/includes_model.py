from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping, Optional

from ..helper.multiformat_serializable_mixin import MultiformatSerializableMixin


@dataclass(slots=True, frozen=True)
class IncludeSpec(MultiformatSerializableMixin):
    src: Path  # absolute
    dest: Optional[str] = None  # bundle-relative target (e.g., "docs/", "etc/file.txt")

    def __post_init__(self):
        resolved = self.src.expanduser().resolve()
        if not resolved.is_file():
            raise FileNotFoundError(f"Included file not found: {resolved}")
        object.__setattr__(self, "src", resolved)

    @property
    def name(self) -> str:
        return self.dest or self.src.name

    @staticmethod
    def parse(item: str | Mapping[str, Any], *, base_dir: Path = os.getcwd()) -> "IncludeSpec":
        if isinstance(item, str):
            if "::" in item:
                s, d = item.split("::", 1)
                src_raw, dest = s.strip(), (d.strip() or None)
            else:
                src_raw, dest = item.strip(), None
        else:
            src_raw = str(item["src"]).strip()
            dest = (None if item.get("dest") in (None, "") else str(item["dest"]))
        src = Path(src_raw)
        src = src if src.is_absolute() else (base_dir / src).expanduser().resolve()
        if not src.is_file():
            raise FileNotFoundError(f"Included file not found: {src}")
        return IncludeSpec(src=src, dest=dest)

    @staticmethod
    def dedup(a: list[IncludeSpec], b: list[IncludeSpec]) -> list[IncludeSpec]:
        seen: set[tuple[str, Optional[str]]] = set()
        out: list[IncludeSpec] = []
        for spec in [*(a or []), *(b or [])]:
            key = (str(spec.src), spec.dest)
            if key not in seen:
                seen.add(key)
                out.append(spec)
        return out

    def to_mapping(self) -> dict[str, Any]:
        return {
            "src": str(self.src),
            "dest": self.dest if self.dest else self.src.name,
        }

    def __str__(self) -> str:
        return f"{self.src}::{self.dest}" if self.dest else str(self.src)

    def resolved_dest(self, includes_dir: Path) -> Path:
        return includes_dir / self.name


@dataclass(slots=True, frozen=True)
class Includes(MultiformatSerializableMixin):
    _items: list[IncludeSpec] = field(default_factory=list)

    @staticmethod
    def from_toml(items: list[str | Mapping[str, Any]] | None, *, base_dir: Path) -> "Includes":
        if not items:
            return Includes()
        return Includes([IncludeSpec.parse(x, base_dir=base_dir) for x in items])

    def to_toml_inline(self) -> list[str]:
        return [str(i) for i in self._items]

    def to_mapping(self) -> list[dict[str, Any]]:
        # JSON/YAML-friendly (fully explicit)
        return [i.to_mapping() for i in self._items]

    @property
    def paths(self) -> list[Path]:
        return [i.src for i in self._items]

    def resolved_dests(self, includes_dir: Path) -> list[Path]:
        return [i.resolved_dest(includes_dir) for i in self._items]
