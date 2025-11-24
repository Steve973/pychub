import re
from dataclasses import dataclass, field
from sys import version_info as _py_version
from typing import Mapping, Optional

from packaging.tags import Tag, parse_tag

from pychub.model.compatibility_spec_model import (
    CompatibilitySpec,
    PlatformOSSpec,
    PlatformFamilySpec,
    PythonVersionsSpec,
    AbiValuesSpec,
)

# ---------------------------------------------------------------------------
# Helpers for platform tag parsing
# ---------------------------------------------------------------------------

# Example tags: manylinux_2_17_x86_64, musllinux_1_1_aarch64, macosx_11_0_arm64, win_amd64
PLATFORM_RE = re.compile(
    r"^(?P<flavor>[a-zA-Z0-9]+)"
    r"(?:_(?P<major>\d+)_(?P<minor>\d+))?"
    r"(?:_(?P<arch>[A-Za-z0-9_]+))?$"
)


def split_platform_tag(platform: str) -> tuple[str, Optional[str], Optional[str]]:
    """
    Splits a platform tag into its respective components: flavor, version, and architecture.

    This function uses a regular expression to parse the given platform tag string. It extracts the
    flavor, version (constructed by combining major and minor components if both exist), and the
    architecture components of the platform tag. If the input platform string does not match the
    expected pattern, it returns the entire platform tag as the flavor, with version and architecture
    set to None.

    Args:
        platform (str): The platform tag string to be parsed.

    Returns:
        Tuple[str, Optional[str], Optional[str]]: A 3-tuple containing:
            - flavor (str): The flavor of the platform, derived from the tag.
            - version (Optional[str]): The combined major and minor components as a single string,
              or None if either of them is missing.
            - arch (Optional[str]): The architecture part of the platform tag, or None if it is not present.
    """
    m = PLATFORM_RE.match(platform)
    if not m:
        return platform, None, None

    flavor = m.group("flavor")
    major = m.group("major")
    minor = m.group("minor")
    arch = m.group("arch")
    version = f"{major}_{minor}" if major and minor else None
    return flavor, version, arch


def parse_glibc_like_version(v: str) -> tuple[int, int]:
    """
    Parses a version string resembling glibc-like versions into major and minor version components.

    This function takes a version string, normalizes it, and extracts the major and minor versions
    as integers. If the version string contains only a major version (e.g., "3"), it assumes a minor
    version of "0". Unexpected formatting of the version string will not raise an error unless it
    prevents splitting or conversion to integers.

    Args:
        v (str): The version string to parse. It is expected to be in the format of "major.minor" or
            just "major".

    Returns:
        Tuple[int, int]: A tuple containing the major and minor versions as integers.
    """
    v = v.strip()
    normalized = v.replace(".", "_")
    try:
        major_s, minor_s = normalized.split("_", 1)
    except ValueError:
        # Bare major -> treat as ".0"
        major_s, minor_s = normalized, "0"
    return int(major_s), int(minor_s)


# ---------------------------------------------------------------------------
# Helpers for Python versions / ABI
# ---------------------------------------------------------------------------


def parse_python_version_label(label: str) -> Optional[tuple[int, int]]:
    """
    Extracts a (major, minor) Python version from a version label.

    This function identifies and parses version labels representing Python versions
    into a tuple of major and minor version numbers. It supports formats such as
    '3.11', 'cp311', 'cp310', 'py311', 'py39', and 'py3'. Labels with only major
    version numbers (e.g., 'py3') are interpreted with a minor version of 0. If no
    valid version can be determined from the label, the function returns None.

    Args:
        label (str): The label to extract the version from. This could be in various
            formats such as '3.11', 'cp311', or 'py3'.

    Returns:
        Optional[Tuple[int, int]]: A tuple of (major, minor) version numbers if the
        label can be parsed, otherwise None.
    """
    s = label.strip()

    # plain "3.11"
    m = re.match(r"^(?P<maj>\d+)\.(?P<min>\d+)$", s)
    if m:
        return int(m.group("maj")), int(m.group("min"))

    # trailing digits in things like 'cp311', 'py3'
    m = re.search(r"(\d+)$", s)
    if not m:
        return None

    digits = m.group(1)
    length = len(digits)
    if length == 1:
        # '3' -> (3, 0)
        return int(digits), 0
    if length == 2:
        # '39' -> 3.9
        return int(digits[0]), int(digits[1])
    if length == 3:
        # '311' -> 3.11
        return int(digits[0]), int(digits[1:])

    return None


def is_debug_abi(abi: str) -> bool:
    """
    Determines if the given ABI (Application Binary Interface) corresponds to a
    debug build configuration.

    This function analyzes the ABI string and checks whether it ends with a
    character 'd', which typically denotes a debug build.

    Args:
        abi (str): The ABI string to evaluate.

    Returns:
        bool: True if the given ABI corresponds to a debug build, otherwise False.
    """
    return abi.endswith("d")


def is_stable_abi(abi: str) -> bool:
    """
    Determines whether the provided ABI (Application Binary Interface) string represents
    a stable ABI.

    An ABI is considered stable if it starts with the prefix "abi" followed by numeric
    characters, or if the ABI is explicitly "none".

    Args:
        abi (str): The ABI string to be checked for stability.

    Returns:
        bool: True if the ABI is stable, False otherwise.
    """
    if abi == "none":
        return True
    return abi.startswith("abi") and abi[3:].isdigit()


@dataclass(slots=True)
class PythonVersionBounds:
    """Represents version bounds for Python with specified minimum and maximum values.

    This class is used to define the minimum and maximum Python version bounds,
    as well as the maximum comparison operator. It ensures clarity and consistency
    when defining compatibility with Python versions.

    Attributes:
        min (Tuple[int, int]): The minimum Python version as a tuple, e.g., (3, 6)
            for Python 3.6.
        max (Tuple[int, int]): The maximum Python version as a tuple, defining the
            upper bound of compatibility.
        max_op (str): The comparison operator for the maximum version, either '<'
            or '<='.
    """
    min: tuple[int, int]
    max: tuple[int, int]
    max_op: str  # '<' or '<='


def _compute_python_version_bounds(spec: PythonVersionsSpec) -> PythonVersionBounds:
    """
    Compute effective Python version bounds (minimum and maximum) based on the provided
    specification. This function determines compliant Python version ranges by applying the
    following rules:

    - Minimum version:
      * If `spec.min` is provided, it is directly used.
      * If `spec.min` is not provided, it defaults to the lowest version for the current
        interpreter major version (e.g., `X.0`).

    - Maximum version:
      * If `spec.max` is omitted, the upper bound defaults to the next major version's `X.0`
        (e.g., `< (min_major + 1).0`).
      * If `spec.max` is provided, it may be specified in one of the following valid formats:
        - `<4.0`
        - `<=4.0`
        - `4.0` (treated as `<= 4.0`)
      * The `*` wildcard is explicitly rejected as unbounded upper ranges are not supported
        for Python versions.

    Args:
        spec (PythonVersionsSpec): The specification containing the min and max Python
            versions to use as bounds.

    Returns:
        PythonVersionBounds: A structure containing the computed minimum version, maximum
        version, and the comparison operator for the maximum version.

    Raises:
        ValueError: If `spec.min` is invalid or cannot be parsed.
        ValueError: If `spec.max` contains an unsupported format or an invalid comparator.
    """
    # ---- min ----
    if spec.min is not None:
        min_v = parse_python_version_label(spec.min)
        if min_v is None:
            raise ValueError(f"Invalid PythonVersions.min: {spec.min!r}")
    else:
        # Lowest version for current interpreter major
        min_v = (_py_version.major, 0)

    # ---- max ----
    raw_max = (spec.max or "").strip() if spec.max is not None else ""
    if not raw_max:
        # default: stay within the major version of min
        max_v = (min_v[0] + 1, 0)
        return PythonVersionBounds(min=min_v, max=max_v, max_op="<")

    if raw_max == "*":
        raise ValueError("PythonVersions.max='*' is not supported (unbounded upper range).")

    op = "<="
    rhs = raw_max
    if raw_max.startswith("<="):
        op, rhs = "<=", raw_max[2:].strip()
    elif raw_max.startswith("<"):
        op, rhs = "<", raw_max[1:].strip()
    # bare number treated as '<='
    v_max = parse_python_version_label(rhs)
    if v_max is None:
        raise ValueError(f"Invalid PythonVersions.max: {raw_max!r}")

    if op not in ("<", "<="):
        raise ValueError(f"Invalid comparator in PythonVersions.max: {raw_max!r}")

    return PythonVersionBounds(min=min_v, max=v_max, max_op=op)


def _version_in_python_bounds(version: tuple[int, int], bounds: PythonVersionBounds) -> bool:
    """
    Checks if the given version is within the specified Python version bounds.

    This function evaluates whether the provided Python version tuple satisfies the
    constraints defined in `PythonVersionBounds`. The check considers both minimum
    version constraints and maximum version constraints with operators.

    Args:
        version (Tuple[int, int]): The Python version to check, represented as a tuple
            of two integers (major, minor).
        bounds (PythonVersionBounds): The constraints for the version check, including
            minimum version, maximum version, and the operator for the maximum comparison.

    Returns:
        bool: True if the version is within the bounds, False otherwise.

    Raises:
        ValueError: If the `max_op` attribute in `bounds` contains an unexpected
            comparison operator.
    """
    if version < bounds.min:
        return False

    match bounds.max_op:
        case "<":
            return version < bounds.max
        case "<=":
            return version <= bounds.max
        case _:
            raise ValueError(f"Unexpected max_op {bounds.max_op!r}")


def _major_in_python_bounds(major: int, bounds: PythonVersionBounds) -> bool:
    """
    Determines if a provided major version falls within the defined version bounds.

    This function verifies whether a given major version number satisfies the
    constraints of the specified `PythonVersionBounds` object. The comparison
    rules depend on the `max_op` value within the `bounds`.

    Args:
        major (int): The major version to check against the bounds.
        bounds (PythonVersionBounds): An object containing the minimum and maximum
            version constraints as well as the operator that defines the upper bound
            behavior.

    Returns:
        bool: True if the provided major version is within the bounds, otherwise False.

    Raises:
        ValueError: If an unexpected or unsupported value for `max_op` is encountered.
    """
    min_major, _ = bounds.min
    if major < min_major:
        return False

    max_major, max_minor = bounds.max

    match bounds.max_op:
        case "<":
            # Need some minor with (major, minor) < max.
            if major < max_major:
                return True
            if major == max_major:
                # We need at least one minor < max_minor.
                return max_minor > 0
            return False
        case "<=":
            # There is a minor <= max iff major <= max_major.
            return major <= max_major
        case _:
            raise ValueError(f"Unexpected max_op {bounds.max_op!r}")


# ---------------------------------------------------------------------------
# Compatibility evaluator
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class CompatibilityEvaluator:
    """
    Evaluates compatibility based on provided specifications, including interpreters, ABIs,
    and platforms. The class is designed for compatibility evaluation of Python distributions,
    allowing filtering and validation against a defined set of rules and constraints.

    This evaluator preprocesses the provided specifications at initialization to optimize
    compatibility checks for interpreters, ABIs, and platforms. It supports features such as
    specific inclusions and exclusions, specific-only whitelisting, universal forms, and bounds
    validation.

    Attributes:
        spec (CompatibilitySpec): The main specification defining the compatibility rules,
            including Python versions, ABIs, and platform-specific constraints.
        tags (Set[Tag]): A set of explicitly accepted tags derived from the provided compatibility
            specifications.
        exclude_tags (Set[Tag]): A set of explicitly excluded tags derived from the specifications.
    """
    spec: CompatibilitySpec
    tags: set[Tag] = field(default_factory=set)
    exclude_tags: set[Tag] = field(default_factory=set)

    # internal
    _py_bounds: Optional[PythonVersionBounds] = field(init=False, default=None)
    _tags_specific_only: bool = field(init=False, default=False)
    _tags_whitelist: set[Tag] = field(init=False, default_factory=set)

    def __post_init__(self) -> None:
        # Precompute Python version bounds
        self._py_bounds = _compute_python_version_bounds(self.spec.python_versions)

        # Precompute explicit tag profiles from CompatibilityTagsSpec
        for profile in self.spec.compatibility_tags.values():
            parsed_specific: set[Tag] = set()
            for s in profile.specific:
                parsed_specific.update(parse_tag(s))
            self.tags.update(parsed_specific)

            if profile.specific_only:
                self._tags_specific_only = True
                self._tags_whitelist.update(parsed_specific)

            for s in profile.excludes:
                self.exclude_tags.update(parse_tag(s))

    # ---------------- Python interpreter ----------------

    def accept_interpreter(self, interpreter: str) -> bool:
        """
        Checks if the provided interpreter part of a tag (e.g., 'cp311', 'py3') is accepted
        according to the PythonVersionsSpec.

        The method applies several rules to validate the interpreter:
          1. Explicit excludes: Rejects interpreters explicitly listed in `spec.excludes`.
          2. Specific-only rule: If `specific_only` is True, only interpreters explicitly
             listed in `spec.specific` are allowed.
          3. Additive specifics: If `specific_only` is False, interpreters explicitly listed
             in `spec.specific` are always allowed.
          4. Universal form ('pyX'): Allows 'pyX' universal interpreters (major Python versions),
             if `accept_universal` is True and the major version lies within the specified bounds.
          5. Concrete versions: Interpreters that map to a specific major/minor version
             are allowed if they fall within the specified bounds.

        Unrecognized or unparsable interpreters are always rejected.

        Args:
            interpreter (str): The interpreter label to check (e.g., 'cp311', 'py3').

        Raises:
            RuntimeError: If Python version bounds are not initialized.

        Returns:
            bool: True if the interpreter is accepted, False otherwise.
        """
        spec = self.spec.python_versions
        bounds = self._py_bounds
        if bounds is None:
            raise RuntimeError("Python version bounds not initialized")

        # 1) explicit excludes
        if interpreter in spec.excludes:
            return False

        # 2) specific_only → pure whitelist
        if spec.specific_only:
            return interpreter in spec.specific

        # 3) additive specifics
        if interpreter in spec.specific:
            return True

        # 4) 'pyX' universal form (single-digit major)
        if spec.accept_universal:
            m = re.match(r"^py(\d+)$", interpreter)
            if m:
                major = int(m.group(1))
                return _major_in_python_bounds(major, bounds)

        # 5) everything else must map to a concrete version in-range
        v = parse_python_version_label(interpreter)
        if v is None:
            # No guessing: if we can't map it, we don't accept it.
            return False

        return _version_in_python_bounds(v, bounds)

    # ---------------- ABI ----------------

    def accept_abi(self, abi: str) -> bool:
        """
        Checks the ABI (Application Binary Interface) part of a tag against specified
        rules defined by the AbiValuesSpec. The function verifies if the provided ABI
        adheres to constraints such as specific inclusion or exclusion rules, and
        Python version compatibility.

        The rules applied are as follows:

        1. Exclude specified ABIs.
        2. If `specific_only` is True:
           - Allow only specified ABI values minus exclusions.
        3. Otherwise:
           - Allow additive specific ABIs.
           - Allow debug ABIs only if `include_debug` is True.
           - Allow stable ABIs (e.g., 'abi3', 'none') only if `include_stable`
             is True and their major version is within Python version bounds.
           - Allow other concrete Python-versioned ABIs (e.g., 'cp311') only if
             they map to a Python version within bounds.
        4. Reject unknown ABIs.

        Args:
            abi (str): The ABI part of the tag (e.g., 'cp311', 'abi3', 'none')
                to be checked against the specification.

        Returns:
            bool: True if the ABI passes the checks and aligns with the specifications,
            otherwise False.

        Raises:
            RuntimeError: If the Python version bounds are not initialized.
        """
        spec: AbiValuesSpec = self.spec.abi_values
        bounds = self._py_bounds
        if bounds is None:
            raise RuntimeError("Python version bounds not initialized")

        # 1) excludes
        if abi in spec.excludes:
            return False

        # 2) specific_only → pure whitelist
        if spec.specific_only:
            return abi in spec.specific

        # 3) additive specifics
        if abi in spec.specific:
            return True

        # 4) debug ABIs
        if is_debug_abi(abi) and not spec.include_debug:
            return False

        # 5) stable ABIs
        if is_stable_abi(abi):
            if not spec.include_stable:
                return False
            if abi == "none":
                return True
            # abiX -> stable ABI for major X
            m = re.search(r"(\d+)$", abi)
            if not m:
                return False
            major = int(m.group(1))
            return _major_in_python_bounds(major, bounds)

        # 6) cpXYZ-style ABIs: must map to a concrete version in-range
        v = parse_python_version_label(abi)
        if v is None:
            return False

        return _version_in_python_bounds(v, bounds)

    # ---------------- Platform ----------------

    def accept_platform(self, platform: str) -> bool:
        """
        Evaluates whether a given platform string conforms to the platform specifications
        defined under the `PlatformValues`. The function performs a series of checks and rules
        to determine if the platform should be accepted or rejected, based on explicit excludes,
        specific entries, specific-only behavior, and family-based criteria. The evaluation
        is fail-closed unless explicitly allowed through the specifications.

        Args:
            platform (str): The platform tag to be checked, typically formatted as
                'flavor_version_arch' (e.g., 'manylinux_2_17_x86_64').

        Returns:
            bool: True if the platform is accepted according to the specifications,
            False otherwise.
        """
        platform_specs: Mapping[str, PlatformOSSpec] = self.spec.platform_values

        # No platform constraints at all -> reject everything by default.
        if not platform_specs:
            return False

        # 1) excludes
        for os_spec in platform_specs.values():
            if platform in os_spec.excludes:
                return False

        # 2) specific_only → whitelist union
        specific_only_specs = [
            os_spec for os_spec in platform_specs.values() if os_spec.specific_only
        ]
        if specific_only_specs:
            whitelist: set[str] = set()
            for os_spec in specific_only_specs:
                whitelist.update(os_spec.specific)
            return platform in whitelist

        # 3) additive specifics
        for os_spec in platform_specs.values():
            if platform in os_spec.specific:
                return True

        # 4) family-based rules
        flavor, version, arch = split_platform_tag(platform)

        family_spec: Optional[PlatformFamilySpec] = None
        owning_os_spec: Optional[PlatformOSSpec] = None

        for os_spec in platform_specs.values():
            fam = os_spec.families.get(flavor)
            if fam is not None:
                family_spec = fam
                owning_os_spec = os_spec
                break

        if family_spec is None:
            # No OS spec describes this flavor
            return False

        # OS-level arch filter
        if owning_os_spec and owning_os_spec.arches:
            if arch is None or arch not in owning_os_spec.arches:
                return False

        # Family-level version filter (supports '*' as unbounded)
        if (family_spec.min or family_spec.max) and version is None:
            return False

        if version is not None:
            v_tuple = parse_glibc_like_version(version)

            if family_spec.min and family_spec.min != "*":
                min_v = parse_glibc_like_version(family_spec.min)
                if v_tuple < min_v:
                    return False

            if family_spec.max and family_spec.max != "*":
                max_v = parse_glibc_like_version(family_spec.max)
                if v_tuple > max_v:
                    return False

        return True

    # ---------------- Full tag / top-level ----------------

    def accept_tag(self, tag: Tag) -> bool:
        """
        Determines whether the given tag is acceptable based on its interpreter,
        ABI, and platform. A tag is considered acceptable if its interpreter, ABI,
        and platform meet specific acceptance criteria.

        Args:
            tag (Tag): The tag to evaluate for acceptance.

        Returns:
            bool: True if the tag is acceptable; otherwise, False.
        """
        return (
            self.accept_interpreter(tag.interpreter)
            and self.accept_abi(tag.abi)
            and self.accept_platform(tag.platform)
        )

    def evaluate_compatibility(self, tag_str: str) -> bool:
        """
        Evaluates whether a given tag string is compatible based on the defined
        rules and profiles.

        The function evaluates the compatibility of a tag string against a series
        of conditions defined by tag-specific exclusions, whitelist, and rules
        based on interpreter, ABI, and platform. The evaluation considers the
        precedence of these conditions to determine whether the tag string is
        accepted as compatible.

        Args:
            tag_str (str): The tag string to evaluate, typically containing
                version, ABI, and platform information (e.g.,
                'cp311-cp311-manylinux_2_17_x86_64').

        Returns:
            bool: True if the tag string is considered compatible, False otherwise.
        """
        tag = next(iter(parse_tag(tag_str)))

        # Tag-level excludes
        if tag in self.exclude_tags:
            return False

        # Tag-specific whitelist mode
        if self._tags_specific_only:
            return tag in self._tags_whitelist

        # Additive tag-specifics
        if tag in self.tags:
            return True

        # Fallback: axis-based rules
        return self.accept_tag(tag)
