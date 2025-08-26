from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path, PurePath
from importlib.metadata import PackageNotFoundError, version as get_version

from .packager import build_chub

_ALLOWED = re.compile(r"[^A-Za-z0-9._-]+")

def _sanitize(p: str | PurePath) -> str:
    parts = [s for s in PurePath(p).parts if s not in ("", ".", "..", "/")]
    name = "_".join(parts) or "script"
    name = _ALLOWED.sub("_", name)
    name = re.sub(r"_+", "_", name).strip("_")
    return name or "script"


def prefixed_script_names(paths: list[str | Path]) -> list[tuple[Path, str]]:
    """Return (src_path, dest_name) with zero-padded index prefix.
    Lexical sort preserves input order; width grows when >=100 items.
    """
    width = max(2, len(str(max(len(paths) - 1, 0))))
    seen: dict[str, int] = {}
    out: list[tuple[Path, str]] = []
    for i, src in enumerate(paths):
        base = _sanitize(src)
        key = base.lower()
        n = seen.get(key, 0)
        seen[key] = n + 1
        if n:  # dedupe while preserving extension
            stem, dot, ext = base.rpartition(".")
            base = f"{(stem or base)}({n}){dot}{ext}"
        out.append((Path(src), f"{i:0{width}d}_{base}"))
    return out


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


def _paths(values):
    """Convert a (possibly nested) list of paths to Path objects.
    Filters out non-existent files.
    """
    out: list[Path] = []
    for item in _flatten(values):
        p = Path(item).expanduser().resolve()
        if p.exists() and p.is_file():
            out.append(p)
    return out


def _includes(values):
    """Return raw include strings (preserving `src::dest`).
    Also validates that `src` exists.
    """
    out: list[str] = []
    for item in _flatten(values):
        s = str(item)
        src = s.split("::", 1)[0]
        p = Path(src).expanduser().resolve()
        if not p.exists() or not p.is_file():
            continue
        # Preserve the original token including ::dest
        out.append(s)
    return out


def main():
    parser = argparse.ArgumentParser(
        prog="pychubby",
        description="Package a wheel and its dependencies into a .chub archive")

    parser.add_argument(
        "wheel",
        type=Path,
        help="Path to the .whl file")

    parser.add_argument(
        "-a",
        "--add-wheel",
        nargs="+",
        type=Path,
        help="One or more additional wheels to include",
        action="append")

    parser.add_argument(
        "-c",
        "--chub",
        type=Path,
        help="Optional path to output .chub (defaults to <name>-<version>.chub)")

    parser.add_argument(
        "-e",
        "--entrypoint",
        help="Optional 'module:function' to run after install")

    parser.add_argument(
        "-i",
        "--include",
        nargs="+",
        metavar="FILE[::dest]",
        help="Extra files to include (dest is relative to install dir)")

    parser.add_argument(
        "-m",
        "--metadata-entry",
        nargs="+",
        action="append",
        metavar="KEY=VALUE[,VALUE...]",
        help="Extra metadata entries to embed in .chubconfig")

    parser.add_argument(
        "-o",
        "--post-script",
        nargs="+",
        metavar="POST_SCRIPT",
        help="Post-install scripts to include and run")

    parser.add_argument(
        "-p",
        "--pre-script",
        nargs="+",
        metavar="PRE_SCRIPT",
        help="Pre-install scripts to include and run (planned)")

    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Set output to verbose")

    parser.add_argument(
        "-v",
        "--version",
        action="store_true",
        help="Show version and exit")

    args = parser.parse_args()

    if args.version:
        print(f"Python: {sys.version.split()[0]}")
        try:
            version = get_version("pychubby")
        except PackageNotFoundError:
            version = "(source)"
        print(f"pychubby: {version}")
        return

    # Build metadata (start empty if None)
    meta_items = _flatten(args.metadata_entry)
    if args.wheel:
        meta_items.append(f"main_wheel={Path(args.wheel).name}")

    metadata: dict[str, str | list[str]] = {}
    for item in meta_items:
        if "=" not in str(item):
            continue
        key, value = str(item).split("=", 1)
        values = [v.strip() for v in value.split(",") if v.strip()]
        metadata[key] = values if len(values) > 1 else values[0]

    # Collect wheels
    wheels: list[Path] = []
    if args.wheel:
        wheels.append(args.wheel.expanduser().resolve())
    wheels.extend(_paths(args.add_wheel))

    include_files = _includes(args.include)
    post_scripts = prefixed_script_names(_paths(args.post_script))
    pre_scripts = prefixed_script_names(_paths(args.pre_script))

    build_chub(
        wheel_paths=wheels,
        chub_path=args.chub,
        entrypoint=args.entrypoint,
        post_install_scripts=post_scripts,
        pre_install_scripts=pre_scripts,
        included_files=include_files,
        metadata=metadata)


if __name__ == "__main__":
    main()
