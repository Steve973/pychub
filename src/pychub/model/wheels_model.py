from __future__ import annotations

import hashlib
import zipfile
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Iterable, Iterator, Mapping

from packaging.requirements import Requirement
from packaging.tags import Tag
from packaging.tags import parse_tag
from packaging.utils import parse_wheel_filename
from packaging.version import Version

from pychub.helper.multiformat_serializable_mixin import MultiformatSerializableMixin
from .wheelinfo_model import WheelInfo


class WheelSourceType(str, Enum):
    PATH = "PATH"        # Supplied from the local filesystem
    PROJECT = "PROJECT"  # Found as a dependency of another local wheel
    PYPI = "PYPI"        # Downloaded from PyPI
    BUILT = "BUILT"      # Locally built artifact


class WheelRoleType(str, Enum):
    PRIMARY = "PRIMARY"        # The main subject of the build
    DEPENDENCY = "DEPENDENCY"  # Required by the primary wheel
    INCLUDED = "INCLUDED"      # Extra wheel intentionally bundled


@dataclass
class WheelArtifact(MultiformatSerializableMixin):
    path: Path
    name: str
    version: Version
    tags: set[Tag]
    requires: list[str] = field(default_factory=list)
    dependencies: list["WheelArtifact"] = field(default_factory=list)
    source: WheelSourceType | None = None
    role: WheelRoleType | None = None
    hash: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    # -------------------------------------------------------------------------
    # Factories
    # -------------------------------------------------------------------------

    @classmethod
    def from_path(
        cls,
        path: Path,
        *,
        is_primary: bool = False,
        source: WheelSourceType | str = WheelSourceType.PATH) -> WheelArtifact:
        """
        Load metadata, dependencies, and tags from a wheel file.
        """
        path = Path(path).expanduser().resolve()
        if not path.is_file():
            raise FileNotFoundError(f"Wheel not found: {path}")

        # Parse filename for name/version/tags
        try:
            name, version, build, tags_set = parse_wheel_filename(path.name)
        except Exception as e:
            raise ValueError(f"Invalid wheel filename: {path.name} ({e})")

        tags = set(tags_set)

        # Compute hash for reproducibility
        sha = hashlib.sha256()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                sha.update(chunk)
        wheel_hash = sha.hexdigest()

        # Parse METADATA for requirements and extra info
        requires, metadata = cls._parse_metadata(path)

        return cls(
            path=path,
            name=name.replace("_", "-").lower(),
            version=version,
            tags=tags,
            requires=requires,
            source=WheelSourceType(source) if not isinstance(source, WheelSourceType) else source,
            role=WheelRoleType.PRIMARY if is_primary else WheelRoleType.DEPENDENCY,
            hash=wheel_hash,
            metadata=metadata)

    @classmethod
    def from_wheel_info(
            cls,
            info: WheelInfo,
            *,
            is_primary: bool = False,
            source: WheelSourceType | str = WheelSourceType.PATH) -> "WheelArtifact":
        """
        Build a WheelArtifact directly from a pre-parsed WheelInfo.
        This bypasses ZIP parsing when the wheel's metadata has already been
        extracted and normalized by WheelInfo.build_from_wheel().
        """
        path = Path(info.filename)
        version = Version(info.version)
        tags = set().union(*(parse_tag(t) for t in info.tags))
        wheel_source = source if isinstance(source, WheelSourceType) else WheelSourceType(source)
        wheel_role = WheelRoleType.PRIMARY if is_primary else WheelRoleType.DEPENDENCY

        # The 'requires_dist' lines from WheelInfo.meta contain dependency specs.
        # Fall back to the "extras" mapping if none are found.
        requires = list(info.meta.get("requires_dist", []))
        if not requires and info.extras:
            for reqs in info.extras.extras.values():
                requires.extend(reqs)

        return cls(
            path=path,
            name=info.name.lower().replace("_", "-"),
            version=version,
            tags=tags,
            requires=requires,
            source=wheel_source,
            role=wheel_role,
            hash=info.sha256,
            metadata=info.meta)

    # -------------------------------------------------------------------------
    # Helpers
    # -------------------------------------------------------------------------

    @staticmethod
    def _parse_metadata(path: Path) -> tuple[list[str], dict[str, Any]]:
        """Extract `Requires-Dist` and selected metadata fields."""
        requires: list[str] = []
        meta: dict[str, Any] = {}

        with zipfile.ZipFile(path) as zf:
            meta_file = next((f for f in zf.namelist() if f.endswith("METADATA")), None)
            if not meta_file:
                return requires, meta
            with zf.open(meta_file) as fh:
                for line in fh:
                    decoded = line.decode("utf-8", errors="replace").strip()
                    if decoded.startswith("Requires-Dist:"):
                        req = decoded.split(":", 1)[1].strip()
                        try:
                            Requirement(req)  # validate
                            requires.append(req)
                        except Exception:
                            continue
                    elif ":" in decoded:
                        key, val = decoded.split(":", 1)
                        if key in {"Author", "Summary", "Home-page", "License"}:
                            meta[key.lower().replace("-", "_")] = val.strip()
        return requires, meta

    # -------------------------------------------------------------------------
    # Properties / views
    # -------------------------------------------------------------------------

    @property
    def is_universal(self) -> bool:
        """Returns True if the wheel is universal (has a `py3-none-any` tag)."""
        if not self.tags:
            return False
        return any(t.interpreter == "py3" and t.abi == "none" and t.platform == "any" for t in self.tags)

    def to_mapping(self) -> dict[str, Any]:
        """Produce a serializable summary."""
        return {
            "path": str(self.path),
            "name": self.name,
            "version": self.version,
            "tags": list(self.tags),
            "hash": self.hash,
            "is_universal": self.is_universal,
            "requires": self.requires,
            "source": self.source,
            "role": self.role,
            "metadata": self.metadata,
        }

    # -------------------------------------------------------------------------
    # Methods for set/dict operations
    # -------------------------------------------------------------------------

    def __hash__(self):
        # Unique by file name only
        return hash(self.path.name)

    def __eq__(self, other):
        if isinstance(other, WheelArtifact):
            return self.path.name == other.path.name
        return NotImplemented


@dataclass
class WheelCollection(MultiformatSerializableMixin):
    _wheels: set[WheelArtifact] = field(default_factory=set)

    # ------- Properties -------

    @property
    def primary(self) -> list[WheelArtifact]:
        return [w for w in self._wheels if w.role == WheelRoleType.PRIMARY]

    @property
    def dependencies(self) -> list[WheelArtifact]:
        return [w for w in self._wheels if w.role == WheelRoleType.DEPENDENCY]

    @property
    def included(self) -> list[WheelArtifact]:
        return [w for w in self._wheels if w.role == WheelRoleType.INCLUDED]

    @property
    def sources(self) -> set:
        return {w.source for w in self._wheels if w.source is not None}

    @property
    def all_tag_sets(self) -> list[set[Tag]]:
        return [w.tags for w in self._wheels]

    @property
    def supported_combos(self) -> set[Tag]:
        tag_sets = self.all_tag_sets
        if not tag_sets:
            return set()
        return set.intersection(*tag_sets)

    @property
    def is_fully_universal(self) -> bool:
        return all(w.is_universal for w in self._wheels)

    @property
    def supported_target_strings(self) -> list[str]:
        combos = self.supported_combos
        return sorted(WheelCollection._tag_to_str(t) for t in combos)

    # ------- Static / Class Methods -------

    @staticmethod
    def _tag_to_str(tag: Tag) -> str:
        return f"{tag.interpreter}-{tag.abi}-{tag.platform}"

    @staticmethod
    def _is_universal(tag: Tag) -> bool:
        return tag.interpreter == "py3" and tag.abi == "none" and tag.platform == "any"

    @classmethod
    def from_iterable(cls, artifacts: Iterable[WheelArtifact]) -> "WheelCollection":
        return cls(set(artifacts))

    # ------- Utility Methods -------

    def __contains__(self, artifact: WheelArtifact) -> bool:
        return artifact in self._wheels

    def __len__(self) -> int:
        return len(self._wheels)

    def __iter__(self) -> Iterator[WheelArtifact]:
        return iter(self._wheels)

    def add(self, artifact: WheelArtifact) -> None:
        self._wheels.add(artifact)

    def extend(self, artifacts: Iterable[WheelArtifact]) -> None:
        self._wheels.update(artifacts)

    def by_source(self, source: WheelSourceType) -> list[WheelArtifact]:
        return [w for w in self._wheels if w.source == source]

    def find(self, name: str, version: Version | None = None) -> list[WheelArtifact]:
        return [
            w for w in self._wheels
            if w.name == name and (version is None or w.version == version)
        ]

    def validate_buildable(self) -> None:
        if not self.supported_combos:
            raise ValueError("No common compatibility target across wheel artifacts.")

    def to_mapping(self) -> Mapping[str, object]:
        return {
            "count": len(self),
            "is_fully_universal": self.is_fully_universal,
            "supported_targets": self.supported_target_strings,
            "artifacts": [w.to_mapping() for w in self],
        }
