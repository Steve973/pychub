from datetime import datetime, date
from enum import Enum
from pathlib import Path
from typing import Any, Mapping

from pychub.helper.toml_utils import dump_toml_to_str


def _normalize(value: Any) -> Any:
    # Path -> POSIX string
    if isinstance(value, Path):
        return value.as_posix()

    # Enums -> their value
    if isinstance(value, Enum):
        return value.value

    # Mappings -> dict with sorted keys
    if isinstance(value, Mapping):
        return {
            str(k): _normalize(v)
            for k, v in sorted(value.items(), key=lambda kv: str(kv[0]))
        }

    # Sets/frozensets -> sorted list
    if isinstance(value, (set, frozenset)):
        return sorted(_normalize(v) for v in value)

    # lists/tuples -> list, normalized elementwise
    if isinstance(value, (list, tuple)):
        return [_normalize(v) for v in value]

    return value


class MultiformatSerializableMixin:
    """
    Mixin for models to support JSON, YAML, and TOML serialization via to_mapping().
    """

    def mapping_hash(self) -> str:
        """
        Compute a stable hash of the semantic mapping representation.
        """
        import hashlib
        import json

        normalized = _normalize(self.to_mapping())  # as before
        payload = json.dumps(
            normalized,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")

        return hashlib.new("sha512", payload).hexdigest()

    def to_mapping(self, *args, **kwargs):
        raise NotImplementedError(
            f"{self.__class__.__name__} must implement to_mapping() "
            "to use MultiformatSerializableMixin serialization.")

    def to_json(self, *, indent=2) -> str:
        import json
        return json.dumps(self.to_mapping(), ensure_ascii=False, indent=indent, sort_keys=True)

    def to_yaml(self, *, indent=2) -> str:
        try:
            import yaml
        except ImportError:
            raise RuntimeError("PyYAML not installed")
        return yaml.safe_dump(self.to_mapping(), sort_keys=True, allow_unicode=True, indent=indent)

    def to_toml(self, *, indent=2) -> str:
        def sort_dict(obj):
            if isinstance(obj, dict):
                return {k: sort_dict(obj[k]) for k in sorted(obj)}
            elif isinstance(obj, list):
                return [sort_dict(item) for item in obj]
            else:
                return obj

        sorted_mapping = sort_dict(self.to_mapping())
        return dump_toml_to_str(sorted_mapping, indent)

    def serialize(self, *, fmt='json', indent=2) -> str:
        if fmt == 'json':
            return self.to_json(indent=indent)
        elif fmt == 'yaml':
            return self.to_yaml(indent=indent)
        elif fmt == 'toml':
            return self.to_toml()
        else:
            raise ValueError(f"unrecognized format: {fmt}")

    def flat_summary(
            self,
            first_fields=("timestamp",),
            last_fields=(),
            sep=" | ",
            exclude=(),
            include_empty=False):
        """
        Produce a readable, ordered string summary from to_mapping().
        - Fields in first_fields go first (if present)
        - Then others, alphabetically, except exclude/first/last
        - Then last_fields (if present)
        - By default, omits fields that are None or empty unless include_empty=True
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