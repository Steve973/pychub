from __future__ import annotations

from datetime import datetime, date
from enum import Enum
from pathlib import Path
from typing import Any, Mapping

from pychub.helper.toml_utils import dump_toml_to_str


def _normalize(value: Any) -> Any:
    """
    Normalizes various types of Python objects to consistent, standardized forms.

    This function processes input values of diverse types and converts them into a
    normalized representation. The normalization includes handling Path objects,
    Enums, mappings, sets, frozensets, lists, and tuples. It recursively processes
    nested structures when applicable, ensuring uniformity across all supported
    data types.

    Args:
        value (Any): The input value to be normalized. It supports various types
            such as Path, Enum, Mapping, sets, frozensets, lists, and tuples.

    Returns:
        Any: The normalized form of the input value. The output will be:
            - A POSIX string for Path types.
            - The stored value for Enum types.
            - A sorted dictionary for Mapping types, with stringified keys.
            - A sorted list for sets and frozensets, with normalized elements.
            - A list for list or tuple input, with elementwise normalization.
            - The original non-supported type if no specific transformation is
              applied.
    """
    # Path -> POSIX string
    match value:
        case Path():
            return value.as_posix()

        case Enum():
            return value.value

        case Mapping():
            return {
                str(k): _normalize(v)
                for k, v in sorted(value.items(), key=lambda kv: str(kv[0]))
            }

        case set() | frozenset():
            return sorted(_normalize(v) for v in value)

        case list() | tuple():
            return [_normalize(v) for v in value]

        case _:
            return value


class MultiformatSerializableMixin:
    """
    A mixin to add multi-format serialization support for custom objects.

    This mixin provides functionality to serialize an object's data into different
    formats, including JSON, YAML, and TOML. It also offers utilities for generating
    hashes, summaries, and customizable mapping transformations. Subclasses must
    implement specific methods to use this mixin effectively.
    """

    def mapping_hash(self) -> str:
        """
        Generates a SHA-512 hash based on the normalized representation of a mapping.

        This method computes a cryptographic hash by first normalizing the mapping
        through a specified normalization process. It serializes the normalized
        structure to JSON with specific settings (sorted keys and custom separators)
        to ensure consistent hash computation. Finally, it generates a SHA-512
        digest of the serialized payload.

        Returns:
            str: The hexadecimal representation of the SHA-512 hash.
        """
        import hashlib
        import json

        normalized = _normalize(self.to_mapping())  # as before
        payload = (
            json.dumps(
                normalized,
                sort_keys=True,
                separators=(",", ":"))
            .encode("utf-8"))

        return hashlib.new("sha512", payload).hexdigest()

    def to_mapping(self, *args, **kwargs):
        """
        Converts data into a mapping-like structure.

        This method is intended to be implemented by subclasses that use the
        MultiformatSerializableMixin. It must provide the logic for serializing
        data into a dictionary-like format.

        Args:
            *args: Variable length argument list for any additional parameters
                required for the conversion.
            **kwargs: Arbitrary keyword arguments for any extra options
                during the conversion.

        Raises:
            NotImplementedError: Raised when subclasses do not implement this
                method.
        """
        raise NotImplementedError(
            f"{self.__class__.__name__} must implement to_mapping() "
            "to use MultiformatSerializableMixin serialization.")

    def to_json(self, *, indent=2) -> str:
        """
        Converts the object's data to a JSON string.

        This method serializes the return value of the `to_mapping` method into a
        JSON-formatted string. It ensures non-ASCII characters are preserved, and
        the output is both indented and sorted by keys for better readability.

        Args:
            indent (int): Number of spaces to use as the indentation level in the
                generated JSON string. Defaults to 2.

        Returns:
            str: A string containing the JSON representation of the object's data.
        """
        import json
        return json.dumps(self.to_mapping(), ensure_ascii=False, indent=indent, sort_keys=True)

    def to_yaml(self, *, indent=2) -> str:
        """
        Converts the object's data to a YAML string representation.

        This method utilizes the PyYAML library to serialize the object's data,
        as obtained by its `to_mapping` method, into a YAML formatted string.
        It allows customization of the indentation level of the resulting YAML
        content.

        Args:
            indent (int): The number of spaces to use for indentation in the
                YAML output. Defaults to 2.

        Returns:
            str: The YAML string representation of the object's data.

        Raises:
            RuntimeError: If the PyYAML library is not installed on the system.
        """
        try:
            import yaml
        except ImportError:
            raise RuntimeError("PyYAML not installed")
        return yaml.safe_dump(self.to_mapping(), sort_keys=True, allow_unicode=True, indent=indent)

    def to_toml(self, *, indent=2) -> str:
        """
        Converts the instance's data to a TOML string.

        This method converts the object's data representation into a formatted TOML
        string. The data is first sorted in an order determined by the `sort_dict`
        function. The sorting ensures that dictionaries and lists are recursively
        ordered. After sorting, the data is serialized into a TOML string.

        Args:
            indent (int): Number of spaces to be used for indentation in the resulting
                TOML string.

        Returns:
            str: A TOML-formatted string representation of the object's data.
        """

        def sort_dict(obj):
            match obj:
                case dict():
                    return {k: sort_dict(obj[k]) for k in sorted(obj)}
                case list():
                    return [sort_dict(item) for item in obj]
                case _:
                    return obj

        sorted_mapping = sort_dict(self.to_mapping())
        return dump_toml_to_str(sorted_mapping, indent)

    def serialize(self, *, fmt='json', indent=2) -> str:
        """
        Serializes the object to a string in the specified format.

        This function allows exporting the object to a string representation
        in one of the supported formats: JSON, YAML, or TOML. The format
        is specified using the `fmt` parameter. Indentation for JSON and
        YAML formats can be customized using the `indent` parameter.

        Args:
            fmt (str): The format to serialize the object to. Supported formats
                are 'json', 'yaml', and 'toml'. Defaults to 'json'.
            indent (int): The number of spaces to use for indentation in JSON
                and YAML formatted output. Defaults to 2.

        Returns:
            str: The serialized representation of the object in the specified format.

        Raises:
            ValueError: If the specified format is not recognized or supported.
        """
        match fmt:
            case 'json':
                return self.to_json(indent=indent)
            case 'yaml':
                return self.to_yaml(indent=indent)
            case 'toml':
                return self.to_toml()
            case _:
                raise ValueError(f"unrecognized format: {fmt}")

    def flat_summary(
            self,
            first_fields=("timestamp",),
            last_fields=(),
            sep=" | ",
            exclude=(),
            include_empty=False):
        """
        Generate a flat summary representation of the object's data.

        The method retrieves the object's mapping representation, organizes its keys
        according to specified first and last fields while ordering the rest alphabetically,
        and creates a flat string representation of the data. Empty or None values are excluded
        unless explicitly included.

        Args:
            first_fields (tuple): A tuple of keys that should appear first in the summary,
                in the specified order.
            last_fields (tuple): A tuple of keys that should appear last in the summary,
                in the specified order.
            sep (str): The string used to separate different items in the summary.
            exclude (tuple): A tuple of keys that should be excluded from the summary.
            include_empty (bool): Whether to include empty fields (e.g., None, empty lists,
                dictionaries, or strings) in the summary.

        Returns:
            str: A flat string representation of the object's data.
        """
        mapping = self.to_mapping()
        all_keys = set(mapping.keys()) - set(exclude)
        first = [f for f in first_fields if f in all_keys]
        last = [f for f in last_fields if f in all_keys and f not in first]
        middle = sorted(all_keys - set(first) - set(last))
        ordered_keys = list(first) + middle + list(last)

        items = []
        for k in ordered_keys:
            v = mapping[k]
            # Filter if not including empty/None
            if not include_empty and (
                    v is None or v == "" or
                    (isinstance(v, (list, tuple, set, dict))
                     and not v)):
                continue

            if isinstance(v, (datetime, date)):
                v_str = v.isoformat(timespec='seconds') if isinstance(v, datetime) else v.isoformat()
            elif k.lower() == "payload" and isinstance(v, dict):
                try:
                    import json
                    v_str = json.dumps(v, separators=(',', ':'))
                except Exception:
                    v_str = repr(v)
            elif isinstance(v, dict):
                v_str = "{" + ", ".join(f"{kk}: {repr(v[kk])}" for kk in v.keys()) + "}"
            elif isinstance(v, (list, tuple, set)):
                v_str = "[" + ", ".join(repr(x) for x in v) + "]"
            else:
                v_str = str(v)
            items.append(f"{k}: {v_str}")
        return sep.join(items)

    def __str__(self):
        return self.flat_summary()
