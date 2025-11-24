from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping, Optional

import yaml

from pychub.model.scripts_model import Scripts
from ..helper.multiformat_deserializable_mixin import MultiformatDeserializableMixin
from ..helper.multiformat_serializable_mixin import MultiformatSerializableMixin


@dataclass(slots=True, frozen=True)
class ChubConfig(MultiformatSerializableMixin, MultiformatDeserializableMixin):
    name: str
    version: str
    entrypoint: Optional[str] = None
    includes: list[str] = field(default_factory=list)
    scripts: Scripts = field(default_factory=Scripts)
    pinned_wheels: list[str] = field(default_factory=list)
    targets: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_mapping(cls, mapping: Mapping[str, Any], **_: Any) -> ChubConfig:
        name = str(mapping.get("name", "")).strip()
        version = str(mapping.get("version", "")).strip()
        entrypoint = mapping.get("entrypoint")
        includes = [str(x) for x in (mapping.get("includes") or [])]
        scripts = Scripts.from_mapping(mapping.get("scripts"))
        pinned_wheels = [str(x) for x in (mapping.get("pinned_wheels") or [])]
        targets = [str(x) for x in (mapping.get("targets") or [])]
        metadata = dict(mapping.get("metadata") or {})

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

    def to_mapping(self) -> dict[str, Any]:
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
