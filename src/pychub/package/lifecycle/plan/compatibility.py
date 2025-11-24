from typing import Sequence

from pychub.model.wheels_model import WheelCollection


def default_targets_for_wheels(wheels: WheelCollection) -> list[str]:
    """
    Determines the default targets for a collection of wheels.

    The function processes a collection of wheels to extract and sort the unique
    supported target strings, which describe the compatibility criteria for the
    wheels. This can help identify the range of supported environments or platforms
    for the given set of wheels.

    Args:
        wheels (WheelCollection): A collection of wheel files whose supported target
            strings need to be determined.

    Returns:
        list[str]: A sorted list of unique supported target strings.
    """
    # later: filter using your curated tag triples list
    return sorted(set(wheels.supported_target_strings))


def resolve_compatibility_targets(
    wheels: WheelCollection,
    configured_target: str | None,
    configured_targets: Sequence[str] | None) -> list[str]:
    """
    Resolves compatibility targets based on the provided configurations and available wheels.

    This function determines the appropriate compatibility targets for a set
    of wheels by following a resolution process:
    1. If the configured target is explicitly set to "universal", that will
       be used as the sole target.
    2. If a list of user-provided configured targets is supplied, these will
       be considered valid and returned directly.
    3. In the absence of any explicit configuration, fallback defaults
       derived from the wheels will be used.

    Args:
        wheels: The collection of wheels to be processed for determining
            compatibility targets.
        configured_target: A single explicit compatibility target string
            (e.g., "universal").
        configured_targets: A list of user-specified compatibility targets
            (e.g., ["cp311-manylinux_x86_64", ...]).

    Returns:
        A list of resolved compatibility targets as strings, in line with
        the provided configuration or the fallback defaults.
    """
    # 1. explicit "universal" wins
    if configured_target == "universal":
        return ["universal"]

    defaults = default_targets_for_wheels(wheels)

    # 2. user-provided list: either trust it or intersect with defaults
    if configured_targets:
        # choice here: just return configured_targets, or validate
        # that they're compatible with defaults. Up to you.
        return list(configured_targets)

    # 3. no config: fall back to defaults from wheels
    return defaults
