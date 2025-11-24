from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Any

from pychub.helper.multiformat_deserializable_mixin import MultiformatDeserializableMixin
from pychub.helper.multiformat_serializable_mixin import MultiformatSerializableMixin

WheelKey = tuple[str, str]  # (normalized_name, version)


@dataclass(slots=True, frozen=True)
class ResolvedWheelNode(MultiformatSerializableMixin, MultiformatDeserializableMixin):
    """
    Represents minimal compatibility and download information for a resolved
    package (name, version) along with its dependencies.

    The class contains information about:
        - The package's identity (name and version).
        - Compatibility tags.
        - Dependencies on other packages.
        - Optional mapping of compatibility tags to download URLs.

    Attributes:
        name (str): The name of the resolved package.
        version (str): The version of the resolved package.
        _compatible_tags (frozenset of str): A frozenset of compatibility tags, e.g.,
            ("cp311-cp311-manylinux_2_28_x86_64", ...).
        dependencies (frozenset of WheelKey): A frozenset of dependencies where
            each WheelKey represents another package (name, version).
        tag_urls (Mapping[str, str] or None): An optional mapping of
            compatibility tags to their associated download URLs (key: compat_tag,
            value: full URL).
    """
    name: str
    version: str
    _compatible_tags: frozenset[str]  # e.g. ("cp311-cp311-manylinux_2_28_x86_64", ...)
    dependencies: frozenset[WheelKey]  # other nodes (name, version)
    tag_urls: Mapping[str, str] | None = None  # compat_tag -> full URL (optional)

    @property
    def key(self) -> WheelKey:
        """
        Gets the unique key of the wheel, which is a combination of its name and version.

        Returns:
            WheelKey: A tuple consisting of the wheel's name and version.
        """
        return self.name, self.version

    @property
    def compatible_tags(self) -> list[str]:
        """
        Returns a sorted list of compatible tags.

        The method retrieves the compatible tags, sorts them, and returns them as a
        list. It ensures the returned list is in a consistent order.

        Returns:
            list[str]: A sorted list of compatible tags.
        """
        return sorted(list(self._compatible_tags))

    def to_mapping(self) -> Mapping[str, Any]:
        """
        Converts the current object to a mapping representation.

        This method creates a dictionary representation of the object's attributes,
        allowing for structured access to its key properties and data. The format of
        the mapping includes information about the name, version, compatible tags,
        dependencies, and tag URLs.

        Returns:
            Mapping[str, Any]: A dictionary containing the mapping representation of
            the current object.

        """
        return {
            "name": self.name,
            "version": self.version,
            "compatible_tags": self.compatible_tags,
            "dependencies": [
                {"name": n, "version": v}
                for (n, v) in sorted(self.dependencies)
            ],
            "tag_urls": dict(self.tag_urls) if self.tag_urls is not None else None,
        }

    @classmethod
    def from_mapping(cls, mapping: Mapping[str, Any], **_: Any) -> ResolvedWheelNode:
        """
        Create a ResolvedWheelNode instance from a provided mapping.

        This method is used to create an instance of the ResolvedWheelNode
        class by interpreting a dictionary-like mapping. The mapping is
        expected to include keys for the name, version, and optionally
        dependencies, compatible tags, and tag URLs.

        Args:
            mapping (Mapping[str, Any]): The input dictionary-like mapping
                containing data required for initializing the class instance.
                Expected keys include:
                - "name": A string representing the name of the node.
                - "version": A string representing the version of the node.
                - "dependencies": An optional list of dictionaries, each containing
                  "name" and "version" fields, representing the dependencies of
                  the node.
                - "compatible_tags": An optional list of strings indicating the
                  compatible tags for the node.
                - "tag_urls": An optional dictionary mapping tags to their
                  corresponding URLs.

            **_ (Any): Additional arguments that are ignored in this method.

        Returns:
            ResolvedWheelNode: A newly created instance of the ResolvedWheelNode
            class, populated based on the provided mapping.
        """
        deps_iter = mapping.get("dependencies") or []
        deps = frozenset((d["name"], d["version"]) for d in deps_iter)
        tag_urls_raw = mapping.get("tag_urls")
        tag_urls = dict(tag_urls_raw) if tag_urls_raw is not None else None
        return cls(
            name=str(mapping["name"]),
            version=str(mapping["version"]),
            _compatible_tags=frozenset(mapping.get("compatible_tags", [])),
            dependencies=deps,
            tag_urls=tag_urls)


@dataclass(slots=True)
class CompatibilityResolution(MultiformatSerializableMixin, MultiformatDeserializableMixin):
    """
    Result of resolving a chub's dependency tree against a CompatibilitySpec.

    This class represents the result of resolving a dependency tree for a chub
    package against a provided compatibility specification. It includes the
    starting points of resolution (roots) and the resulting mapping of nodes.
    The nodes detail connections and dependencies within the tree. The purpose
    of this class is to validate whether all root nodes and dependency
    relationships are fully resolved as part of the initialization process.

    Attributes:
        _roots (set[WheelKey]): The starting (name, version) nodes representing
            the chub's dependencies as requested by the user.
        nodes (dict[WheelKey, ResolvedWheelNode]): A canonical mapping from
            (name, version) pairs to ResolvedWheelNodes representing resolved
            dependencies and their metadata.
    """
    _roots: set[WheelKey]
    nodes: dict[WheelKey, ResolvedWheelNode]

    def __post_init__(self) -> None:
        """
        Validates the topology of nodes and dependencies after initialization.

        This method performs two key checks:
        1. Ensures that all root nodes specified in the `_roots` attribute exist within the `nodes` dictionary.
        2. Verifies that all dependencies mentioned in each node's `dependencies` list are present as keys
           in the `nodes` dictionary.

        Raises:
            ValueError: If any root nodes specified in `_roots` are missing from the keys of `nodes`.
            ValueError: If dependencies in any node's `dependencies` list reference missing keys within `nodes`.

        """
        node_keys = set(self.nodes.keys())

        # All roots must exist
        missing_roots = self._roots - node_keys
        if missing_roots:
            raise ValueError(f"Root nodes without metadata: {missing_roots}")

        # All dependencies must exist
        missing_deps: set[WheelKey] = set()
        for node in self.nodes.values():
            for dep_key in node.dependencies:
                if dep_key not in node_keys:
                    missing_deps.add(dep_key)

        if missing_deps:
            raise ValueError(f"Dependencies refer to missing nodes: {missing_deps}")

    @property
    def roots(self) -> list[WheelKey]:
        """
        Gets the roots of the wheel keys.

        The roots represent a sorted list extracted from the internal data structure,
        which contains the foundational wheel keys.

        Returns:
            list[WheelKey]: A sorted list of wheel keys that are considered roots.
        """
        return sorted(list(self._roots))

    def to_mapping(self) -> Mapping[str, Any]:
        """
        Converts the instance data into a mapping structure.

        This method transforms the object's roots and nodes attributes into a structured
        mapping, where roots are represented as a list of dictionaries, and nodes are
        mapped by their name and version as keys to their respective mapping representations.

        Returns:
            Mapping[str, Any]: A mapping that contains the serialized structure of roots
            and nodes. The roots are a list of dictionaries containing "name" and "version".
            The nodes are represented as a dictionary, where each key is a string
            combining the node's name and version, and the value is the node's mapping
            representation.
        """
        return {
            "roots": [
                {"name": n, "version": v} for (n, v) in self.roots
            ],
            "nodes": {
                f"{n}=={v}": node.to_mapping() for (n, v), node in self.nodes.items()
            },
        }

    @classmethod
    def from_mapping(cls, mapping: Mapping[str, Any], **_: Any) -> CompatibilityResolution:
        """
        Constructs a CompatibilityResolution object from a mapping representation.

        Args:
            mapping (Mapping[str, Any]): A dictionary representing the mapping structure.
                Must contain keys "roots" and "nodes".
            **_ (Any): Additional keyword arguments that are ignored.

        Returns:
            CompatibilityResolution: An instance of the CompatibilityResolution class
            created based on the given mapping.

        Raises:
            KeyError: If certain expected keys are missing in the input mapping.
            TypeError: If the provided mapping does not conform to the expected format.
        """
        root_items = mapping.get("roots") or []
        roots: set[WheelKey] = {(r["name"], r["version"]) for r in root_items}
        raw_nodes = mapping.get("nodes") or {}
        nodes: dict[WheelKey, ResolvedWheelNode] = {}
        for _key_str, node_mapping in raw_nodes.items():
            node = ResolvedWheelNode.from_mapping(node_mapping)
            nodes[node.key] = node
        return cls(_roots=roots, nodes=nodes)