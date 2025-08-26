from __future__ import annotations

from dataclasses import dataclass, field
from email.parser import Parser
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Tuple
import hashlib
import zipfile

# --------------------------------------------------------------------------
# Selectors (case-insensitive). Use "A|B" to mean "prefer A, else B".
# Keys are canonical names you want in YAML; values are header selectors.
# Mark keys that are multivalued in MULTI_FIELDS.
# --------------------------------------------------------------------------
# Selector = (alternatives, multi?)
# Each alternative may be an OR-chain like "License|License-Expression"
Selector = Tuple[Tuple[str, ...], bool]

METADATA_SELECTORS: Dict[str, Selector] = {
    "name": (("Name",), False),
    "version": (("Version",), False),
    "summary": (("Summary",), False),
    "license": (("License|License-Expression",), False),
    "requires_python": (("Requires-Python",), False),
    "requires_dist": (("Requires-Dist",), True),
    "provides_extra": (("Provides-Extra",), True),
    "home_page": (("Home-page",), False),
}

WHEEL_SELECTORS: Dict[str, Selector] = {
    "wheel_version": (("Wheel-Version",), False),
    "generator": (("Generator",), False),
    "root_is_purelib": (("Root-Is-Purelib",), False),
    "tag": (("Tag",), True),
}


# --------------------------------------------------------------------------

@dataclass(slots=True)
class SourceInfo:
    type: str = "local"  # local | index | vcs | other
    url: Optional[str] = None
    index_url: Optional[str] = None
    downloaded_at: Optional[str] = None  # ISO8601

    def to_mapping(self) -> Dict[str, Any]:
        m: Dict[str, Any] = {"type": self.type}
        if self.url:
            m["url"] = self.url
        if self.index_url:
            m["index_url"] = self.index_url
        if self.downloaded_at:
            m["downloaded_at"] = self.downloaded_at
        return m


@dataclass(slots=True)
class WheelInfo:
    filename: str
    name: str
    version: str
    size: int
    sha256: str
    tags: List[str] = field(default_factory=list)        # from WHEEL Tag
    requires_python: Optional[str] = None
    deps: List[str] = field(default_factory=list)        # immediate deps (filenames)
    source: Optional[SourceInfo] = None
    meta: Dict[str, Any] = field(default_factory=dict)   # normalized METADATA
    wheel: Dict[str, Any] = field(default_factory=dict)  # normalized WHEEL

    def to_mapping(self) -> Dict[str, Any]:
        out: Dict[str, Any] = {
            "name": self.name,
            "version": self.version,
            "sha256": self.sha256,
            "size": self.size,
            "tags": list(self.tags),
        }
        if self.requires_python:
            out["requires_python"] = self.requires_python
        if self.deps:
            out["deps"] = list(self.deps)
        if self.source:
            out["source"] = self.source.to_mapping()
        if self.meta:
            out["meta"] = dict(self.meta)
        if self.wheel:
            out["wheel"] = dict(self.wheel)
        return out

    @staticmethod
    def from_mapping(filename: str, m: Mapping[str, Any]) -> "WheelInfo":
        return WheelInfo(
            filename=filename,
            name=str(m.get("name", "")),
            version=str(m.get("version", "")),
            size=int(m.get("size", 0)),
            sha256=str(m.get("sha256", "")),
            tags=[str(x) for x in (m.get("tags") or [])],
            requires_python=(str(m["requires_python"])
                             if m.get("requires_python") else None),
            deps=[str(x) for x in (m.get("deps") or [])],
            source=SourceInfo(**m["source"]) if m.get("source") else None,
            meta=dict(m.get("meta") or {}),
            wheel=dict(m.get("wheel") or {}))

    @staticmethod
    def build_from_wheel(
            path: str | Path,
            *,
            deps: Iterable[str] | None = None,
            source: SourceInfo | None = None) -> "WheelInfo":
        p = Path(path)
        size = p.stat().st_size
        sha256 = _sha256_file(p)

        meta_hdrs = _read_headers_from_wheel(p, ".dist-info/METADATA")
        wheel_hdrs = _read_headers_from_wheel(p, ".dist-info/WHEEL")

        # Normalize using OR-able selectors (with multi flags baked in)
        meta = _select_fields(meta_hdrs, METADATA_SELECTORS)
        wheel = _select_fields(wheel_hdrs, WHEEL_SELECTORS)

        # Prefer selector results; hard-require Name/Version from METADATA
        name = (meta.pop("name", None) or _select_one(meta_hdrs, ("Name",)))
        version = (meta.pop("version", None) or _select_one(meta_hdrs, ("Version",)))
        if not name or not version:
            raise ValueError(f"{p.name}: METADATA missing Name/Version")

        tags = list(wheel.get("tag") or [])  # already list
        requires_python = str(meta.pop("requires_python", None))

        return WheelInfo(
            filename=p.name,
            name=name,
            version=version,
            size=size,
            sha256=sha256,
            tags=tags,
            requires_python=requires_python,
            deps=[str(x) for x in (deps or ())],
            source=source,
            meta=meta,
            wheel={k: v for k, v in wheel.items() if k != "tag"},
        )


# ------------------------------- helpers ----------------------------------

def _sha256_file(path: Path, *, chunk: int = 1_048_576) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(chunk), b""):
            h.update(block)
    return h.hexdigest()


def _read_headers_from_wheel(
    path: Path, suffix: str) -> Mapping[str, List[str]]:
    with zipfile.ZipFile(path) as z:
        name = next((n for n in z.namelist() if n.endswith(suffix)), None)
        if not name:
            return {}
        text = z.read(name).decode("utf-8", errors="replace")
    msg = Parser().parsestr(text)
    out: Dict[str, List[str]] = {}
    for k in (msg.keys() or []):
        vals = msg.get_all(k) or []
        out.setdefault(k, []).extend(vals)
    return out


def _select_fields(
    headers: Mapping[str, List[str]],
    selectors: Mapping[str, Selector],) -> Dict[str, object]:
    """Apply OR-able selectors with a built-in multi flag."""
    ci: Dict[str, List[str]] = {k.lower(): v for k, v in headers.items()}
    out: Dict[str, object] = {}
    for canon, (alts, multi) in selectors.items():
        chosen: Optional[List[str]] = None
        for sel in alts:
            for alt in (s.strip() for s in sel.split("|")):
                vals = ci.get(alt.lower())
                if vals:
                    chosen = [str(x) for x in vals]
                    break
            if chosen:
                break
        if chosen is None:
            continue
        out[canon] = chosen if multi else chosen[0]
    return out

def _select_one(headers: Mapping[str, List[str]], alts: Tuple[str, ...]) -> Optional[str]:
    ci: Dict[str, List[str]] = {k.lower(): v for k, v in headers.items()}
    for sel in alts:
        for alt in (s.strip() for s in sel.split("|")):
            vals = ci.get(alt.lower())
            if vals:
                return str(vals[0])
    return None


def meta_list(v: Any) -> List[str]:
    if v is None:
        return []
    if isinstance(v, list):
        return [str(x) for x in v]
    return [str(v)]


def meta_str(v: Any) -> Optional[str]:
    return None if v is None else str(v)
