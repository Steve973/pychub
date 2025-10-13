from __future__ import annotations

import json
from dataclasses import field
from pathlib import Path
from pickle import compatible_formats
from typing import Any, Dict, List, Mapping, Optional
from typing import TYPE_CHECKING

import yaml

from pychub.model.scripts_model import Scripts

if TYPE_CHECKING:
    from dataclasses import dataclass as dataclass
else:
    from .dataclass_shim import dataclass


@dataclass(slots=True, frozen=True)
class ChubConfig:
    name: str
    version: str
    entrypoint: Optional[str] = None
    wheels: Dict[str, List[str]] = field(default_factory=dict)
    includes: List[str] = field(default_factory=list)
    scripts: Scripts = field(default_factory=Scripts)
    compatibility: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    @staticmethod
    def from_mapping(m: Mapping[str, Any]) -> "ChubConfig":
        name = str(m.get("name", "")).strip()
        version = str(m.get("version", "")).strip()
        entrypoint = m.get("entrypoint")
        wheels_raw = m.get("wheels") or {}
        wheels = {
            str(k): [str(x) for x in (v or [])] for k, v in wheels_raw.items()
        }
        includes = [str(x) for x in (m.get("includes") or [])]
        scripts = Scripts.from_mapping(m.get("scripts"))
        compatibility = dict(m.get("compatibility") or {})
        metadata = dict(m.get("metadata") or {})

        cfg = ChubConfig(
            name=name,
            version=version,
            entrypoint=str(entrypoint) if entrypoint is not None else None,
            wheels=wheels,
            includes=includes,
            scripts=scripts,
            compatibility=compatibility,
            metadata=metadata)
        cfg.validate()
        return cfg

    @classmethod
    def from_yaml(cls, s: str) -> "ChubConfig":
        if yaml is None:
            raise RuntimeError("PyYAML not installed")
        obj = next(iter(yaml.safe_load_all(s)), None) or {}
        return cls.from_mapping(obj)

    @classmethod
    def from_file(cls, path: str | Path) -> "ChubConfig":
        p = Path(path)
        text = p.read_text(encoding="utf-8")
        return cls.from_yaml(text)

    def to_mapping(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "version": self.version,
            "entrypoint": self.entrypoint,
            "scripts": self.scripts.to_mapping(),
            "includes": list(self.includes),
            "wheels": {k: list(v) for k, v in self.wheels.items()},
            "compatibility": dict(self.compatibility),
            "metadata": dict(self.metadata),
        }

    def to_json(self, *, indent: int = 2) -> str:
        return json.dumps(self.to_mapping(), ensure_ascii=False, indent=indent)

    def to_yaml(self) -> str:
        if yaml is None:
            raise RuntimeError("PyYAML not installed")
        return yaml.safe_dump(self.to_mapping(), sort_keys=False, allow_unicode=True)

    def validate(self) -> None:
        if not self.name:
            raise ValueError("name is required")
        if not self.version:
            raise ValueError("version is required")
        for w, deps in self.wheels.items():
            if not w.endswith(".whl"):
                raise ValueError(f"wheel key must end with .whl: {w}")
            for d in deps:
                if not d.endswith(".whl"):
                    raise ValueError(f"dependency must end with .whl: {d}")
        # Keep the entrypoint a single token, and actual arg parsing happens at run.
        if self.entrypoint and (" " in self.entrypoint):
            raise ValueError("entrypoint must be a single token")
