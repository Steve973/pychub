from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Mapping

from ..helper.multiformat_deserializable_mixin import MultiformatDeserializableMixin
from ..helper.multiformat_serializable_mixin import MultiformatSerializableMixin


class SourceKind(str, Enum):
    CLI = "cli"
    FILE = "file"
    MAPPING = "mapping"
    TEST = "test"
    DEFAULT = "default"


class OperationKind(str, Enum):
    INIT = "init"
    MERGE_EXTEND = "merge_extend"
    MERGE_OVERRIDE = "merge_override"


@dataclass(slots=True)
class ProvenanceEvent(MultiformatSerializableMixin, MultiformatDeserializableMixin):
    source: SourceKind
    operation: OperationKind
    details: dict[str, Any] = field(default_factory=dict)

    def to_mapping(self) -> Mapping[str, Any]:
        return {
            "source": self.source.value,
            "operation": self.operation.value,
            "details": self.details,
        }

    @classmethod
    def from_mapping(cls, mapping: Mapping[str, Any], **_: Any) -> ProvenanceEvent:
        details_obj = mapping.get("details") or {}
        if not isinstance(details_obj, dict):
            raise TypeError(f"Expected 'details' to be a mapping, got {type(details_obj)!r}")
        return ProvenanceEvent(
            source=SourceKind(mapping.get("source")),
            operation=OperationKind(mapping.get("operation")),
            details=details_obj)
