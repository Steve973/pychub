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
    includes: List[str] = field(default_factory=list)
    scripts: Scripts = field(default_factory=Scripts)
    pinned_wheels: List[str] = field(default_factory=list)
    targets: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    @staticmethod
    def from_mapping(m: Mapping[str, Any]) -> "ChubConfig":
        name = str(m.get("name", "")).strip()
        version = str(m.get("version", "")).strip()
        entrypoint = m.get("entrypoint")
        includes = [str(x) for x in (m.get("includes") or [])]
        scripts = Scripts.from_mapping(m.get("scripts"))
        pinned_wheels = [str(x) for x in (m.get("pinned_wheels") or [])]
        targets = [str(x) for x in (m.get("targets") or [])]
        metadata = dict(m.get("metadata") or {})

        cfg = ChubConfig(
            name=name,
            version=version,
            entrypoint=str(entrypoint) if entrypoint is not None else None,
            includes=includes,
            scripts=scripts,
            pinned_wheels=pinned_wheels,
            targets=targets,
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
            "pinned_wheels": list(self.pinned_wheels),
            "targets": list(self.targets),
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
        for pinned_wheel in self.pinned_wheels:
            dep_parts = pinned_wheel.split("==")
            if len(dep_parts) != 2:
                raise ValueError(f"pinned wheel must be in the format 'name==ver': {pinned_wheel}")
        # Keep the entrypoint a single token, and actual arg parsing happens at run.
        if self.entrypoint and (" " in self.entrypoint):
            raise ValueError("entrypoint must be a single token")
