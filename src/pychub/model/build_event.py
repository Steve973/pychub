from __future__ import annotations

import datetime
import json
from dataclasses import dataclass, field
from typing import Any, Optional, Literal, get_args

# --------------------------------------------------------------------------- #
# Typed + runtime-safe event type definition
# --------------------------------------------------------------------------- #

StageType = Literal[
    "LIFECYCLE",  # the overall orchestration: start → complete
    "INIT",       # CLI parsing, environment checks, caching
    "PLAN",       # dependency resolution, wheel analysis, SBOM generation
    "EXECUTE",    # build or other actions based on the plan
    "CLEANUP"     # optional teardown or post-build validation
]

STAGE_TYPES = set(get_args(StageType))

LevelType = Literal[
    "DEBUG",
    "INFO",
    "WARN",
    "ERROR"
]

LEVEL_TYPES = set(get_args(LevelType))

EventType = Literal[
    "ABORTED",       # An action was conditionally aborted
    "ACTION",        # Meaningful step taken (copy, build, inject)
    "CHECKPOINT",    # Mid-stage milestone or marker
    "COMPLETE",      # Successfully finished
    "DECISION",      # Conditional logic branch taken
    "DEFERRED",      # Action intentionally delayed
    "EXCEPTION",     # Indicates exception-related event
    "FAIL",          # Stage failed, unrecoverable
    "INPUT",         # External input received or used
    "OUTPUT",        # Artifact produced (file, archive, metadata)
    "RESOLVE",       # Item was resolved (e.g., dependency, strategy)
    "SKIP",          # Intentionally bypassed
    "START",         # Beginning of a stage or substage
    "VALIDATION",    # Validation event
]

EVENT_TYPES = set(get_args(EventType))


def audit(stage: StageType, substage: str | None = None):
    def decorator(fn):
        def wrapper(plan, *args, **kwargs):
            plan.audit_log.append(BuildEvent(stage=stage, substage=substage, event_type="START", level="INFO"))
            try:
                result = fn(plan, *args, **kwargs)
                plan.audit_log.append(BuildEvent(stage=stage, substage=substage, event_type="COMPLETE", level="INFO"))
                return result
            except Exception as e:
                plan.audit_log.append(
                    BuildEvent(stage=stage, substage=substage, event_type="EXCEPTION", level="ERROR", message=str(e))
                )
                raise
        return wrapper
    return decorator


# --------------------------------------------------------------------------- #
# Data model
# --------------------------------------------------------------------------- #

@dataclass(slots=True, frozen=True)
class BuildEvent:
    timestamp: datetime.datetime = field(
        default_factory=lambda: datetime.datetime.now(datetime.timezone.utc)
    )
    stage: StageType = field(default="")
    substage: Optional[str] = field(default=None)
    event_type: EventType = field(default="ACTION")
    level: LevelType = field(default="INFO")
    message: Optional[str] = field(default=None)
    payload: Optional[dict[str, Any]] = field(default=None)

    def __post_init__(self):
        if self.stage not in STAGE_TYPES:
            raise ValueError(f"Invalid stage '{self.stage}'. Must be one of {sorted(STAGE_TYPES)}.")

        if self.event_type not in EVENT_TYPES:
            raise ValueError(f"Invalid event_type '{self.event_type}'. Must be one of {sorted(EVENT_TYPES)}.")

    def to_mapping(self) -> dict[str, Any]:
        return {
            "timestamp": self.timestamp.isoformat(),
            "level": self.level,
            "event_type": self.event_type,
            "stage": self.stage,
            "substage": self.substage,
            "message": self.message,
            "payload": self.payload or {},
        }

    @staticmethod
    def from_mapping(m: dict[str, Any]) -> BuildEvent:
        raw_event_type = m.get("event_type", "ACTION")
        if raw_event_type not in EVENT_TYPES:
            raise ValueError(f"Invalid event_type '{raw_event_type}'. Must be one of {sorted(EVENT_TYPES)}.")

        raw_stage = m.get("stage", "")
        if raw_stage not in STAGE_TYPES:
            raise ValueError(f"Invalid stage '{raw_stage}'. Must be one of {sorted(STAGE_TYPES)}.")

        raw_level = m.get("level", "INFO")
        if raw_level not in LEVEL_TYPES:
            raise ValueError(f"Invalid level '{raw_level}'. Must be one of {sorted(LEVEL_TYPES)}.")

        return BuildEvent(
            timestamp=datetime.datetime.fromisoformat(
                m.get("timestamp", datetime.datetime.now(datetime.timezone.utc).isoformat(),)
            ),
            stage=m.get(raw_stage),     # type: ignore[arg-type]
            substage=m.get("substage"),
            event_type=raw_event_type,  # type: ignore[arg-type]
            level=raw_level,            # type: ignore[arg-type]
            message=m.get("message"),
            payload=m.get("payload"),
        )

    def as_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_mapping(), indent=indent)

    def __str__(self) -> str:
        ts = f"{self.timestamp.isoformat(timespec='seconds')}"
        lvl = f"level: {self.level}" if self.level else None
        evt = f"event: {self.event_type}" if self.event_type else None
        stg = [s for s in (str(self.stage), str(self.substage)) if s is not None]
        stg_sub = f"stage: {'/'.join(stg)}" if stg else None
        msg = f"message: '{self.message}'" if self.message else None
        p = f"payload: {json.dumps(self.payload, separators=(',', ':'))}" if self.payload else None
        fields = [f for f in (ts, lvl, evt, stg_sub, msg, p) if f is not None]
        return " | ".join(fields)
