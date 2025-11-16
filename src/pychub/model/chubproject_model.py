from __future__ import annotations

import re
from argparse import Namespace
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional, Mapping

from .chubproject_provenance_model import ProvenanceEvent, SourceKind, OperationKind
from ..helper.multiformat_serializable_mixin import MultiformatSerializableMixin
from ..helper.toml_utils import load_toml_text


def _normalize_str_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    if isinstance(value, (list, tuple, set)):
        return [str(v) for v in value]
    # last resort: treat it as a single item
    return [str(value)]


def _normalize_metadata(value: Any) -> dict[str, Any]:
    if value is None:
        return {}
    if isinstance(value, dict):
        return dict(value)
    # if someone passes a list of "k=v" or something weird in a mapping context,
    # you could decide to be clever; for now just coerce to dict-ish or blow up.
    raise TypeError(f"metadata must be a mapping, got {type(value)!r}")


def _select_package_table(doc: Mapping[str, Any], toml_name: str = None) -> Mapping[str, Any] | None:
    # 1) if pyproject.toml, exact [tool.pychub.package] in pyproject.toml
    if toml_name == "pyproject.toml":
        pkg = doc.get("tool", {}).get("pychub", {}).get("package")
        if isinstance(pkg, Mapping):
            if pkg.get("enabled") is False:
                print("WARNING: [tool.pychub.package.enabled] is False -- skipping pychub packaging")
                return None
            else:
                print("INFO: [tool.pychub.package] is enabled -- using pychub packaging")
                return pkg
        else:
            print("WARNING: [tool.pychub.package] not found in pyproject.toml -- skipping pychub packaging")
            return None
    # 2) exact [tool.pychub.package] [pychub.package] or [package] in chubproject.toml
    elif re.fullmatch(r".*chubproject.*\.toml", toml_name):
        pkg = doc.get("tool", doc).get("pychub", doc).get("package")
        if isinstance(pkg, Mapping):
            print(f"INFO: [pychub.package] is enabled in {toml_name} -- using pychub packaging")
            return pkg
        else:
            # 3) flat table in chubproject.toml
            print(f"INFO: flat table found in {toml_name} -- using pychub packaging")
            return doc
    else:
        print(f"WARNING: unrecognized document detected: {toml_name} -- skipping pychub packaging")
        return None


def _determine_table_path(chubproject_path: Path, table_arg: str | None) -> str | None:
    """
    Determine the effective table path to use for loading the config.

    - If the filename is pyproject.toml → always return 'tool.pychub.package'
    - If table_arg is None → always return 'tool.pychub.package' (it is the default)
    - If table_arg == 'flat' → return None (flat table)
    - Else → return the dotted path (e.g., 'pychub.package', 'package')
    """
    default_table = "tool.pychub.package"

    if chubproject_path.name == "pyproject.toml":
        return default_table

    if not re.fullmatch(r"(.*[-_.])?chubproject([-_.].*)?\.toml", chubproject_path.name):
        raise ValueError(f"Invalid chubproject_path: {chubproject_path!r}")

    if table_arg is None:
        return default_table

    normalized_name = table_arg.strip().lower()

    if normalized_name == "flat":
        return None

    if re.fullmatch(r"^(tool\.)?(pychub\.)?package$", normalized_name):
        return normalized_name

    raise ValueError(f"Invalid table_arg: {table_arg!r}")


def _nest_under(table_path: str, value: dict[str, Any]) -> dict[str, Any]:
    """
    Wrap `value` under a dotted table path.

    Example:
      table_path = "tool.pychub.package"
      value = {"name": "foo"}
      -> {"tool": {"pychub": {"package": {"name": "foo"}}}}
    """
    keys = table_path.split(".")
    d: dict[str, Any] = value
    for k in reversed(keys):
        d = {k: d}
    return d


def _coerce_toml_value(x: Any) -> Any:
    """
    Coerce Python values into TOML-writer-friendly types.
    """
    if isinstance(x, Path):
        return x.as_posix()
    if isinstance(x, dict):
        return {str(k): _coerce_toml_value(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [_coerce_toml_value(v) for v in x]
    if isinstance(x, set):
        # stable ordering for sets
        return sorted(_coerce_toml_value(v) for v in x)
    return x


def _parse_metadata_entries(entries: list[str] | None) -> dict[str, list[str]]:
    """
    Turn ['key=val1,val2', 'other=x'] into {'key': ['val1', 'val2'], 'other': ['x']}.
    Adjust if you want scalar vs list behavior.
    """
    if not entries:
        return {}

    result: dict[str, list[str]] = {}
    for raw in entries:
        if "=" not in raw:
            # allow bare keys, treat as an empty list or [""] depending on taste
            key, values = raw, []
        else:
            key, values = raw.split("=", 1)
        key = key.strip()
        if not key:
            continue
        vals = [v.strip() for v in values.split(",")] if values else []
        # merge multiple entries for the same key
        bucket = result.setdefault(key, [])
        for v in vals:
            if v and v not in bucket:
                bucket.append(v)
    return result


class ChubProjectError(Exception):
    pass


@dataclass(slots=True)
class ChubProject(MultiformatSerializableMixin):
    # identity / general
    name: Optional[str] = None
    version: Optional[str] = None
    project_path: Optional[str] = None  # typically "." or a path string

    # chub behavior
    chub: Optional[str] = None
    entrypoint: Optional[str] = None
    entrypoint_args: list[str] = field(default_factory=list)

    verbose: bool = False
    analyze_compatibility: bool = False
    table: Optional[str] = None  # output layout hint
    show_version: bool = False  # -v/--version

    # wheels & extra content
    wheels: list[str] = field(default_factory=list)  # .whl paths or pkg specs
    includes: list[str] = field(default_factory=list)  # raw FILE[::dest] strings
    include_chubs: list[str] = field(default_factory=list)  # other .chub files

    pre_scripts: list[str] = field(default_factory=list)
    post_scripts: list[str] = field(default_factory=list)

    # extra metadata
    metadata: dict[str, Any] = field(default_factory=dict)

    # provenance / audit
    provenance: list[ProvenanceEvent] = field(default_factory=list)

    @classmethod
    def from_mapping(
            cls,
            data: Mapping[str, Any] | None,
            *,
            source: Optional[SourceKind] = None,
            details: Optional[dict[str, Any]] = None) -> "ChubProject":
        data = data or {}

        inst = cls(
            # scalars
            name=data.get("name"),
            version=data.get("version"),
            project_path=data.get("project_path"),
            chub=data.get("chub"),
            entrypoint=data.get("entrypoint"),
            verbose=bool(data.get("verbose", False)),
            analyze_compatibility=bool(data.get("analyze_compatibility", False)),
            table=data.get("table"),
            show_version=bool(data.get("show_version", False)),

            # lists
            wheels=_normalize_str_list(data.get("wheels")),
            entrypoint_args=_normalize_str_list(data.get("entrypoint_args")),
            includes=_normalize_str_list(data.get("includes")),
            include_chubs=_normalize_str_list(data.get("include_chubs")),
            pre_scripts=_normalize_str_list(data.get("pre_scripts") or (data.get("scripts") or {}).get("pre")),
            post_scripts=_normalize_str_list(data.get("post_scripts") or (data.get("scripts") or {}).get("post")),

            # metadata
            metadata=_normalize_metadata(data.get("metadata")),
        )

        if source is not None:
            inst.provenance.append(
                ProvenanceEvent(
                    source=source,
                    operation=OperationKind.INIT,
                    details=details or {},
                )
            )

        return inst

    def merge_from_mapping(
            self,
            data: Mapping[str, Any] | None,
            *,
            source: Optional[SourceKind] = None,
            details: Optional[dict[str, Any]] = None) -> None:
        if not data:
            return

        # ---- Scalars: incoming overrides if present ----
        scalar_fields = (
            "name",
            "version",
            "project_path",
            "chub",
            "entrypoint",
            "verbose",
            "analyze_compatibility",
            "table",
            "show_version",
        )
        for field_name in scalar_fields:
            if field_name in data:
                setattr(self, field_name, data[field_name])

        # ---- lists: union + dedupe (existing first) ----
        def _merge_list(attr: str, key: str | None = None) -> None:
            mapping_key = key or attr
            if mapping_key not in data:
                return
            existing = getattr(self, attr) or []
            incoming = _normalize_str_list(data[mapping_key])
            combined: list[str] = []
            seen = set()
            for item in existing + incoming:
                if item not in seen:
                    seen.add(item)
                    combined.append(item)
            setattr(self, attr, combined)

        list_fields = (
            "wheels",
            "entrypoint_args",
            "includes",
            "include_chubs",
        )
        for prop in list_fields:
            _merge_list(prop)

        list_fields_with_key = (
            "pre_scripts",
            "post_scripts",
        )
        for prop in list_fields_with_key:
            _merge_list(prop, key=prop)

        # Also support legacy "scripts" mapping in the incoming data
        scripts_tbl = data.get("scripts") or {}
        if scripts_tbl:
            _merge_list("pre_scripts", key=None if "pre_scripts" in data else "pre")
            _merge_list("post_scripts", key=None if "post_scripts" in data else "post")

        # ---- dict: metadata per-key merge ----
        incoming_meta = data.get("metadata")
        if incoming_meta is not None:
            incoming_meta = _normalize_metadata(incoming_meta)
            for k, v_in in incoming_meta.items():
                v_existing = self.metadata.get(k)
                # If either side is not a list, treat as scalar and let incoming win
                if not isinstance(v_existing, list) or not isinstance(v_in, list):
                    self.metadata[k] = v_in
                else:
                    # both lists: union + dedupe
                    combined = []
                    seen = set()
                    for item in list(v_existing) + list(v_in):
                        key = repr(item)
                        if key not in seen:
                            seen.add(key)
                            combined.append(item)
                    self.metadata[k] = combined

        # ---- provenance ----
        if source is not None:
            self.provenance.append(
                ProvenanceEvent(
                    source=source,
                    operation=OperationKind.MERGE_EXTEND,
                    details=details or {},
                )
            )

    def override_from_mapping(
            self,
            data: Mapping[str, Any] | None,
            *,
            source: Optional[SourceKind] = None,
            details: Optional[dict[str, Any]] = None) -> None:
        if not data:
            return

        # Scalars: override if present
        scalar_fields = (
            "name",
            "version",
            "project_path",
            "chub",
            "entrypoint",
            "verbose",
            "analyze_compatibility",
            "table",
            "show_version",
        )
        for field_name in scalar_fields:
            if field_name in data:
                setattr(self, field_name, data[field_name])

        # lists: replace wholesale if present
        list_fields = (
            "wheels",
            "entrypoint_args",
            "includes",
            "include_chubs",
            "pre_scripts",
            "post_scripts",
        )
        for prop in list_fields:
            if prop in data:
                setattr(self, prop, _normalize_str_list(data[prop]))

        scripts_tbl = data.get("scripts") or {}
        if scripts_tbl:
            if "pre" in scripts_tbl and "pre_scripts" not in data:
                self.pre_scripts = _normalize_str_list(scripts_tbl["pre"])
            if "post" in scripts_tbl and "post_scripts" not in data:
                self.post_scripts = _normalize_str_list(scripts_tbl["post"])

        # dict: metadata replace if present
        if "metadata" in data:
            self.metadata = _normalize_metadata(data["metadata"])

        # provenance
        if source is not None:
            self.provenance.append(
                ProvenanceEvent(
                    source=source,
                    operation=OperationKind.MERGE_OVERRIDE,
                    details=details or {},
                )
            )

    def to_mapping(self) -> dict[str, Any]:
        """
        Serialize to a plain mapping suitable for TOML/JSON, preserving the
        existing chubproject/chubconfig shape.
        """
        return {
            "name": self.name,
            "version": self.version,
            "project_path": self.project_path,
            "wheels": list(self.wheels),
            "chub": self.chub,
            "entrypoint": self.entrypoint,
            "entrypoint_args": list(self.entrypoint_args),
            "includes": list(self.includes),
            "include_chubs": list(self.include_chubs),
            "verbose": self.verbose,
            "metadata": dict(self.metadata),
            "scripts": {
                "pre": list(self.pre_scripts),
                "post": list(self.post_scripts),
            },
        }

    @staticmethod
    def load_from_toml(
            path: Path,
            *,
            source: SourceKind = SourceKind.FILE) -> ChubProject:
        """
        Read TOML from `path`, use existing table-selection logic to find the
        packaging config mapping, and build a ChubProject from it.
        """
        doc = load_toml_text(path.read_text(encoding="utf-8"))
        package_mapping = _select_package_table(doc, path.name)
        if package_mapping is None:
            raise ChubProjectError(f"No pychub config found in {path}")
        return ChubProject.from_mapping(
            package_mapping,
            source=source,
            details={"file": str(path)},
        )

    @staticmethod
    def cli_to_mapping(args: Namespace, other_args: list[str]) -> dict[str, object]:
        """
        Normalize argparse.Namespace into the ChubProject.from_mapping() shape.
        Field names match the ChubProject dataclass fields.
        """
        return {
            # scalars
            "project_path": args.project_path,
            "chub": args.chub,
            "entrypoint": args.entrypoint,
            "verbose": bool(args.verbose),
            "analyze_compatibility": bool(args.analyze_compatibility),
            "show_version": bool(args.version),
            "table": args.table,

            # lists
            "wheels": args.wheel or [],
            "includes": args.include or [],
            "include_chubs": args.include_chub or [],
            "pre_scripts": args.pre_script or [],
            "post_scripts": args.post_script or [],
            # we keep using the “extra args” as entrypoint_args, like before
            "entrypoint_args": other_args or [],

            # metadata as a dict
            "metadata": _parse_metadata_entries(args.metadata_entry),
        }

    @staticmethod
    def save_file(
            project: ChubProject | dict[str, Any],
            path: str | Path = "chubproject.toml",
            *,
            table_arg: str | None = None,
            overwrite: bool = False,
            make_parents: bool = True) -> Path:
        """
        Serialize a ChubProject (or raw mapping) to TOML and write it to `path`.

        - If `table_path` is a dotted path (e.g. "tool.pychub.package"),
          the options mapping is nested under that table.
        - If `table_path` is None (e.g., when determine_table_path(...) returns None),
          the options mapping is written flat at the root.
        - If `path` exists and `overwrite` is False, raises ChubProjectError.
        """
        if _TOML_WRITER is None:
            raise ChubProjectError(
                "Saving requires a TOML writer. Install one of:\n"
                "  pip install tomli-w   # preferred\n"
                "  pip install tomlkit   # also works\n"
                "  pip install toml      # legacy"
            )

        # accept either a ChubProject or a raw mapping
        if isinstance(project, ChubProject):
            obj = project.to_mapping()
        else:
            obj = ChubProject.from_mapping(project).to_mapping()

        # strip out None-valued keys, keep False/[], {}
        obj = {k: v for k, v in obj.items() if v is not None}

        p = Path(path).expanduser().resolve()
        table_path = _determine_table_path(p, table_arg)

        if table_path is not None:
            obj = _nest_under(table_path, obj)
        # else: flat mode, obj is already the root-level mapping

        if p.exists() and not overwrite:
            raise ChubProjectError(f"Refusing to overwrite without overwrite=True: {p}")
        if make_parents:
            p.parent.mkdir(parents=True, exist_ok=True)

        text = _TOML_WRITER.dumps(_coerce_toml_value(obj))  # type: ignore[attr-defined]
        p.write_text(text, encoding="utf-8")
        return p
