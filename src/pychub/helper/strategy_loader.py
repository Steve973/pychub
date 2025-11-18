from __future__ import annotations

import importlib
import inspect
import pkgutil
from importlib.metadata import entry_points
from typing import Any, Iterable, Mapping


def _builtin_strategy_classes(base: type, package_name: str) -> list[type]:
    """
    Discover strategy classes living under the given package.

    Any class that:
      - is a subclass of `base`
      - is not `base` itself
    will be collected.
    """
    package = importlib.import_module(package_name)
    classes: list[type] = []

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


def _entrypoint_strategy_classes(base: type, group: str) -> list[type]:
    """
    Discover external strategy classes via entry points.
    """
    classes: list[type] = []

    for ep in entry_points().select(group=group):
        obj = ep.load()
        if not inspect.isclass(obj) or not issubclass(obj, base):
            continue
        classes.append(obj)

    return classes


def load_strategies_base(
        *,
        base: type,
        package_name: str,
        entrypoint_group: str,
        ordered_names: Iterable[str] | None = None,
        precedence_overrides: Mapping[str, int] | None = None) -> list[Any]:
    """
    SPI-style loader.

    - `base`: abstract or concrete base class/protocol used for issubclass checks
    - returns: instantiated strategy objects (as `list[Any]`)

    Ordering rules:
      - If `ordered_names` is provided, that explicit order wins.
      - Remaining strategies are sorted by `precedence` then `name`.
    """
    classes: list[type] = (
            _builtin_strategy_classes(base, package_name) +
            _entrypoint_strategy_classes(base, entrypoint_group)
    )

    # map name -> class
    by_name: dict[str, type] = {}
    for cls in classes:
        name = getattr(cls, "name", cls.__name__)
        by_name[name] = cls

    # explicit order mode
    if ordered_names is not None:
        instances: list[Any] = []

        for name in ordered_names:
            selected = by_name.get(name)
            if selected is not None:
                instances.append(selected())
                del by_name[name]

        remaining: list[tuple[int, str, Any]] = []
        for name, cls in by_name.items():
            prec = getattr(cls, "precedence", 100)
            if precedence_overrides and name in precedence_overrides:
                prec = precedence_overrides[name]
            remaining.append((prec, name, cls()))

        remaining.sort(key=lambda t: (t[0], t[1]))
        instances.extend(inst for _p, _n, inst in remaining)

        return instances

    # precedence-only mode
    ranked: list[tuple[int, str, Any]] = []
    for cls in classes:
        name = getattr(cls, "name", cls.__name__)
        prec = getattr(cls, "precedence", 100)
        if precedence_overrides and name in precedence_overrides:
            prec = precedence_overrides[name]
        ranked.append((prec, name, cls()))

    ranked.sort(key=lambda t: (t[0], t[1]))
    return [inst for _p, _n, inst in ranked]
