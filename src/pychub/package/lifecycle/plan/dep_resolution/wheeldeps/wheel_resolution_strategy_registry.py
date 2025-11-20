from __future__ import annotations

from typing import Iterable, Mapping, cast

from pychub.helper.strategy_loader import load_strategies_base
from .wheel_resolution_strategy_base import WheelResolutionStrategy

ENTRYPOINT_GROUP = "pychub.wheel_resolution_strategies"
PACKAGE_NAME = __name__.rsplit(".", 1)[0]


def load_strategies(
    ordered_names: Iterable[str] | None = None,
    precedence_overrides: Mapping[str, int] | None = None) -> list[WheelResolutionStrategy]:
    """
    Loads a list of wheel resolution strategies, optionally ordering or overriding their precedence.

    This function retrieves all available strategies for wheel resolution from a specified entry
    point group. Users can optionally provide an ordered list of strategy names or define
    specific precedence overrides to alter the default loading behavior.

    Args:
        ordered_names (Iterable[str] | None): An optional iterable of strategy names that specifies
            the order in which strategies should appear.
        precedence_overrides (Mapping[str, int] | None): A mapping of strategy names to integer values
            specifying their precedence. Higher precedence values take priority over lower ones.

    Returns:
        list[WheelResolutionStrategy]: A list of instances of `WheelResolutionStrategy` loaded and
        ordered based on the provided arguments.
    """
    raw = load_strategies_base(
        base=WheelResolutionStrategy,
        package_name=PACKAGE_NAME,
        entrypoint_group=ENTRYPOINT_GROUP,
        ordered_names=ordered_names,
        precedence_overrides=precedence_overrides)
    return cast(list[WheelResolutionStrategy], raw)
