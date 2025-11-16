from __future__ import annotations

import importlib
import inspect
import pkgutil
from importlib.metadata import entry_points
from typing import Iterable, Mapping, TypeVar

B = TypeVar("B")  # base strategy type


def _builtin_strategy_classes(base: type[B], package_name: str) -> list[type[B]]:
    """
    Discover strategy classes living under the given package.

    Any class that:
      - is a subclass of `base`
      - is not `base` itself
    will be collected.
    """
    package = importlib.import_module(package_name)
    classes: list[type[B]] = []

    for _finder, mod_name, _ispkg in pkgutil.walk_packages(
            package.__path__, package.__name__ + "."):
        module = importlib.import_module(mod_name)

        for obj in vars(module).values():
            if not inspect.isclass(obj):
                continue
            if not issubclass(obj, base):
                continue
            if obj is base:
                continue
            classes.append(obj)

    return classes


def _entrypoint_strategy_classes(base: type[B], group: str) -> list[type[B]]:
    """
    Discover external strategy classes via entry points.
    """
    classes: list[type[B]] = []

    for ep in entry_points().select(group=group):
        obj = ep.load()
        if not inspect.isclass(obj) or not issubclass(obj, base):
            continue
        classes.append(obj)

    return classes


def load_strategies(
        *,
        base: type[B],
        package_name: str,
        entrypoint_group: str,
        ordered_names: Iterable[str] | None = None,
        precedence_overrides: Mapping[str, int] | None = None) -> list[B]:
    """
    Generic SPI-style loader.

    Returns an ordered list of instantiated strategies (with `base` type).

    - If `ordered_names` is provided, that order wins.
    - Otherwise, sort by `precedence` then `name`.

    Assumes each strategy class optionally has:

      - `name: str` (fallback: class name)
      - `precedence: int` (fallback: 100)
    """
    # 1) collect all classes
    classes: list[type[B]] = (
            _builtin_strategy_classes(base, package_name)
            + _entrypoint_strategy_classes(base, entrypoint_group)
    )

    # map for name-based lookup
    by_name: dict[str, type[B]] = {}
    for cls in classes:
        name = getattr(cls, "name", cls.__name__)
        by_name[name] = cls

    # explicit order mode
    if ordered_names is not None:
        instances: list[B] = []

        for name in ordered_names:
            cls = by_name.pop(name, None)
            if cls is not None:
                instances.append(cls())

        # append remaining by precedence so they’re not lost
        remaining: list[tuple[int, str, B]] = []
        for name, cls in by_name.items():
            prec = getattr(cls, "precedence", 100)
            if precedence_overrides and name in precedence_overrides:
                prec = precedence_overrides[name]
            remaining.append((prec, name, cls()))

        remaining.sort(key=lambda t: (t[0], t[1]))
        instances.extend(inst for _p, _n, inst in remaining)

        return instances

    # precedence-only mode
    ranked: list[tuple[int, str, B]] = []
    for cls in classes:
        name = getattr(cls, "name", cls.__name__)
        prec = getattr(cls, "precedence", 100)
        if precedence_overrides and name in precedence_overrides:
            prec = precedence_overrides[name]
        ranked.append((prec, name, cls()))

    ranked.sort(key=lambda t: (t[0], t[1]))
    return [inst for _p, _n, inst in ranked]
