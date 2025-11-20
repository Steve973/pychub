import logging
import sys
from pathlib import Path
from typing import Optional

from pychub.model.build_event import BuildEvent
from pychub.model.buildplan_model import BuildPlan
from pychub.package.context_vars import current_build_plan

_LOG_FILE_NAME = "build.audit.json"


def to_logging_level(event_type: str) -> int:
    """
    Converts an event type string to its corresponding logging level.

    The function takes an event type string, checks if it matches "DEBUG" (case
    insensitive), and returns the corresponding logging level defined in the
    logging module. If the event type is not "DEBUG", it defaults to returning
    the INFO logging level.

    Args:
        event_type (str): The type of the event, typically represented as a string.
            Expected values are case-insensitive, e.g., "DEBUG".

    Returns:
        int: The corresponding logging level (DEBUG or INFO) as defined in
            the logging module.
    """
    return logging.DEBUG if event_type.upper() == "DEBUG" else logging.INFO


def emit_event(logger: logging.Logger, event: BuildEvent, indent: int = 2) -> None:
    """
    Emits a build event to the specified logger with the provided logging level derived
    from the event type. The event is serialized into JSON format with a specified indentation
    level and then logged.

    Args:
        logger (logging.Logger): The logger instance used for emitting the event log message.
        event (BuildEvent): The build event instance that contains event data and metadata.
        indent (int): The number of spaces used for JSON indentation. Defaults to 2.

    Returns:
        None
    """
    level = to_logging_level(event.event_type)
    logger.log(level, event.to_json(indent=indent))


def emit_all(logger: logging.Logger, events: list[BuildEvent], indent: int = 2) -> None:
    """
    Emit all provided build events using the given logger.

    This function iterates through a list of build events and emits each one by
    delegating to the `emit_event` function. An optional indentation level can
    be specified to control the formatting of logged messages.

    Args:
        logger (logging.Logger): A logger instance used to record events.
        events (list[BuildEvent]): A list of build events to be emitted.
        indent (int): Optional indentation level for formatting log messages.
            Defaults to 2.
    """
    for event in events:
        emit_event(logger, event, indent=indent)


def configure_emitter(dest: list[str], level: int = logging.INFO) -> logging.Logger:
    """
    Configures and returns a logger for audit purposes. The logger can output audit logs to multiple
    destinations such as stdout, stderr, or files. If the destinations are not valid, a ValueError
    is raised. Existing handlers of the logger are cleared before applying the new configuration.

    Args:
        dest (list[str]): A list of destinations for the logger outputs. Supported destinations:
            - "stdout": Output logs to the standard output.
            - "stderr": Output logs to the standard error.
            - "file:<path>": Output logs to a file at the specified path. Replace `<path>` with
              the desired file path.
        level (int, optional): The logging level. Defaults to `logging.INFO`.

    Returns:
        logging.Logger: The configured logger instance.
    """
    logger = logging.getLogger("pychub.audit")
    logger.setLevel(level)
    logger.propagate = False
    logger.handlers.clear()

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
    Emits an audit log according to the specified build plan.

    This function generates an audit log based on the provided build plan, output
    destination(s), and optional formatting options. It ensures that the log is
    properly emitted to the desired destinations.

    Args:
        build_plan (BuildPlan): The build plan from which the audit log is generated.
        dest (str): The destination for the audit log. Multiple destinations can be
            specified as a space-separated string. Defaults to "file".
        path (Optional[Path]): An optional file path to write the log when the destination
            includes "file". If not provided, a default path is derived.
        indent (int): The number of spaces used for indenting the log entries. Defaults
            to 2.

    Raises:
        ValueError: If the build plan is not provided or is invalid.
    """

    if not build_plan:
        raise ValueError("No build plan found; cannot emit audit log")
    default_path = build_plan.project_staging_dir / _LOG_FILE_NAME
    dests = []
    for d in dest.split(" "):
        if d == "file" and path is None:
            dests.append(f"file:{default_path}")
        else:
            dests.append(d)
    logger = configure_emitter(dests)
    emit_all(logger, build_plan.audit_log, indent)
