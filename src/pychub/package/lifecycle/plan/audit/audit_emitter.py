import logging
import sys
from pathlib import Path
from typing import Optional

from pychub.model.build_event import BuildEvent
from pychub.model.buildplan_model import BuildPlan
from pychub.package.context_vars import current_build_plan

_LOG_FILE_NAME = "build.audit.json"


def to_logging_level(event_type: str) -> int:
    return logging.DEBUG if event_type.upper() == "DEBUG" else logging.INFO


def emit_event(logger: logging.Logger, event: BuildEvent, indent: int = 2) -> None:
    level = to_logging_level(event.event_type)
    logger.log(level, event.to_json(indent=indent))


def emit_all(logger: logging.Logger, events: list[BuildEvent], indent: int = 2) -> None:
    for event in events:
        emit_event(logger, event, indent=indent)


def configure_emitter(dest: list[str], level: int = logging.INFO) -> logging.Logger:
    logger = logging.getLogger("pychub.audit")
    logger.setLevel(level)
    logger.propagate = False

    for d in dest:
        handler: logging.Handler
        if d == "stdout":
            handler = logging.StreamHandler(sys.stdout)
        elif d == "stderr":
            handler = logging.StreamHandler(sys.stderr)
        elif d.startswith("file:"):
            path = d[len("file:"):]
            handler = logging.FileHandler(path)
        else:
            raise ValueError(f"Unknown audit log destination: {d}")

        handler.setFormatter(logging.Formatter('%(message)s'))
        logger.addHandler(handler)

    return logger


def emit_audit_log(
        build_plan: BuildPlan,
        dest: str = "file",
        path: Optional[Path] = None,
        indent: int = 2) -> None:
    """
    Write the build audit log to a file or stream.

    Args:
        build_plan: The BuildPlan containing audit events
        dest: space separated values of 'stdout', 'stderr', or 'file'
        path: If dest='file', the path to write to (default: <plan.staging_dir>/build.audit.json)
        indent: JSON indentation level
    """
    build_plan = build_plan or current_build_plan.get()
    if not build_plan:
        raise ValueError("No build plan found; cannot emit audit log")
    dests = []
    for d in dest.split(" "):
        if d == "file" and path is None:
            dests.append(f"file:{build_plan.cache_root}/{build_plan.project_dir}/{_LOG_FILE_NAME}")
        else:
            dests.append(d)
    logger = configure_emitter(dests)
    emit_all(logger, build_plan.audit_log, indent)
