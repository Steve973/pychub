from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Mapping

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
class ProvenanceEvent(MultiformatSerializableMixin):
    source: SourceKind
    operation: OperationKind
    details: dict[str, Any] = field(default_factory=dict)

    def to_mapping(self) -> Mapping[str, Any]:
        return {
            "source": self.source.value,
            "operation": self.operation.value,
            "details": self.details,
        }

    @staticmethod
    def from_mapping(m: Mapping[str, Any]) -> "ProvenanceEvent":
        return ProvenanceEvent(
            source=SourceKind(m.get("source")),
            operation=OperationKind(m.get("operation")),
            details=m.get("details")
        )
