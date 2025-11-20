from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Mapping

from ..helper.multiformat_serializable_mixin import MultiformatSerializableMixin


class ScriptType(str, Enum):
    PRE = "pre"
    POST = "post"


@dataclass(slots=True, frozen=True)
class ScriptSpec(MultiformatSerializableMixin):
    src: Path
    script_type: ScriptType

    def __post_init__(self):
        resolved = self.src.expanduser().resolve()
        if not resolved.is_file():
            raise FileNotFoundError(f"Script not found: {resolved}")
        object.__setattr__(self, "src", resolved)

    @property
    def name(self) -> str:
        return self.src.name

    @staticmethod
    def from_mapping(m: Mapping[str, Any] | None) -> "ScriptSpec":
        if not m:
            raise ValueError("Empty script mapping")
        src = Path(m["src"])
        script_type = ScriptType(m["script_type"])
        return ScriptSpec(src, script_type)

    def to_mapping(self) -> dict[str, str]:
        return {
            "src": str(self.src),
            "script_type": self.script_type.value
        }


@dataclass(slots=True, frozen=True)
class Scripts(MultiformatSerializableMixin):
    _items: list[ScriptSpec] = field(default_factory=list)

    @staticmethod
    def dedup(items: list[ScriptSpec]) -> list[ScriptSpec]:
        seen: set[tuple[str, ScriptType]] = set()
        out: list[ScriptSpec] = []
        for s in items:
            key = (str(s.src), s.script_type)
            if key in seen:
                continue
            seen.add(key)
            out.append(s)
        return out

    @classmethod
    def merged(cls, *scripts_objs: "Scripts") -> "Scripts":
        all_items: list[ScriptSpec] = []
        for s in scripts_objs:
            if s:
                all_items.extend(s.items)
        return cls(_items=cls.dedup(all_items))

    @staticmethod
    def from_mapping(m: Mapping[str, list[dict[str, str]]] | None) -> "Scripts":
        if not m:
            return Scripts()
        return Scripts([
            ScriptSpec.from_mapping(x)
            for t in ScriptType
            for x in (m.get(t.value) or [])
        ])

    def to_mapping(self) -> dict[str, list[dict[str, str]]]:
        return {
            "pre": [x.to_mapping() for x in self.pre],
            "post": [x.to_mapping() for x in self.post]
        }

    @property
    def pre(self) -> list[ScriptSpec]:
        return [i for i in self._items if i.script_type == ScriptType.PRE]

    @property
    def post(self) -> list[ScriptSpec]:
        return [i for i in self._items if i.script_type == ScriptType.POST]

    @property
    def items(self):
        return self._items
