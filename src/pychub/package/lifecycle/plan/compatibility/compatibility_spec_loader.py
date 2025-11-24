from __future__ import annotations

from collections.abc import Mapping as MappingABC
from importlib import resources
from pathlib import Path
from typing import Any, Mapping, Optional

from pychub.helper.toml_utils import load_toml_text
from pychub.model.compatibility_spec_model import CompatibilitySpec

_DEFAULT_SPEC_RESOURCE_PACKAGE = "pychub.package.lifecycle.plan.compatibility"
_DEFAULT_SPEC_RESOURCE_NAME = "compatibility_spec.toml"


def _spec_override(
        base: Mapping[str, Any],
        override: Mapping[str, Any]) -> dict[str, Any]:
    """
    Recursively merges two mappings, overriding values in the base mapping with
    those from the override mapping. If both values corresponding to the same key
    are mappings, their values are also recursively merged.

    Args:
        base: The base mapping to be merged.
        override: The mapping containing values that will override those in the
            base mapping.

    Returns:
        A dictionary representing the result of merging the base and override
        mappings.
    """
    result: dict[str, Any] = dict(base)
    for key, o_val in override.items():
        b_val = result.get(key)
        if isinstance(b_val, MappingABC) and isinstance(o_val, MappingABC):
            result[key] = _spec_override(b_val, o_val)
        else:
            result[key] = o_val
    return result


def _spec_merge(
        base: Mapping[str, Any],
        override: Mapping[str, Any]) -> dict[str, Any]:
    """
    Merges two mappings recursively, combining values from both mappings based
    on specific rules. The merging prioritizes the `override` mapping over the
    `base` mapping.

    Lists in the mappings are merged with items from the `override` mapping
    appended to the list of the `base` mapping, avoiding duplication. Nested
    mappings are recursively merged.

    Args:
        base (Mapping[str, Any]): The base mapping to be merged into.
        override (Mapping[str, Any]): The mapping whose values will override or
            supplement the base mapping.

    Returns:
        dict[str, Any]: A new dictionary obtained by merging the two input mappings.
    """
    result: dict[str, Any] = dict(base)
    for key, o_val in override.items():
        b_val = result.get(key)

        if isinstance(b_val, MappingABC) and isinstance(o_val, MappingABC):
            result[key] = _spec_merge(b_val, o_val)
        elif isinstance(b_val, list) and isinstance(o_val, list):
            # defaults first, then any file items not already present
            result[key] = b_val + [x for x in o_val if x not in b_val]
        else:
            result[key] = o_val

    return result


def _load_default_spec_mapping() -> Mapping[str, Any]:
    """
    Loads the default specification mapping from a predefined resource.

    This function reads a TOML file from the specified resource package and parses
    its contents to generate a mapping of specifications. The function is
    responsible for ensuring that the resource file is read in UTF-8 encoding.

    Returns:
        Mapping[str, Any]: A mapping representing the parsed specifications from
        the TOML resource.
    """
    text = (
        resources.files(_DEFAULT_SPEC_RESOURCE_PACKAGE)
        .joinpath(_DEFAULT_SPEC_RESOURCE_NAME)
        .read_text(encoding="utf-8")
    )
    return load_toml_text(text)


def _load_file_spec_mapping(path: Path) -> Mapping[str, Any]:
    """
    Loads a TOML file and returns its contents as a mapping. This function
    ensures the file exists before reading and parsing its contents.

    Args:
        path (Path): The file path to the TOML file to be loaded.

    Returns:
        Mapping[str, Any]: The parsed contents of the TOML file.

    Raises:
        FileNotFoundError: If the specified file does not exist.
    """
    if not path.exists():
        raise FileNotFoundError(f"Compatibility spec file not found: {path}")
    return load_toml_text(path.read_text(encoding="utf-8"))


def load_effective_compatibility_spec(
    *,
    strategy_name: str,
    user_spec_path: Optional[Path],
    inline_overrides: Optional[Mapping[str, Any]]) -> CompatibilitySpec:
    """
    Loads the effective compatibility specification by overlaying default settings,
    user-provided file configurations, and potential inline overrides in a specific
    precedence order.

    This function combines three sources to create an effective compatibility
    specification: embedded defaults, an optional user specification file, and
    optional inline overrides. Inline overrides always take the highest precedence,
    followed by the user specification file, and then the embedded defaults. It
    ensures that the resulting specification takes all these sources into account
    and is enriched with a clear source description.

    Args:
        strategy_name (str): Strategy for merging the specifications. Can either
            be "override" or "merge". If an invalid strategy is given, it should
            already be normalized by the caller.
        user_spec_path (Optional[Path]): Path to the user specification file. If
            None, this step will be skipped.
        inline_overrides (Optional[Mapping[str, Any]]): Inline overrides to apply
            on top of the specifications. These overrides always take the highest
            precedence.

    Returns:
        CompatibilitySpec: The resulting compatibility specification object
        created by merging the given sources.
    """
    # 1) Start from embedded defaults
    default_map = _load_default_spec_mapping()
    merged_map: dict[str, Any] = dict(default_map)

    source_parts: list[str] = [
        f"embedded:{_DEFAULT_SPEC_RESOURCE_PACKAGE}/{_DEFAULT_SPEC_RESOURCE_NAME}"
    ]

    # 2) Overlay file spec, if present
    if user_spec_path is not None:
        file_map = _load_file_spec_mapping(user_spec_path)

        if strategy_name == "override":
            merged_map = _spec_override(merged_map, file_map)
            source_parts.append(f"file:{user_spec_path} (override)")
        else:
            # "merge" (or anything invalid that you already normalized in the caller)
            merged_map = _spec_merge(merged_map, file_map)
            source_parts.append(f"file:{user_spec_path} (merge)")

    # 3) Apply inline overrides (the highest precedence, always full override semantics)
    if inline_overrides:
        merged_map = _spec_override(merged_map, inline_overrides)
        source_parts.append("inline:project_toml")

    # 4) Build the spec object
    spec = CompatibilitySpec.from_mapping(merged_map)

    # Let this override whatever fmt:path the mixin might have guessed
    try:
        spec.source_description = " + ".join(source_parts)
    except AttributeError:
        pass

    return spec
