from __future__ import annotations

from typing import Iterable, Mapping, cast

from pychub.helper.strategy_loader import load_strategies_base
from .project_path_strategy_base import ProjectPathStrategy

ENTRYPOINT_GROUP = "pychub.project_path_strategies"
PACKAGE_NAME = __name__.rsplit(".", 1)[0]


def load_strategies(
    ordered_names: Iterable[str] | None = None,
    precedence_overrides: Mapping[str, int] | None = None) -> list[ProjectPathStrategy]:
    """
    Loads and returns a list of `ProjectPathStrategy` objects based on specified configurations.
    This function uses a base loading mechanism to gather and organize implementations
    of the `ProjectPathStrategy` interface from an entry point group. The strategies can be
    optionally ordered and prioritized according to the provided arguments.

    Args:
        ordered_names (Iterable[str] | None): An optional iterable of strategy names specifying the
            order in which strategies should be loaded. If provided, the strategies will be ordered
            according to this list, with any additional ones appended later in an undefined order.
        precedence_overrides (Mapping[str, int] | None): An optional mapping of strategy names to
            their respective precedence values. Lower precedence values define a higher priority,
            directly influencing the sorting of strategies.

    Returns:
        list[ProjectPathStrategy]: A list of `ProjectPathStrategy` instances, sorted based on the
            provided `ordered_names` and `precedence_overrides`.
    """
    raw = load_strategies_base(
        base=ProjectPathStrategy,
        package_name=PACKAGE_NAME,
        entrypoint_group=ENTRYPOINT_GROUP,
        ordered_names=ordered_names,
        precedence_overrides=precedence_overrides)
    return cast(list[ProjectPathStrategy], raw)
