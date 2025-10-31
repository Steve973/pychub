import logging
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch, call, mock_open

import pytest

from pychub.package.lifecycle.plan.audit.audit_emitter import (
    to_logging_level,
    emit_event,
    emit_all,
    configure_emitter,
    emit_audit_log,
    _LOG_FILE_NAME,
)


# Test to_logging_level
def test_to_logging_level_debug():
    """Test that DEBUG event type maps to logging.DEBUG."""
    assert to_logging_level("DEBUG") == logging.DEBUG


def test_to_logging_level_debug_lowercase():
    """Test that debug (lowercase) event type maps to logging.DEBUG."""
    assert to_logging_level("debug") == logging.DEBUG


def test_to_logging_level_info():
    """Test that INFO event type maps to logging.INFO."""
    assert to_logging_level("INFO") == logging.INFO


def test_to_logging_level_other():
    """Test that any other event type maps to logging.INFO."""
    assert to_logging_level("START") == logging.INFO
    assert to_logging_level("COMPLETE") == logging.INFO
    assert to_logging_level("ERROR") == logging.INFO
    assert to_logging_level("EXCEPTION") == logging.INFO


# Test emit_event
def test_emit_event_with_default_indent():
    """Test emitting a single event with default indent."""
    mock_logger = Mock(spec=logging.Logger)
    mock_event = Mock()
    mock_event.event_type = "INFO"
    mock_event.as_json.return_value = '{"test": "data"}'

    emit_event(mock_logger, mock_event)

    mock_event.as_json.assert_called_once_with(indent=2)
    mock_logger.log.assert_called_once_with(logging.INFO, '{"test": "data"}')


def test_emit_event_with_custom_indent():
    """Test emitting a single event with custom indent."""
    mock_logger = Mock(spec=logging.Logger)
    mock_event = Mock()
    mock_event.event_type = "START"
    mock_event.as_json.return_value = '{"test": "data"}'

    emit_event(mock_logger, mock_event, indent=4)

    mock_event.as_json.assert_called_once_with(indent=4)
    mock_logger.log.assert_called_once_with(logging.INFO, '{"test": "data"}')


def test_emit_event_debug_level():
    """Test emitting a DEBUG event logs at DEBUG level."""
    mock_logger = Mock(spec=logging.Logger)
    mock_event = Mock()
    mock_event.event_type = "DEBUG"
    mock_event.as_json.return_value = '{"debug": "info"}'

    emit_event(mock_logger, mock_event)

    mock_logger.log.assert_called_once_with(logging.DEBUG, '{"debug": "info"}')


# Test emit_all
def test_emit_all_empty_list():
    """Test emitting an empty list of events."""
    mock_logger = Mock(spec=logging.Logger)
    events = []

    emit_all(mock_logger, events)

    mock_logger.log.assert_not_called()


def test_emit_all_single_event():
    """Test emitting a single event from a list."""
    mock_logger = Mock(spec=logging.Logger)
    mock_event = Mock()
    mock_event.event_type = "INFO"
    mock_event.as_json.return_value = '{"test": "data"}'

    emit_all(mock_logger, [mock_event])

    mock_event.as_json.assert_called_once_with(indent=2)
    mock_logger.log.assert_called_once_with(logging.INFO, '{"test": "data"}')


def test_emit_all_multiple_events():
    """Test emitting multiple events from a list."""
    mock_logger = Mock(spec=logging.Logger)

    mock_event1 = Mock()
    mock_event1.event_type = "START"
    mock_event1.as_json.return_value = '{"event": "start"}'

    mock_event2 = Mock()
    mock_event2.event_type = "DEBUG"
    mock_event2.as_json.return_value = '{"event": "debug"}'

    mock_event3 = Mock()
    mock_event3.event_type = "COMPLETE"
    mock_event3.as_json.return_value = '{"event": "complete"}'

    emit_all(mock_logger, [mock_event1, mock_event2, mock_event3], indent=4)

    assert mock_event1.as_json.call_count == 1
    assert mock_event2.as_json.call_count == 1
    assert mock_event3.as_json.call_count == 1

    assert mock_logger.log.call_count == 3
    mock_logger.log.assert_any_call(logging.INFO, '{"event": "start"}')
    mock_logger.log.assert_any_call(logging.DEBUG, '{"event": "debug"}')
    mock_logger.log.assert_any_call(logging.INFO, '{"event": "complete"}')


# Test configure_emitter
@patch('pychub.package.lifecycle.plan.audit.audit_emitter.logging.getLogger')
@patch('pychub.package.lifecycle.plan.audit.audit_emitter.logging.StreamHandler')
def test_configure_emitter_stdout(mock_stream_handler, mock_get_logger):
    """Test configuring emitter with stdout destination."""
    mock_logger = Mock(spec=logging.Logger)
    mock_get_logger.return_value = mock_logger
    mock_handler = Mock()
    mock_stream_handler.return_value = mock_handler

    with patch('pychub.package.lifecycle.plan.audit.audit_emitter.sys.stdout') as mock_stdout:
        result = configure_emitter(["stdout"])

    mock_get_logger.assert_called_once_with("pychub.audit")
    mock_logger.setLevel.assert_called_once_with(logging.INFO)
    assert mock_logger.propagate is False
    mock_stream_handler.assert_called_once_with(mock_stdout)
    mock_handler.setFormatter.assert_called_once()
    mock_logger.addHandler.assert_called_once_with(mock_handler)
    assert result == mock_logger


@patch('pychub.package.lifecycle.plan.audit.audit_emitter.logging.getLogger')
@patch('pychub.package.lifecycle.plan.audit.audit_emitter.logging.StreamHandler')
def test_configure_emitter_stderr(mock_stream_handler, mock_get_logger):
    """Test configuring emitter with stderr destination."""
    mock_logger = Mock(spec=logging.Logger)
    mock_get_logger.return_value = mock_logger
    mock_handler = Mock()
    mock_stream_handler.return_value = mock_handler

    with patch('pychub.package.lifecycle.plan.audit.audit_emitter.sys.stderr') as mock_stderr:
        result = configure_emitter(["stderr"])

    mock_stream_handler.assert_called_once_with(mock_stderr)
    mock_handler.setFormatter.assert_called_once()
    mock_logger.addHandler.assert_called_once_with(mock_handler)


@patch('pychub.package.lifecycle.plan.audit.audit_emitter.logging.getLogger')
@patch('pychub.package.lifecycle.plan.audit.audit_emitter.logging.FileHandler')
def test_configure_emitter_file(mock_file_handler, mock_get_logger):
    """Test configuring emitter with file destination."""
    mock_logger = Mock(spec=logging.Logger)
    mock_get_logger.return_value = mock_logger
    mock_handler = Mock()
    mock_file_handler.return_value = mock_handler

    result = configure_emitter(["file:/path/to/audit.log"])

    mock_file_handler.assert_called_once_with("/path/to/audit.log")
    mock_handler.setFormatter.assert_called_once()
    mock_logger.addHandler.assert_called_once_with(mock_handler)


@patch('pychub.package.lifecycle.plan.audit.audit_emitter.logging.getLogger')
@patch('pychub.package.lifecycle.plan.audit.audit_emitter.logging.StreamHandler')
@patch('pychub.package.lifecycle.plan.audit.audit_emitter.logging.FileHandler')
def test_configure_emitter_multiple_destinations(mock_file_handler, mock_stream_handler, mock_get_logger):
    """Test configuring emitter with multiple destinations."""
    mock_logger = Mock(spec=logging.Logger)
    mock_get_logger.return_value = mock_logger

    mock_stdout_handler = Mock()
    mock_file_handler_obj = Mock()
    mock_stream_handler.return_value = mock_stdout_handler
    mock_file_handler.return_value = mock_file_handler_obj

    with patch('pychub.package.lifecycle.plan.audit.audit_emitter.sys.stdout') as mock_stdout:
        result = configure_emitter(["stdout", "file:/tmp/test.log"])

    assert mock_stream_handler.call_count == 1
    mock_stream_handler.assert_called_with(mock_stdout)
    mock_file_handler.assert_called_once_with("/tmp/test.log")
    assert mock_logger.addHandler.call_count == 2
    mock_logger.addHandler.assert_any_call(mock_stdout_handler)
    mock_logger.addHandler.assert_any_call(mock_file_handler_obj)


@patch('pychub.package.lifecycle.plan.audit.audit_emitter.logging.getLogger')
def test_configure_emitter_custom_level(mock_get_logger):
    """Test configuring emitter with custom log level."""
    mock_logger = Mock(spec=logging.Logger)
    mock_get_logger.return_value = mock_logger

    with patch('pychub.package.lifecycle.plan.audit.audit_emitter.logging.StreamHandler'):
        with patch('pychub.package.lifecycle.plan.audit.audit_emitter.sys.stdout'):
            result = configure_emitter(["stdout"], level=logging.DEBUG)

    mock_logger.setLevel.assert_called_once_with(logging.DEBUG)


@patch('pychub.package.lifecycle.plan.audit.audit_emitter.logging.getLogger')
def test_configure_emitter_invalid_destination(mock_get_logger):
    """Test configuring emitter with invalid destination raises ValueError."""
    mock_logger = Mock(spec=logging.Logger)
    mock_get_logger.return_value = mock_logger

    with pytest.raises(ValueError, match="Unknown audit log destination: invalid"):
        configure_emitter(["invalid"])


# Test emit_audit_log
@patch('pychub.package.lifecycle.plan.audit.audit_emitter.emit_all')
@patch('pychub.package.lifecycle.plan.audit.audit_emitter.configure_emitter')
def test_emit_audit_log_default_file_destination(mock_configure, mock_emit_all):
    """Test emit_audit_log with default file destination."""
    mock_logger = Mock()
    mock_configure.return_value = mock_logger

    mock_plan = Mock()
    mock_plan.staging_dir = Path("/tmp/staging")
    mock_plan.audit_log = [Mock(), Mock()]

    emit_audit_log(mock_plan)

    mock_configure.assert_called_once_with([f"file:/tmp/staging/{_LOG_FILE_NAME}"])
    mock_emit_all.assert_called_once_with(mock_logger, mock_plan.audit_log, 2)


@patch('pychub.package.lifecycle.plan.audit.audit_emitter.emit_all')
@patch('pychub.package.lifecycle.plan.audit.audit_emitter.configure_emitter')
def test_emit_audit_log_custom_file_path(mock_configure, mock_emit_all):
    """Test emit_audit_log with custom file path."""
    mock_logger = Mock()
    mock_configure.return_value = mock_logger

    mock_plan = Mock()
    mock_plan.staging_dir = Path("/tmp/staging")
    mock_plan.audit_log = [Mock()]

    custom_path = Path("/custom/audit.json")
    emit_audit_log(mock_plan, dest="file", path=custom_path)

    # When path is provided, "file" should be passed as-is (not expanded)
    mock_configure.assert_called_once_with(["file"])
    mock_emit_all.assert_called_once_with(mock_logger, mock_plan.audit_log, 2)


@patch('pychub.package.lifecycle.plan.audit.audit_emitter.emit_all')
@patch('pychub.package.lifecycle.plan.audit.audit_emitter.configure_emitter')
def test_emit_audit_log_stdout_destination(mock_configure, mock_emit_all):
    """Test emit_audit_log with stdout destination."""
    mock_logger = Mock()
    mock_configure.return_value = mock_logger

    mock_plan = Mock()
    mock_plan.staging_dir = Path("/tmp/staging")
    mock_plan.audit_log = [Mock(), Mock(), Mock()]

    emit_audit_log(mock_plan, dest="stdout")

    mock_configure.assert_called_once_with(["stdout"])
    mock_emit_all.assert_called_once_with(mock_logger, mock_plan.audit_log, 2)


@patch('pychub.package.lifecycle.plan.audit.audit_emitter.emit_all')
@patch('pychub.package.lifecycle.plan.audit.audit_emitter.configure_emitter')
def test_emit_audit_log_multiple_destinations(mock_configure, mock_emit_all):
    """Test emit_audit_log with multiple destinations."""
    mock_logger = Mock()
    mock_configure.return_value = mock_logger

    mock_plan = Mock()
    mock_plan.staging_dir = Path("/tmp/staging")
    mock_plan.audit_log = [Mock()]

    emit_audit_log(mock_plan, dest="stdout stderr")

    mock_configure.assert_called_once_with(["stdout", "stderr"])
    mock_emit_all.assert_called_once_with(mock_logger, mock_plan.audit_log, 2)


@patch('pychub.package.lifecycle.plan.audit.audit_emitter.emit_all')
@patch('pychub.package.lifecycle.plan.audit.audit_emitter.configure_emitter')
def test_emit_audit_log_mixed_destinations_with_file(mock_configure, mock_emit_all):
    """Test emit_audit_log with mixed destinations including file."""
    mock_logger = Mock()
    mock_configure.return_value = mock_logger

    mock_plan = Mock()
    mock_plan.staging_dir = Path("/cache/build")
    mock_plan.audit_log = [Mock(), Mock()]

    emit_audit_log(mock_plan, dest="stdout file stderr")

    expected_dests = ["stdout", f"file:/cache/build/{_LOG_FILE_NAME}", "stderr"]
    mock_configure.assert_called_once_with(expected_dests)
    mock_emit_all.assert_called_once_with(mock_logger, mock_plan.audit_log, 2)


@patch('pychub.package.lifecycle.plan.audit.audit_emitter.emit_all')
@patch('pychub.package.lifecycle.plan.audit.audit_emitter.configure_emitter')
def test_emit_audit_log_custom_indent(mock_configure, mock_emit_all):
    """Test emit_audit_log with custom indent."""
    mock_logger = Mock()
    mock_configure.return_value = mock_logger

    mock_plan = Mock()
    mock_plan.staging_dir = Path("/tmp/staging")
    mock_plan.audit_log = [Mock()]

    emit_audit_log(mock_plan, dest="stdout", indent=4)

    mock_configure.assert_called_once_with(["stdout"])
    mock_emit_all.assert_called_once_with(mock_logger, mock_plan.audit_log, 4)


@patch('pychub.package.lifecycle.plan.audit.audit_emitter.emit_all')
@patch('pychub.package.lifecycle.plan.audit.audit_emitter.configure_emitter')
def test_emit_audit_log_empty_audit_log(mock_configure, mock_emit_all):
    """Test emit_audit_log with empty audit log."""
    mock_logger = Mock()
    mock_configure.return_value = mock_logger

    mock_plan = Mock()
    mock_plan.staging_dir = Path("/tmp/staging")
    mock_plan.audit_log = []

    emit_audit_log(mock_plan, dest="stdout")

    mock_configure.assert_called_once_with(["stdout"])
    mock_emit_all.assert_called_once_with(mock_logger, [], 2)