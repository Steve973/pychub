from __future__ import annotations

import json
import os
import re
import zipfile
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Tuple
from typing import TYPE_CHECKING

import yaml

from pychub.model.includes_model import IncludeSpec
from pychub.model.scripts_model import Scripts

if TYPE_CHECKING:
    from dataclasses import dataclass as dataclass
else:
    from .dataclass_shim import dataclass

# --- reader: tomllib on 3.11+, tomli on 3.9–3.10 ---
try:  # pragma: no cover
    # noinspection PyCompatibility
    import tomllib  # Python 3.11+
except ModuleNotFoundError:  # pragma: no cover
    import tomli as tomllib  # type: ignore

# --- optional writers: pick any writer to be installed ---
_TOML_WRITER = None
for _name in ("tomli_w", "tomlkit", "toml"):  # pragma: no cover
    try:
        _TOML_WRITER = __import__(_name)
        break
    except ModuleNotFoundError:
        pass


class ChubProjectError(Exception):
    pass


def get_wheel_name_version(wheel_path: Path) -> tuple[str, str]:
    if wheel_path is None:
        raise ValueError("Cannot get wheel name and version: no wheel path provided")
    with zipfile.ZipFile(wheel_path) as zf:
        metadata_file = next((f for f in zf.namelist() if f.endswith('METADATA')), None)
        if metadata_file is None:
            raise ValueError("No METADATA file found in wheel")

        with zf.open(metadata_file) as f:
            for line in f:
                decoded = line.decode('utf-8')
                if decoded.startswith("Name: "):
                    name = decoded.split("Name: ", 1)[1].strip()
                elif decoded.startswith("Version: "):
                    version = decoded.split("Version: ", 1)[1].strip()
                if 'name' in locals() and 'version' in locals():
                    return name, version

    raise ValueError("Name and Version not found in wheel METADATA")


@dataclass(slots=True)
class ChubProject:
    # flat fields (one-shot build config)
    name: Optional[str] = None
    version: Optional[str] = None
    project_path: Optional[str] = None
    wheels: Optional[List[str]] = None
    chub: Optional[str] = None
    entrypoint: Optional[str] = None
    entrypoint_args: Optional[list[str]] = None
    includes: List["IncludeSpec"] = None
    include_chubs: List[str] = None
    verbose: bool = False
    metadata: Dict[str, Any] = None
    scripts: Scripts = None

    # ------------------- factories -------------------

    @staticmethod
    def from_mapping(m: Mapping[str, Any] | None) -> "ChubProject":
        """One-shot: build directly from a *package-like* mapping (no namespacing here)."""
        if not m:
            return ChubProject(wheels=[], includes=[], metadata={}, scripts=Scripts())
        project_path = m.get("project_path") or os.getcwd()
        wheels = m.get("wheel") or []
        main_wheel = wheels[0] if wheels else None
        wheel_name, wheel_version = get_wheel_name_version(Path(main_wheel)) if main_wheel else (None, None)
        name = m.get("name") or wheel_name
        version = m.get("version") or wheel_version
        includes = [IncludeSpec.parse(item) for item in (m.get("includes") or [])]
        include_chubs = m.get("include_chubs") or []

        return ChubProject(
            name=name,
            version=version,
            project_path=project_path,
            wheels=wheels,
            chub=str(m["chub"]) if m.get("chub") else None,
            entrypoint=str(m["entrypoint"]) if m.get("entrypoint") else None,
            entrypoint_args=m.get("entrypoint_args", []),
            includes=includes,
            include_chubs=include_chubs,
            verbose=bool(m.get("verbose", False)),
            metadata=dict(m.get("metadata") or {}),
            scripts=Scripts.from_mapping(m.get("scripts")))

    @staticmethod
    def from_toml_document(doc: Mapping[str, Any], toml_name: str = None) -> "ChubProject":
        """
        Load with flexible namespacing:
          1) [tool.pychub.package] if pyproject.toml
          2) [tool.pychub.package] or [pychub.package] or [package] if chubproject.toml
          3) the entire document if the previous namespace is not found, and is chubproject.toml
        """
        tbl = ChubProject._select_package_table(doc, toml_name)
        return ChubProject.from_mapping(tbl)

    @staticmethod
    def from_cli_args(args: Mapping[str, Any]) -> "ChubProject":
        """
        One-shot build config from parsed CLI options (no "append" semantics).
        Expected canonical keys (per README):
          wheel, chub, entrypoint, verbose,
          add_wheel (repeatable),
          include (repeatable),
          pre_script (repeatable), post_script (repeatable),
          metadata_entry (repeatable)
        """
        # scalars
        chub = args.get("chub") if args.get("chub") else None
        entrypoint = str(args.get("entrypoint")) if args.get("entrypoint") else None
        verbose = bool(args.get("verbose", False))
        project_path = str(args.get("project_path")) if args.get("project_path") else os.getcwd()

        # lists
        wheels = str(args.get("wheel")) if args.get("wheel") else []
        main_wheel = wheels[0] if wheels else None
        wheel_name, wheel_version = get_wheel_name_version(Path(main_wheel)) if main_wheel else (None, None)
        name = args.get("name") or wheel_name
        spdx_licenses = args.get("spdx_license") or []
        version = args.get("version") or wheel_version

        # entrypoint args: --entrypoint-args (repeatable)
        entrypoint_args = args.get("entrypoint_args") or []

        # includes: --include (list or comma-separated)
        inc_raw = args.get("include") or []
        includes = [IncludeSpec.parse(s) for s in ChubProject._comma_split_maybe(inc_raw)]

        # Chub files to include: --include-chub (repeatable)
        include_chubs = args.get("include_chub") or []

        # scripts: --pre-script, --post-script
        pre = ChubProject._comma_split_maybe(ChubProject._flatten(args.get("pre_script")))
        post = ChubProject._comma_split_maybe(ChubProject._flatten(args.get("post_script")))
        scripts = Scripts.from_mapping({"pre": [str(x) for x in pre], "post": [str(x) for x in post]})

        # metadata: --metadata-entry key=value (repeatable/CSV)
        metadata: Dict[str, Any] = {}

        for item in (args.get("metadata_entry") or []):
            s = item[0] if isinstance(item, (list, tuple)) else item
            s = str(s).strip()
            sep = "=" if "=" in s else None
            if not sep:
                raise ValueError(f"--metadata-entry must be key=value (got {item!r})")

            k, v = s.split(sep, 1)
            k = k.strip()
            v = v.strip()

            metadata[k] = [p.strip() for p in v.split(",")] if "," in v else v

        return ChubProject(
            name=name,
            version=version,
            project_path=project_path,
            wheels=wheels,
            chub=chub,
            entrypoint=entrypoint,
            entrypoint_args=entrypoint_args,
            includes=includes,
            include_chubs=include_chubs,
            verbose=verbose,
            metadata=metadata,
            scripts=scripts)

    # ------------------- immutable merges -------------------

    @staticmethod
    def merge_from_cli_args(existing: "ChubProject", args: Mapping[str, Any]) -> "ChubProject":
        """
        Additive merge (less heavy-handed):
          - scalars: keep existing unless provided
          - lists: extend + dedup (preserve order)
          - scripts: extend pre/post if provided in args
          - metadata: add keys; existing keys win
        """
        inc = ChubProject.from_cli_args(args)

        name = existing.name if inc.name is None else inc.name
        version = existing.version if inc.version is None else inc.version
        project_path = existing.project_path if inc.project_path is None else inc.project_path

        wheels = existing.wheels + inc.wheels if inc.wheels else existing.wheels
        chub = inc.chub or existing.chub
        entrypoint = existing.entrypoint if inc.entrypoint is None else inc.entrypoint
        entrypoint_args = existing.entrypoint_args + inc.entrypoint_args if inc.entrypoint_args else existing.entrypoint_args
        verbose = existing.verbose or inc.verbose

        includes = ChubProject._dedup_includes(existing.includes or [], inc.includes or [])
        include_chubs = existing.include_chubs + inc.include_chubs if inc.include_chubs else existing.include_chubs

        # scripts: only extend if the caller provided some
        provided_scripts = bool(inc.scripts and (inc.scripts.pre or inc.scripts.post))
        if provided_scripts:
            scripts = Scripts().from_mapping({
                "pre": ChubProject._dedup([*(existing.scripts.pre if existing.scripts else []),
                                           *(inc.scripts.pre if inc.scripts else [])]),
                "post": ChubProject._dedup([*(existing.scripts.post if existing.scripts else []),
                                            *(inc.scripts.post if inc.scripts else [])])
            })
        else:
            scripts = existing.scripts or Scripts()

        # metadata: additive (existing wins)
        meta: Dict[str, Any] = dict(inc.metadata or {})
        for k, v in (existing.metadata or {}).items():
            if k not in meta:
                meta[k] = v

        return ChubProject(
            name=name,
            version=version,
            project_path=project_path,
            wheels=wheels,
            chub=chub,
            entrypoint=entrypoint,
            entrypoint_args=entrypoint_args,
            includes=includes,
            include_chubs=include_chubs,
            verbose=verbose,
            metadata=meta,
            scripts=scripts)

    @staticmethod
    def override_from_cli_args(existing: "ChubProject", args: Mapping[str, Any]) -> "ChubProject":
        """
        Replacing merge (heavier-handed):
          - provided scalars/lists replace existing
          - scripts replace wholesale if provided
          - metadata from args overwrites existing keys
          - unspecified fields keep existing values
        """
        inc = ChubProject.from_cli_args(args)

        name = inc.name if inc.name is not None else existing.name
        version = inc.version if inc.version is not None else existing.version
        project_path = inc.project_path if inc.project_path is not None else existing.project_path

        wheels = inc.wheels if inc.wheels is not None else existing.wheels
        chub = inc.chub or existing.chub
        entrypoint = inc.entrypoint if inc.entrypoint is not None else existing.entrypoint
        entrypoint_args = inc.entrypoint_args if inc.entrypoint_args is not None else existing.entrypoint_args
        verbose = existing.verbose or inc.verbose

        includes = inc.includes if inc.includes else (existing.includes or [])
        include_chubs = inc.include_chubs if inc.include_chubs else (existing.include_chubs or [])

        scripts = existing.scripts or Scripts()
        if inc.scripts and (inc.scripts.pre or inc.scripts.post):
            scripts = inc.scripts  # wholesale replace

        meta = dict(existing.metadata or {})
        meta.update(inc.metadata or {})

        return ChubProject(
            name=name,
            version=version,
            project_path=project_path,
            wheels=wheels,
            chub=chub,
            entrypoint=entrypoint,
            entrypoint_args=entrypoint_args,
            includes=includes,
            include_chubs=include_chubs,
            verbose=verbose,
            metadata=meta,
            scripts=scripts)

    # ------------------- namespacing helpers -------------------

    @staticmethod
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

    @staticmethod
    def determine_table_path(chubproject_path: Path, table_arg: str | None) -> str | None:
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

    @staticmethod
    def load_file(path: str | Path) -> ChubProject:
        """
        Load a chubproject TOML file from disk.

        - PATH is the filesystem path to the TOML file (e.g., passed via --chubproject PATH).
        - Supports flexible namespacing inside the file via ChubProject.from_toml_document:
            [package], [pychub.package], or any table ending with ".pychub.package".
        - After parsing, records the file's absolute path under metadata["__file__"].
        """
        p = Path(path).expanduser().resolve()
        if not p.is_file():
            raise ChubProjectError(f"Project file not found: {p}")

        try:
            with p.open("rb") as f:
                doc = tomllib.load(f)
        except Exception as e:
            raise ChubProjectError(f"Failed to parse TOML at {p}") from e

        # Let the model handle namespace discovery inside the TOML document
        proj = ChubProject.from_toml_document(doc, path.name)

        return ChubProject.merge_from_cli_args(
            proj,
            {"metadata_entry": [f"__file__={p.as_posix()}"]})

    @staticmethod
    def save_file(
            project: ChubProject | dict,
            path: str | Path = "chubproject.toml",
            *,
            table_name: str = "tool.pychub.package",
            overwrite: bool = False,
            make_parents: bool = True) -> Path:
        if _TOML_WRITER is None:
            raise ChubProjectError(
                "Saving requires a TOML writer. Install one of:\n"
                "  pip install tomli-w   # preferred\n"
                "  pip install tomlkit   # also works\n"
                "  pip install toml      # legacy")

        # accept either a ChubProject or a raw mapping
        if isinstance(project, ChubProject):
            obj = project.to_mapping()
        else:
            obj = ChubProject.from_mapping(project).to_mapping()
        obj = {k: v for k, v in obj.items() if v is not None}

        # Nests under a dotted table name
        def nest_under(table_path: str, value: dict) -> dict:
            keys = table_path.split(".")
            d = value
            for k in reversed(keys):
                d = {k: d}
            return d

        obj = nest_under(table_name, obj)

        p = Path(path).expanduser().resolve()
        if p.exists() and not overwrite:
            raise ChubProjectError(f"Refusing to overwrite without overwrite=True: {p}")
        if make_parents:
            p.parent.mkdir(parents=True, exist_ok=True)

        def _coerce(x: Any):
            if isinstance(x, Path):
                return x.as_posix()
            if isinstance(x, dict):
                return {str(k): _coerce(v) for k, v in x.items()}
            if isinstance(x, (list, tuple)):
                return [_coerce(v) for v in x]
            if isinstance(x, set):
                return sorted(_coerce(v) for v in x)
            return x

        text = _TOML_WRITER.dumps(_coerce(obj))  # type: ignore[attr-defined]
        p.write_text(text, encoding="utf-8")
        return p

    # ------------------- small utils -------------------

    @staticmethod
    def _comma_split_maybe(x: Optional[List[str] | str]) -> List[str]:
        if x is None:
            return []
        if isinstance(x, str):
            return [p.strip() for p in x.split(",") if p.strip()]
        out: List[str] = []
        for item in x:
            if isinstance(item, str) and "," in item:
                out.extend([p.strip() for p in item.split(",") if p.strip()])
            else:
                out.append(str(item))
        return out

    @staticmethod
    def _flatten(values):
        """Flatten lists that may be appended by argparse (list[list[str]]).
        Keeps non-list items as-is.
        """
        if not values:
            return []
        flat = []
        for v in values:
            if isinstance(v, (list, tuple)):
                flat.extend(v)
            else:
                flat.append(v)
        return flat

    @staticmethod
    def _dedup(items: List[str]) -> List[str]:
        seen, out = set(), []
        for s in items:
            if s not in seen:
                seen.add(s)
                out.append(s)
        return out

    @staticmethod
    def _dedup_includes(a: List["IncludeSpec"], b: List["IncludeSpec"]) -> List["IncludeSpec"]:
        """Deduplicate by (src, dest) preserving order."""
        seen: set[Tuple[str, Optional[str]]] = set()
        out: List["IncludeSpec"] = []
        for spec in [*(a or []), *(b or [])]:
            key = (spec.src, spec.dest)
            if key not in seen:
                seen.add(key)
                out.append(spec)
        return out

    # ------------------- instance methods -------------------

    def to_mapping(self) -> Dict[str, Any]:
        """Dump back into a plain mapping (for export/round-tripping)."""
        return {
            "name": self.name,
            "version": self.version,
            "project_path": self.project_path,
            "wheels": list(self.wheels or []),
            "chub": self.chub,
            "entrypoint": self.entrypoint,
            "entrypoint_args": list(self.entrypoint_args) or [],
            "includes": [inc.as_string() for inc in (self.includes or [])],
            "include_chubs": self.include_chubs or [],
            "verbose": self.verbose,
            "metadata": dict(self.metadata or {}),
            "scripts": self.scripts.to_mapping() if self.scripts else {"pre": [], "post": []},
        }

    def to_json(self, *, indent: int = 2) -> str:
        return json.dumps(self.to_mapping(), sort_keys=True, ensure_ascii=False, indent=indent)

    def to_yaml(self, *, indent: int = 2) -> str:
        if yaml is None:
            raise RuntimeError("PyYAML not installed")
        return yaml.safe_dump(self.to_mapping(), sort_keys=True, indent=indent, allow_unicode=True)
