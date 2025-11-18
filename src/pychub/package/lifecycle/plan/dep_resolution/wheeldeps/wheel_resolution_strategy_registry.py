from __future__ import annotations

from typing import Iterable, Mapping, cast

from pychub.helper.strategy_loader import load_strategies_base
from .wheel_resolution_strategy_base import WheelResolutionStrategy

ENTRYPOINT_GROUP = "pychub.wheel_resolution_strategies"
PACKAGE_NAME = __name__.rsplit(".", 1)[0]


def load_strategies(
    ordered_names: Iterable[str] | None = None,
    precedence_overrides: Mapping[str, int] | None = None) -> list[WheelResolutionStrategy]:
    raw = load_strategies_base(
        base=WheelResolutionStrategy,
        package_name=PACKAGE_NAME,
        entrypoint_group=ENTRYPOINT_GROUP,
        ordered_names=ordered_names,
        precedence_overrides=precedence_overrides)
    return cast(list[WheelResolutionStrategy], raw)
