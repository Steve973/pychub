from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

import tomli
import tomli_w


def load_toml_file(path: str | Path) -> dict[str, Any]:
    with open(path, "rb") as f:
        return tomli.load(f)


def load_toml_text(text: str) -> dict[str, Any]:
    return tomli.loads(text)


def dump_toml_to_str(data: Mapping[str, Any], indent: int = 2) -> str:
    return tomli_w.dumps(data, indent=indent)


def dump_toml_to_file(data: Mapping[str, Any], path: str | Path) -> None:
    Path(path).write_text(dump_toml_to_str(data), encoding="utf-8")
