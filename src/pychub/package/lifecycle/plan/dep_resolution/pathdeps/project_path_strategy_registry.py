from __future__ import annotations

from typing import Iterable, Mapping, cast

from pychub.helper.strategy_loader import load_strategies_base
from .project_path_strategy_base import ProjectPathStrategy

ENTRYPOINT_GROUP = "pychub.project_path_strategies"
PACKAGE_NAME = __name__.rsplit(".", 1)[0]


def load_strategies(
    ordered_names: Iterable[str] | None = None,
    precedence_overrides: Mapping[str, int] | None = None) -> list[ProjectPathStrategy]:
    raw = load_strategies_base(
        base=ProjectPathStrategy,
        package_name=PACKAGE_NAME,
        entrypoint_group=ENTRYPOINT_GROUP,
        ordered_names=ordered_names,
        precedence_overrides=precedence_overrides)
    return cast(list[ProjectPathStrategy], raw)
