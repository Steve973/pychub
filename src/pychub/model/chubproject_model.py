from __future__ import annotations

from typing import Any, Dict, List, Mapping, Optional, Tuple

from pychub.model.chubconfig_model import dataclass
from pychub.model.includes_model import IncludeSpec
from pychub.model.scripts_model import Scripts


@dataclass(slots=True)
class ChubProject:
    # flat fields (one-shot build config)
    wheel: Optional[str] = None
    add_wheels: List[str] = None  # normalized to list in factories
    chub: Optional[str] = None
    entrypoint: Optional[str] = None
    includes: List["IncludeSpec"] = None
    verbose: bool = False
    metadata: Dict[str, Any] = None
    scripts: Scripts = None

    # ------------------- factories -------------------

    @staticmethod
    def from_mapping(m: Mapping[str, Any] | None) -> "ChubProject":
        """One-shot: build directly from a *package-like* mapping (no namespacing here)."""
        if not m:
            return ChubProject(add_wheels=[], includes=[], metadata={}, scripts=Scripts())

        # includes: accept both styles
        includes: List["IncludeSpec"] = []
        for item in (m.get("includes") or []):
            includes.append(IncludeSpec.parse(item))

        return ChubProject(
            wheel=(str(m["wheel"]) if m.get("wheel") else None),
            add_wheels=[str(x) for x in (m.get("add_wheels") or [])],
            chub=(str(m["chub"]) if m.get("chub") else None),
            entrypoint=(str(m["entrypoint"]) if m.get("entrypoint") else None),
            includes=includes,
            verbose=bool(m.get("verbose", False)),
            metadata=dict(m.get("metadata") or {}),
            scripts=Scripts.from_mapping(m.get("scripts")))

    @staticmethod
    def from_toml_document(doc: Mapping[str, Any]) -> "ChubProject":
        """
        Load with flexible namespacing:
          1) [package]
          2) [pychub.package]
          3) any table whose dotted path endswith ".pychub.package"
          4) if exactly one table looks package-like, use it; otherwise error
        """
        tbl = ChubProject._select_package_table(doc)
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
        wheel = str(args.get("wheel")) if args.get("wheel") else None
        chub = str(args.get("chub") ) if args.get("chub") else None
        entrypoint = str(args.get("entrypoint")) if args.get("entrypoint") else None
        verbose = bool(args.get("verbose", False))

        # lists
        add_wheels = ChubProject._comma_split_maybe(args.get("add_wheel"))

        # includes: --include; list or comma-separated
        inc_raw = args.get("include") or []
        includes = [IncludeSpec.parse(s) for s in ChubProject._comma_split_maybe(inc_raw)]

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
        wheel=wheel,
        add_wheels=add_wheels,
        chub=chub,
        entrypoint=entrypoint,
        includes=includes,
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

        wheel      = existing.wheel if inc.wheel is None else inc.wheel
        chub       = inc.chub or existing.chub
        entrypoint = existing.entrypoint if inc.entrypoint is None else inc.entrypoint
        verbose    = existing.verbose or inc.verbose

        add_wheels = ChubProject._dedup([*(existing.add_wheels or []), *(inc.add_wheels or [])])
        includes   = ChubProject._dedup_includes(existing.includes or [], inc.includes or [])

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
            wheel=wheel,
            add_wheels=add_wheels,
            chub=chub,
            entrypoint=entrypoint,
            includes=includes,
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

        wheel      = inc.wheel if inc.wheel is not None else existing.wheel
        chub       = inc.chub or existing.chub
        entrypoint = inc.entrypoint if inc.entrypoint is not None else existing.entrypoint
        verbose    = existing.verbose or inc.verbose

        add_wheels = inc.add_wheels if inc.add_wheels else (existing.add_wheels or [])
        includes   = inc.includes   if inc.includes   else (existing.includes or [])

        scripts = existing.scripts or Scripts()
        if inc.scripts and (inc.scripts.pre or inc.scripts.post):
            scripts = inc.scripts  # wholesale replace

        meta = dict(existing.metadata or {})
        meta.update(inc.metadata or {})

        return ChubProject(
            wheel=wheel,
            add_wheels=add_wheels,
            chub=chub,
            entrypoint=entrypoint,
            includes=includes,
            verbose=verbose,
            metadata=meta,
            scripts=scripts)

    # ------------------- namespacing helpers -------------------

    @staticmethod
    def _select_package_table(doc: Mapping[str, Any]) -> Mapping[str, Any]:
        # 1) exact [package]
        pkg = doc.get("package")
        if isinstance(pkg, Mapping):
            return pkg

        # 2) scan for pychub.package or any *.pychub.package
        candidates: List[Tuple[int, str, Mapping[str, Any]]] = []
        for path, tbl in ChubProject._walk_tables("", doc):
            if path == "pychub.package":
                candidates.append((0, path, tbl))
            elif path.endswith(".pychub.package"):
                candidates.append((1, path, tbl))

        if candidates:
            candidates.sort(key=lambda t: t[0])
            best_score = candidates[0][0]
            best = [c for c in candidates if c[0] == best_score]
            if len(best) > 1:
                opts = ", ".join(p for _, p, _ in best)
                raise ValueError(f"Ambiguous config tables: {opts}. Choose and use only one.")
            return best[0][2]

        # 3) last resort: unique package-like table
        lookalikes = [(p, t) for p, t in ChubProject._walk_tables("", doc) if ChubProject._looks_like_pkg_table(t)]
        if len(lookalikes) == 1:
            return lookalikes[0][1]
        if not lookalikes:
            raise ValueError(
                "No package-like table found. Provide [package], [pychub.package], "
                "a table ending with .pychub.package, or use a flattened config."
            )
        paths = ", ".join(p for p, _ in lookalikes)
        raise ValueError(f"Multiple package-like tables found: {paths}. Choose and use only one.")

    @staticmethod
    def _walk_tables(prefix: str, tbl: Mapping[str, Any]):
        yield prefix, tbl
        for k, v in tbl.items():
            if isinstance(v, Mapping):
                sub = f"{prefix}.{k}" if prefix else str(k)
                yield from ChubProject._walk_tables(sub, v)

    @staticmethod
    def _looks_like_pkg_table(tbl: Mapping[str, Any]) -> bool:
        anchors = ("wheel", "add_wheels", "entrypoint", "includes", "include", "scripts", "metadata", "chub")
        return any(k in tbl for k in anchors)

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
                seen.add(s); out.append(s)
        return out

    @staticmethod
    def _dedup_includes(a: List["IncludeSpec"], b: List["IncludeSpec"]) -> List["IncludeSpec"]:
        """Deduplicate by (src, dest) preserving order."""
        seen: set[Tuple[str, Optional[str]]] = set()
        out: List["IncludeSpec"] = []
        for spec in [*(a or []), *(b or [])]:
            key = (spec.src, spec.dest)
            if key not in seen:
                seen.add(key); out.append(spec)
        return out

    # ------------------- instance methods -------------------


    def to_mapping(self) -> Dict[str, Any]:
        """Dump back into a plain mapping (for export/round-tripping)."""
        return {
            "wheel": self.wheel,
            "add_wheels": list(self.add_wheels or []),
            "chub": self.chub,
            "entrypoint": self.entrypoint,
            "includes": [inc.as_string() for inc in (self.includes or [])],
            "verbose": self.verbose,
            "metadata": dict(self.metadata or {}),
            "scripts": self.scripts.to_mapping() if self.scripts else {"pre": [], "post": []},
        }
