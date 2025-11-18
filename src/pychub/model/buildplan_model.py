from __future__ import annotations

import datetime
from dataclasses import dataclass, field
from importlib.metadata import version as get_version
from pathlib import Path
from typing import Any, Mapping

import yaml
from appdirs import user_cache_dir

from pychub.model.chubproject_model import ChubProject
from .build_event import BuildEvent
from .includes_model import Includes
from .scripts_model import Scripts
from .wheels_model import WheelCollection
from ..helper.multiformat_serializable_mixin import MultiformatSerializableMixin
from ..package.constants import CHUB_INCLUDES_DIR, CHUB_SCRIPTS_DIR, RUNTIME_DIR, CHUB_BUILD_DIR, CHUB_LIBS_DIR, \
    CHUBCONFIG_FILENAME, CHUB_WHEELS_DIR


@dataclass(slots=True, frozen=False)
class BuildPlan(MultiformatSerializableMixin):
    """
    Represents the resolved plan and staging metadata for building a .chub archive.

    The BuildPlan includes the original ChubProject definition, the staging directory,
    and a flattened list of completed stages (and optional substages) in the form
    of strings like "INIT:load_config" or "PLAN:COMPLETE".
    """

    # The audit log of events that occurred during the build process
    audit_log: list[BuildEvent] = field(default_factory=list)
    # Path to the top-level pychub staging/cache directory
    cache_root: Path = field(default_factory=Path)
    # When the build plan was created
    created_at: datetime.datetime = field(default_factory=lambda: datetime.datetime.now(datetime.timezone.utc))
    # Included files to be staged in the build
    include_files: Includes = field(default_factory=Includes)
    # Scripts to be staged in the build
    install_scripts: Scripts = field(default_factory=Scripts)
    # Wheels to be staged in the build
    wheels: WheelCollection = field(default_factory=WheelCollection)
    # Additional metadata for the build
    metadata: dict[str, Any] = field(default_factory=dict)
    # The ChubProject definition
    project: ChubProject = field(default_factory=ChubProject)
    # Path to the wheel project directory
    project_dir: Path = field(default_factory=Path)
    # Becomes a directory under the staging directory for this chub project
    project_hash: str = field(default="")
    # The version of pychub that created this plan
    pychub_version: str = field(default_factory=lambda: get_version("pychub"))

    # ------------------------------------------------------------------ #
    # Construction helpers
    # ------------------------------------------------------------------ #

    @staticmethod
    def from_mapping(m: Mapping[str, Any]) -> BuildPlan:
        project = ChubProject.from_mapping(m["project"]) if "project" in m else None
        if project is None:
            raise ValueError("BuildPlan requires a nested 'project' mapping")

        return BuildPlan(
            audit_log=list(m.get("audit_log", [])),
            cache_root=Path(m.get("cache_root", str(user_cache_dir("pychub")))),
            created_at=datetime.datetime.fromisoformat(
                m.get("created_at", datetime.datetime.now(datetime.timezone.utc).isoformat())
            ),
            metadata=dict(m.get("metadata") or {}),
            project=project,
            project_dir=Path(m.get("project_dir") or "."),
            project_hash=m.get("project_hash", ""),
            pychub_version=m.get("pychub_version", get_version("pychub")))

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

    def to_mapping(self, include_derived: bool = False) -> dict[str, Any]:
        """
        Return a dict representing the state of this BuildPlan.
        By default, it only includes core fields required for round-trip persistence.
        If `include_derived` is True, adds all computed/convenience fields
        (i.e., derived properties such as directory paths) for compatibility
        or interop with consumers that don't recalculate them.
        """
        core = {
            "audit_log": [e.to_mapping() for e in self.audit_log],
            "cache_root": str(self.cache_root),
            "created_at": str(self.created_at.isoformat()),
            "metadata": dict(self.metadata),
            "project": self.project.to_mapping(),
            "project_dir": str(self.project_dir),
            "project_hash": self.project_hash,
            "pychub_version": self.pychub_version,
        }
        derived = {}
        if include_derived:
            derived.update({
                "project_staging_dir": str(self.project_staging_dir),
                "staged_wheels_dir": str(self.staged_wheels_dir),
                "staged_includes_dir": str(self.staged_includes_dir),
                "staged_scripts_dir": str(self.staged_scripts_dir),
                "staged_runtime_dir": str(self.staged_runtime_dir),
                "build_dir": str(self.build_dir),
                "bundled_libs_dir": str(self.bundled_libs_dir),
                "bundled_includes_dir": str(self.bundled_includes_dir),
                "bundled_scripts_dir": str(self.bundled_scripts_dir),
                "bundled_runtime_dir": str(self.bundled_runtime_dir),
                "bundled_chubconfig_path": str(self.bundled_chubconfig_path),
            })
        return {**core, **derived}

    # ------------------------------------------------------------------ #
    # Validation
    # ------------------------------------------------------------------ #

    def validate(self) -> None:
        validations = {
            'audit_log': (list, 'audit_log list[BuildEvent]'),
            'cache_root': (Path, 'cache_root Path'),
            'created_at': (datetime.datetime, 'created_at datetime'),
            'metadata': (dict, 'metadata dict'),
            'project': (ChubProject, 'ChubProject'),
            'project_dir': (Path, 'project_dir Path'),
            'project_hash': (str, 'project_hash str'),
            'pychub_version': (str, 'pychub_version str'),
        }

        for attr_name, (expected_type, type_desc) in validations.items():
            value = getattr(self, attr_name)
            if not isinstance(value, expected_type):
                raise ValueError(f"expected {type_desc}, got {type(value)}")

        # Special validation for audit_log contents
        if not all(isinstance(i, BuildEvent) for i in self.audit_log):
            raise ValueError("each entry in 'audit_log' must be a BuildEvent")

    # ------------------------------------------------------------------ #
    # Properties
    # ------------------------------------------------------------------ #

    @property
    def project_staging_dir(self) -> Path:
        return self.cache_root / self.project_hash

    @property
    def staged_wheels_dir(self) -> Path:
        """Where wheels are first staged."""
        return self.project_staging_dir / CHUB_WHEELS_DIR

    @property
    def staged_includes_dir(self) -> Path:
        """Where includes are initially copied for staging."""
        return self.project_staging_dir / CHUB_INCLUDES_DIR

    @property
    def staged_scripts_dir(self) -> Path:
        """Where scripts are staged."""
        return self.project_staging_dir / CHUB_SCRIPTS_DIR

    @property
    def staged_runtime_dir(self) -> Path:
        """Where runtime files are staged."""
        return self.project_staging_dir / RUNTIME_DIR

    @property
    def build_dir(self) -> Path:
        """Root of the final build structure (from which .chub is assembled)."""
        return self.project_staging_dir / CHUB_BUILD_DIR

    @property
    def bundled_libs_dir(self) -> Path:
        """libs/ in the final build dir"""
        return self.build_dir / CHUB_LIBS_DIR

    @property
    def bundled_includes_dir(self) -> Path:
        return self.build_dir / CHUB_INCLUDES_DIR

    @property
    def bundled_scripts_dir(self) -> Path:
        return self.build_dir / CHUB_SCRIPTS_DIR

    @property
    def bundled_runtime_dir(self) -> Path:
        return self.build_dir / RUNTIME_DIR

    @property
    def bundled_chubconfig_path(self) -> Path:
        return self.build_dir / CHUBCONFIG_FILENAME

    @property
    def meta_json(self) -> dict[str, Any]:
        return {
            "pychub_version": self.pychub_version,
            "created_at": self.created_at.isoformat(),
            "project_hash": self.project_hash,
        }
