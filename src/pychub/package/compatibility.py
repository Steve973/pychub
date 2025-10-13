from __future__ import annotations

from typing import Dict, List, Optional
from typing import Set

import requests
from packaging.requirements import Requirement
from packaging.tags import Tag
from packaging.version import Version, InvalidVersion


def filter_tags_py3_or_higher(tags: Set[Tag]) -> Set[Tag]:
    """
    Filter out any tags that are not Python 3+ (keep cp3x, py3, py2.py3, etc).
    Discards tags that are only for Python 2.
    """

    def is_py3(tag: Tag) -> bool:
        # Accepts: cp3x, py3, py2.py3, and friends.
        interp = tag.interpreter.lower()
        # Covers 'cp3X', 'py3', 'py2.py3', 'py2.py3', etc
        if interp.startswith("cp3") or interp == "py3" or "py3" in interp:
            return True
        return False

    return {tag for tag in tags if is_py3(tag)}


def parse_wheel_tags(wheel_filename: str) -> Set[Tag]:
    """Return set of tags for a wheel filename."""
    _, _, _, tags = parse_wheel_filename(wheel_filename)
    return set(tags)


def collect_wheel_tags_for_deps(wheel_files: Dict[str, List[str]]) -> Dict[str, Set[Tag]]:
    """
    Given {dep: [wheel_filenames]}, return {dep: set(Tag, ...)}
    """
    tags_by_dep = {}
    for dep, wheel_list in wheel_files.items():
        dep_tags = set()
        for wf in wheel_list:
            dep_tags |= parse_wheel_tags(wf)
        tags_by_dep[dep] = dep_tags
    return tags_by_dep


def tag_sort_key(tag: Tag):
    """Sort tags (interpreter, abi, platform)"""
    return tag.interpreter, tag.abi, tag.platform


def compute_compatibility_combos(wheel_files: dict[str, list[str]]) -> list[tuple[Tag, dict[str, str]]]:
    tags_by_dep = collect_wheel_tags_for_deps(wheel_files)
    dep_tags = list(tags_by_dep.values())
    if not dep_tags:
        return []
    common_tags = set.intersection(*dep_tags)
    combos = []
    for tag in sorted(common_tags, key=lambda t: (t.interpreter, t.abi, t.platform)):
        # Optionally: produce mapping of dep → wheel filename
        combos.append((tag, {}))  # (for now, just put an empty dict)
    return combos


def match_wheels_to_tag(wheel_files: Dict[str, List[str]], tag: Tag) -> Optional[Dict[str, str]]:
    """
    For a given target tag, select a wheel for each dep that matches that tag.
    Return {dep: wheel_filename}, or None if not possible.
    """
    mapping = {}
    for dep, wheel_list in wheel_files.items():
        found = False
        for wheel in wheel_list:
            if tag in parse_wheel_tags(wheel):
                mapping[dep] = wheel
                found = True
                break
        if not found:
            return None
    return mapping


from packaging.utils import parse_wheel_filename


def aggregate_tag_components(wheel_files: dict[str, list[str]]):
    interpreters, abis, platforms = set(), set(), set()
    for wheels in wheel_files.values():
        for fname in wheels:
            _, _, _, tags = parse_wheel_filename(fname)
            for tag in tags:
                interpreters.add(tag.interpreter)
                abis.add(tag.abi)
                platforms.add(tag.platform)
    return sorted(interpreters), sorted(abis), sorted(platforms)


def enumerate_valid_combos(wheel_files: dict[str, list[str]]) -> list[tuple[str, str, str]]:
    tags_by_dep = {}
    deps_with_universal = set()
    all_combos = set()

    # First pass: collect tag sets and detect universal
    for dep, wheels in wheel_files.items():
        tag_set = set()
        for fname in wheels:
            _, _, _, tags = parse_wheel_filename(fname)
            tag_set |= set(tags)
            if any(is_universal_tag(tag) for tag in tags):
                deps_with_universal.add(dep)
        tags_by_dep[dep] = tag_set
        all_combos |= {(tag.interpreter, tag.abi, tag.platform) for tag in tag_set}

    # UNIVERSAL SHORT-CIRCUIT
    if tags_by_dep and deps_with_universal and all(dep in deps_with_universal for dep in tags_by_dep):
        return [("py3", "none", "any")]

    # Second pass: propagate all combos to universal deps
    for dep in deps_with_universal:
        tags_by_dep[dep] = {Tag(*combo) for combo in all_combos}

    # Third pass: find combos that every dep supports
    valid_combos = []
    for combo in all_combos:
        tag_obj = Tag(*combo)
        if all(tag_obj in tags for tags in tags_by_dep.values()):
            valid_combos.append(combo)

    return valid_combos


def fetch_all_wheel_variants(
    *requirements: str,
    index_url: str = "https://pypi.org/pypi") -> Dict[str, List[dict]]:
    """
    For each requirement (e.g., 'attrs>=23.0.0'), query PyPI and return all available wheels.
    Does not download wheel files—returns metadata for selection and planning.

    Returns:
        { package_name: [ {filename, url, version, tags (set of Tag)}, ... ], ... }
    """
    results: Dict[str, List[dict]] = {}

    for req_str in requirements:
        try:
            req = Requirement(req_str)
        except Exception as e:
            print(f"[compatibility] Could not parse requirement '{req_str}': {e}")
            continue

        pkg_name = req.name
        try:
            r = requests.get(f"{index_url}/{pkg_name}/json", timeout=10)
            r.raise_for_status()
            data = r.json()
        except Exception as e:
            print(f"[compatibility] Could not fetch metadata for {pkg_name}: {e}")
            continue

        wheels: List[dict] = []
        for ver_str, files in data.get("releases", {}).items():
            # Optionally filter by version specifier
            try:
                ver = Version(ver_str)
            except InvalidVersion:
                continue
            if req.specifier and not req.specifier.contains(ver, prereleases=True):
                continue

            for file in files:
                fn = file.get("filename", "")
                if fn.endswith(".whl"):
                    try:
                        _, _, _, tags = parse_wheel_filename(fn)
                    except Exception as e:
                        print(f"[compatibility] Failed to parse tags from {fn}: {e}")
                        continue
                    wheels.append({
                        "filename": fn,
                        "url": file.get("url"),
                        "version": ver_str,
                        "tags": tags,
                    })
        if wheels:
            results[pkg_name] = wheels

    return results


def tag_to_str(tag: Tag) -> str:
    return f"{tag.interpreter}-{tag.abi}-{tag.platform}"


def is_universal_tag(tag: Tag) -> bool:
    return tag.interpreter == "py3" and tag.abi == "none" and tag.platform == "any"


def has_universal_tag(wheel: str) -> bool:
    return any(
        is_universal_tag(t)
        for t in parse_wheel_tags(wheel))


def compute_per_combo_wheel_map(wheel_files: Dict[str, List[str]]) -> Dict[str, Dict[str, str]]:
    """
    Given all available wheels per dependency, return a mapping of compatible
    combos to selected wheels.

    For each valid (interpreter, abi, platform) combo, include one matching
    wheel per dependency (universal or platform-specific).

    Returns:
        {
          "cp310-cp310-manylinux_2_17_x86_64": {
              "dep1": "dep1-1.0.0-py3-none-any.whl",
              "dep2": "dep2-1.0.0-cp310-cp310-manylinux_2_17_x86_64.whl",
          },
          ...
        }
    """
    # 1. Find all combos supported by ALL deps
    combos = enumerate_valid_combos(wheel_files)
    if not combos:
        return {}

    combo_map: Dict[str, Dict[str, str]] = {}

    # 2. For each combo, select the best wheel per dep
    for interp, abi, plat in combos:
        tag = Tag(interp, abi, plat)
        combo_key = tag_to_str(tag)
        wheel_map: Dict[str, str] = {}

        for dep, wheels in wheel_files.items():
            # Find the first wheel whose tag set
            # 1. is a universal wheel (preferred)
            # 2. matches this combo tag
            universal = next((w for w in wheels if has_universal_tag(w)), None)
            if universal:
                wheel_map[dep] = universal
            else:
                matching_wheels = [
                    wheel for wheel in wheels
                    if any(tag == candidate for candidate in parse_wheel_tags(wheel))
                ]
                if matching_wheels:
                    wheel_map[dep] = matching_wheels[0]

        if len(wheel_map) == len(wheel_files):
            combo_map[combo_key] = wheel_map

    return combo_map
