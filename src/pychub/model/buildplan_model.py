from __future__ import annotations

import datetime
import json
from dataclasses import field
from importlib.metadata import version as get_version
from pathlib import Path
from typing import Any, Dict, Mapping, TYPE_CHECKING

import yaml

from pychub.model.chubproject_model import ChubProject
from .build_event import BuildEvent

if TYPE_CHECKING:
    from dataclasses import dataclass as dataclass
else:
    from .dataclass_shim import dataclass


@dataclass(slots=True, frozen=False)
class BuildPlan:
    """
    Represents the resolved plan and staging metadata for building a .chub archive.

    The BuildPlan includes the original ChubProject definition, the staging directory,
    and a flattened list of completed stages (and optional substages) in the form
    of strings like "INIT:load_config" or "PLAN:COMPLETE".
    """

    # The ChubProject definition
    project: ChubProject = field(default_factory=ChubProject)
    # Becomes a directory under the staging directory for this chub project
    project_hash: str = field(default="")
    # Path to the wheel project directory
    project_dir: Path = field(default_factory=Path)
    # Path to the top-level pychub staging/cache directory
    staging_dir: Path = field(default_factory=Path)
    # Staging directory for wheels under the chub project hash directory
    wheels_dir: str = field(default="wheels")
    # The software bill of materials (SBOM) file path
    sbom: str = field(default="sbom.json")
    # When the build plan was created
    created_at: datetime.datetime = field(
        default_factory=lambda: datetime.datetime.now(datetime.timezone.utc)
    )
    # The version of pychub that created this plan
    pychub_version: str = field(default_factory=lambda: get_version("pychub"))
    # The audit log of events that occurred during the build process
    audit_log: list[BuildEvent] = field(default_factory=list)
    # Additional metadata for the build
    metadata: Dict[str, Any] = field(default_factory=dict)

    # ------------------------------------------------------------------ #
    # Construction helpers
    # ------------------------------------------------------------------ #

    @staticmethod
    def from_mapping(m: Mapping[str, Any]) -> BuildPlan:
        project = ChubProject.from_mapping(m["project"]) if "project" in m else None
        if project is None:
            raise ValueError("BuildPlan requires a nested 'project' mapping")

        return BuildPlan(
            project=project,
            project_hash=m.get("project_hash", ""),
            project_dir=Path(m.get("project_dir") or "."),
            staging_dir=Path(m.get("staging_dir") or None),
            wheels_dir=m.get("wheels_dir", "wheels"),
            sbom=m.get("sbom", "sbom.json"),
            created_at=datetime.datetime.fromisoformat(
                m.get("created_at", datetime.datetime.now(datetime.timezone.utc).isoformat())
            ),
            pychub_version=m.get("pychub_version", get_version("pychub")),
            audit_log=list(m.get("audit_log", [])),
            metadata=dict(m.get("metadata") or {}))

    @classmethod
    def from_yaml(cls, s: str) -> BuildPlan:
        if yaml is None:
            raise RuntimeError("PyYAML not installed")
        obj = next(iter(yaml.safe_load_all(s)), None) or {}
        return cls.from_mapping(obj)

    @classmethod
    def from_file(cls, path: str | Path) -> BuildPlan:
        p = Path(path)
        text = p.read_text(encoding="utf-8")
        return cls.from_yaml(text)

    # ------------------------------------------------------------------ #
    # Serialization
    # ------------------------------------------------------------------ #

    def to_mapping(self) -> Dict[str, Any]:
        return {
            "project": self.project.to_mapping(),
            "project_hash": self.project_hash,
            "project_dir": str(self.project_dir),
            "staging_dir": str(self.staging_dir),
            "wheels_dir": self.wheels_dir,
            "sbom": self.sbom,
            "created_at": self.created_at.isoformat(),
            "pychub_version": self.pychub_version,
            "audit_log": list(self.audit_log),
            "metadata": dict(self.metadata),
        }

    def to_json(self, *, indent: int = 2) -> str:
        return json.dumps(self.to_mapping(), ensure_ascii=False, indent=indent)

    def to_yaml(self) -> str:
        if yaml is None:
            raise RuntimeError("PyYAML not installed")
        return yaml.safe_dump(self.to_mapping(), sort_keys=False, allow_unicode=True)

    # ------------------------------------------------------------------ #
    # Validation
    # ------------------------------------------------------------------ #

    def validate(self) -> None:
        if not isinstance(self.project, ChubProject):
            raise ValueError(f"expected ChubProject, got {type(self.project)}")
        if not isinstance(self.project_dir, Path):
            raise ValueError(f"expected project_dir Path, got {type(self.project_dir)}")
        if not isinstance(self.staging_dir, Path):
            raise ValueError(f"expected staging_dir Path, got {type(self.staging_dir)}")
        if not isinstance(self.metadata, dict):
            raise ValueError(f"expected metadata dict, got {type(self.metadata)}")
        if not isinstance(self.audit_log, list):
            raise ValueError(f"expected audit_log list[BuildEvent], got {type(self.audit_log)}")
        if not all(isinstance(i, BuildEvent) for i in self.audit_log):
            raise ValueError("each entry in 'audit_log' must be a BuildEvent")
