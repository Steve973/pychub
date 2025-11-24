from __future__ import annotations

import datetime
import functools
import uuid
from collections.abc import Mapping, Callable
from dataclasses import dataclass, field
from enum import Enum
from types import MappingProxyType
from typing import Any, Optional, ParamSpec, TypeVar

from pychub.helper.multiformat_deserializable_mixin import MultiformatDeserializableMixin
from pychub.helper.multiformat_serializable_mixin import MultiformatSerializableMixin
from pychub.package.context_vars import current_build_plan

P = ParamSpec("P")
R = TypeVar("R")


# --------------------------------------------------------------------------- #
# Typed + runtime-safe event type definition
# --------------------------------------------------------------------------- #

class StageType(str, Enum):
    LIFECYCLE = "LIFECYCLE"  # the overall orchestration: start → complete
    INIT = "INIT"  # CLI parsing, environment checks, caching
    PLAN = "PLAN"  # dependency resolution, wheel analysis, SBOM generation
    EXECUTE = "EXECUTE"  # build or other actions based on the plan
    CLEANUP = "CLEANUP"  # optional teardown or post-build validation


class LevelType(str, Enum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARN = "WARN"
    ERROR = "ERROR"


class EventType(str, Enum):
    ABORTED = "ABORTED"  # An action was conditionally aborted
    ACTION = "ACTION"  # Meaningful step taken (copy, build, inject)
    ANNOTATION = "ANNOTATION"
    CHECKPOINT = "CHECKPOINT"  # Mid-stage milestone or marker
    COMPLETE = "COMPLETE"  # Successfully finished
    DECISION = "DECISION"  # Conditional logic branch taken
    DEFERRED = "DEFERRED"  # Action intentionally delayed
    EXCEPTION = "EXCEPTION"  # Indicates exception-related event
    FAIL = "FAIL"  # Stage failed, unrecoverable
    INPUT = "INPUT"  # External input received or used
    OUTPUT = "OUTPUT"  # Artifact produced (file, archive, metadata)
    RESOLVE = "RESOLVE"  # Item was resolved (e.g., dependency, strategy)
    SKIP = "SKIP"  # Intentionally bypassed
    START = "START"  # Beginning of a stage or substage
    VALIDATION = "VALIDATION"  # Validation event


class AnnotationType(str, Enum):
    AMENDS = "AMENDS"  # Replaces or corrects a prior event
    COMMENT = "COMMENT"  # Human or system note, no functional change
    RELATES_TO = "RELATES_TO"  # Links to another event semantically
    SUPPLEMENTS = "SUPPLEMENTS"  # Adds context or extra data


def audit(stage: StageType, substage: str | None = None) -> Callable[[Callable[P, R]], Callable[P, R]]:
    def decorator(fn: Callable[P, R]) -> Callable[P, R]:
        @functools.wraps(fn)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            plan = current_build_plan.get()
            if plan is None:
                raise RuntimeError("No active BuildPlan in context for @audit-decorated function")

            plan.audit_log.append(
                BuildEvent.make(
                    stage,
                    EventType.START,
                    substage=substage,
                )
            )

            try:
                result = fn(*args, **kwargs)
                plan.audit_log.append(
                    BuildEvent.make(
                        stage,
                        EventType.COMPLETE,
                        substage=substage,
                    )
                )
                return result
            except Exception as e:
                plan.audit_log.append(
                    BuildEvent.make(
                        stage,
                        EventType.EXCEPTION,
                        LevelType.ERROR,
                        substage=substage,
                        message=str(e),
                    )
                )
                raise

        return wrapper

    return decorator


# --------------------------------------------------------------------------- #
# Data model
# --------------------------------------------------------------------------- #

@dataclass(slots=True, frozen=True)
class BuildEvent(MultiformatSerializableMixin, MultiformatDeserializableMixin):
    """
    Immutable, context-aware audit event model.

    Each BuildEvent instance is a complete factual snapshot.
    ANNOTATION events extend prior events without altering them.
    """
    annotation_type: AnnotationType | None = None
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    event_type: EventType = EventType.ACTION
    level: LevelType = LevelType.INFO
    message: Optional[str] = field(default=None)
    payload: Mapping[str, Any] | None = field(default=None)
    stage: StageType | None = None
    substage: Optional[str] = field(default=None)
    timestamp: datetime.datetime = field(
        default_factory=lambda: datetime.datetime.now(datetime.timezone.utc))

    def __post_init__(self):
        if not isinstance(self.stage, StageType):
            raise TypeError("BuildEvent.stage must be a StageType")
        if not isinstance(self.event_type, EventType):
            raise TypeError("BuildEvent.event_type must be an EventType")
        if not isinstance(self.level, LevelType):
            raise TypeError("BuildEvent.level must be a LevelType")
        if self.annotation_type is not None:
            if not isinstance(self.annotation_type, AnnotationType):
                raise TypeError("BuildEvent.annotation_type must be an AnnotationType")
            if self.event_type != EventType.ANNOTATION:
                raise ValueError("BuildEvent.annotation_type can only be set for ANNOTATION events")
        if self.event_type == EventType.ANNOTATION:
            if self.annotation_type is None:
                raise ValueError("BuildEvent.annotation_type must be set for ANNOTATION events")

    def to_mapping(self) -> dict[str, Any]:
        return {
            "annotation_type": self.annotation_type.value if self.annotation_type else None,
            "event_id": self.event_id,
            "event_type": self.event_type.value,
            "level": self.level.value,
            "message": self.message or "",
            "payload": self.payload or {},
            "stage": self.stage.value if self.stage else None,
            "substage": self.substage or "",
            "timestamp": self.timestamp.isoformat(),
        }

    @classmethod
    def make(
            cls,
            stage: StageType,
            event_type: EventType,
            level: LevelType = LevelType.INFO,
            annotation_type: AnnotationType | None = None,
            *,
            substage: str | None = None,
            message: str | None = None,
            payload: dict[str, Any] | None = None) -> BuildEvent:
        """Convenience factory for constructing and timestamping BuildEvents uniformly."""
        frozen_payload = MappingProxyType(payload or {})
        return cls(
            stage=stage,
            substage=substage,
            event_type=event_type,
            annotation_type=annotation_type,
            level=level,
            message=message,
            payload=frozen_payload)

    @classmethod
    def from_mapping(cls, mapping: Mapping[str, Any], **_: Any) -> BuildEvent:
        annotation_type = AnnotationType(mapping.get("annotation_type")) if mapping.get("annotation_type") else None
        event_type = EventType(mapping.get("event_type", EventType.ACTION.value))
        level = LevelType(mapping.get("level", LevelType.INFO.value))
        stage = StageType(mapping.get("stage", StageType.LIFECYCLE.value))

        return BuildEvent(
            annotation_type=annotation_type,
            event_id=mapping.get("event_id", str(uuid.uuid4())),
            event_type=event_type,
            level=level,
            message=mapping.get("message"),
            payload=mapping.get("payload"),
            stage=stage,
            substage=mapping.get("substage"),
            timestamp=datetime.datetime.fromisoformat(
                mapping.get("timestamp", datetime.datetime.now(datetime.timezone.utc).isoformat())))
