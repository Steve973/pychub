"""Unit tests for pychub.package.main module."""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from pychub.model.buildplan_model import BuildPlan
from pychub.package import context_vars
from pychub.package.main import main, run


# ===========================
# run() tests
# ===========================

def test_run_creates_build_plan_and_sets_context():
    """Test that run() creates a BuildPlan and sets it in the context."""
    captured_build_plan = None

    def capture_from_context(*args, **kwargs):
        nonlocal captured_build_plan
        captured_build_plan = context_vars.current_build_plan.get()
        return Path("/tmp/cache"), False

    with patch("pychub.package.main.get_version", return_value="1.0.0"), \
            patch("pychub.package.main.init_project", side_effect=capture_from_context), \
            patch("pychub.package.main.plan_build"), \
            patch("pychub.package.main.execute_build", return_value=Path("/tmp/test.chub")), \
            patch("pychub.package.main.emit_audit_log"):
        run()

        assert captured_build_plan is not None
        assert isinstance(captured_build_plan, BuildPlan)


def test_run_sets_pychub_version_in_build_plan():
    """Test that run() sets the pychub version in the build plan."""
    expected_version = "2.5.3"
    captured_build_plan = None

    def capture_from_context(*args, **kwargs):
        nonlocal captured_build_plan
        captured_build_plan = context_vars.current_build_plan.get()
        return Path("/tmp/cache"), False

    with patch("pychub.package.main.get_version", return_value=expected_version), \
            patch("pychub.package.main.init_project", side_effect=capture_from_context), \
            patch("pychub.package.main.plan_build"), \
            patch("pychub.package.main.execute_build", return_value=Path("/tmp/test.chub")), \
            patch("pychub.package.main.emit_audit_log"):
        run()

        assert captured_build_plan is not None
        assert captured_build_plan.pychub_version == expected_version


def test_run_executes_full_lifecycle_with_chubproject_path(tmp_path):
    """Test that run() executes the complete lifecycle with a chubproject path."""
    chubproject_path = tmp_path / "chubproject.toml"
    chubproject_path.write_text("[tool.pychub.package]\nname = 'test'\n", encoding="utf-8")
    mock_cache_path = tmp_path / "cache"
    mock_chub_path = tmp_path / "test.chub"

    with patch("pychub.package.main.get_version", return_value="1.0.0") as mock_version, \
            patch("pychub.package.main.init_project", return_value=(mock_cache_path, False)) as mock_init, \
            patch("pychub.package.main.plan_build") as mock_plan, \
            patch("pychub.package.main.execute_build", return_value=mock_chub_path) as mock_execute, \
            patch("pychub.package.main.emit_audit_log") as mock_emit:
        run(chubproject_path=chubproject_path)

        # Verify version was retrieved
        mock_version.assert_called_once_with("pychub")

        # Verify init was called with the path
        mock_init.assert_called_once_with(chubproject_path)

        # Verify plan was called with cache_path and strategies
        mock_plan.assert_called_once()
        assert mock_plan.call_args[0][0] == mock_cache_path
        assert len(mock_plan.call_args[0][1]) == 2  # Two strategies

        # Verify execute_build was called
        mock_execute.assert_called_once()

        # Verify audit log was emitted
        mock_emit.assert_called_once()


def test_run_executes_full_lifecycle_without_chubproject_path():
    """Test that run() executes the complete lifecycle without a chubproject path (CLI mode)."""
    mock_cache_path = Path("/tmp/cache")
    mock_chub_path = Path("/tmp/test.chub")

    with patch("pychub.package.main.get_version", return_value="1.0.0"), \
            patch("pychub.package.main.init_project", return_value=(mock_cache_path, False)) as mock_init, \
            patch("pychub.package.main.plan_build") as mock_plan, \
            patch("pychub.package.main.execute_build", return_value=mock_chub_path) as mock_execute, \
            patch("pychub.package.main.emit_audit_log") as mock_emit:
        run(chubproject_path=None)

        # Verify init was called with None
        mock_init.assert_called_once_with(None)

        # Verify all lifecycle stages were called
        mock_plan.assert_called_once()
        mock_execute.assert_called_once()
        mock_emit.assert_called_once()


def test_run_adds_start_audit_event():
    """Test that run() adds a START audit event."""
    captured_build_plan = None

    def capture_from_context(*args, **kwargs):
        nonlocal captured_build_plan
        captured_build_plan = context_vars.current_build_plan.get()
        return Path("/tmp/cache"), False

    with patch("pychub.package.main.get_version", return_value="1.0.0"), \
            patch("pychub.package.main.init_project", side_effect=capture_from_context), \
            patch("pychub.package.main.plan_build"), \
            patch("pychub.package.main.execute_build", return_value=Path("/tmp/test.chub")), \
            patch("pychub.package.main.emit_audit_log"):
        run()

        assert captured_build_plan is not None
        start_events = [e for e in captured_build_plan.audit_log
                        if e.stage == "LIFECYCLE" and e.event_type == "START"]
        assert len(start_events) == 1
        assert "Starting pychub build" in start_events[0].message


def test_run_adds_input_audit_event_with_chubproject_path(tmp_path):
    """Test that run() adds an INPUT audit event when chubproject_path is provided."""
    chubproject_path = tmp_path / "chubproject.toml"
    captured_build_plan = None

    def capture_from_context(*args, **kwargs):
        nonlocal captured_build_plan
        captured_build_plan = context_vars.current_build_plan.get()
        return Path("/tmp/cache"), False

    with patch("pychub.package.main.get_version", return_value="1.0.0"), \
            patch("pychub.package.main.init_project", side_effect=capture_from_context), \
            patch("pychub.package.main.plan_build"), \
            patch("pychub.package.main.execute_build", return_value=Path("/tmp/test.chub")), \
            patch("pychub.package.main.emit_audit_log"):
        run(chubproject_path=chubproject_path)

        assert captured_build_plan is not None
        input_events = [e for e in captured_build_plan.audit_log
                        if e.stage == "LIFECYCLE" and e.event_type == "INPUT"]
        assert len(input_events) == 1
        assert "Build invoked with chubproject path" in input_events[0].message
        assert str(chubproject_path) in input_events[0].message


def test_run_adds_input_audit_event_without_chubproject_path():
    """Test that run() adds an INPUT audit event when no chubproject_path is provided."""
    captured_build_plan = None

    def capture_from_context(*args, **kwargs):
        nonlocal captured_build_plan
        captured_build_plan = context_vars.current_build_plan.get()
        return Path("/tmp/cache"), False

    with patch("pychub.package.main.get_version", return_value="1.0.0"), \
            patch("pychub.package.main.init_project", side_effect=capture_from_context), \
            patch("pychub.package.main.plan_build"), \
            patch("pychub.package.main.execute_build", return_value=Path("/tmp/test.chub")), \
            patch("pychub.package.main.emit_audit_log"):
        run()

        assert captured_build_plan is not None
        input_events = [e for e in captured_build_plan.audit_log
                        if e.stage == "LIFECYCLE" and e.event_type == "INPUT"]
        assert len(input_events) == 1
        assert "Build will use CLI options" in input_events[0].message


def test_run_sets_project_dir_when_chubproject_path_provided(tmp_path):
    """Test that run() sets the project_dir in build_plan when chubproject_path is provided."""
    chubproject_path = tmp_path / "subdir" / "chubproject.toml"
    chubproject_path.parent.mkdir(parents=True, exist_ok=True)
    captured_build_plan = None

    def capture_from_context(*args, **kwargs):
        nonlocal captured_build_plan
        captured_build_plan = context_vars.current_build_plan.get()
        return Path("/tmp/cache"), False

    with patch("pychub.package.main.get_version", return_value="1.0.0"), \
            patch("pychub.package.main.init_project", side_effect=capture_from_context), \
            patch("pychub.package.main.plan_build"), \
            patch("pychub.package.main.execute_build", return_value=Path("/tmp/test.chub")), \
            patch("pychub.package.main.emit_audit_log"):
        run(chubproject_path=chubproject_path)

        assert captured_build_plan is not None
        assert captured_build_plan.project_dir == chubproject_path.parent.resolve()


def test_run_adds_complete_audit_event_on_success():
    """Test that run() adds a COMPLETE audit event when successful."""
    captured_build_plan = None

    def capture_from_context(*args, **kwargs):
        nonlocal captured_build_plan
        captured_build_plan = context_vars.current_build_plan.get()
        return Path("/tmp/cache"), False

    with patch("pychub.package.main.get_version", return_value="1.0.0"), \
            patch("pychub.package.main.init_project", side_effect=capture_from_context), \
            patch("pychub.package.main.plan_build"), \
            patch("pychub.package.main.execute_build", return_value=Path("/tmp/test.chub")), \
            patch("pychub.package.main.emit_audit_log"):
        run()

        assert captured_build_plan is not None
        complete_events = [e for e in captured_build_plan.audit_log
                           if e.stage == "LIFECYCLE" and e.event_type == "COMPLETE"]
        assert len(complete_events) == 1
        assert "Completed pychub build" in complete_events[0].message


def test_run_adds_output_audit_event_with_chub_path():
    """Test that run() adds an OUTPUT audit event with the chub file path."""
    mock_chub_path = Path("/tmp/output/test.chub")
    captured_build_plan = None

    def capture_from_context(*args, **kwargs):
        nonlocal captured_build_plan
        captured_build_plan = context_vars.current_build_plan.get()
        return Path("/tmp/cache"), False

    with patch("pychub.package.main.get_version", return_value="1.0.0"), \
            patch("pychub.package.main.init_project", side_effect=capture_from_context), \
            patch("pychub.package.main.plan_build"), \
            patch("pychub.package.main.execute_build", return_value=mock_chub_path), \
            patch("pychub.package.main.emit_audit_log"):
        run()

        assert captured_build_plan is not None
        output_events = [e for e in captured_build_plan.audit_log
                         if e.stage == "LIFECYCLE" and e.event_type == "OUTPUT"]
        assert len(output_events) == 1
        assert "Chub file built and located at" in output_events[0].message
        assert str(mock_chub_path) in output_events[0].message


def test_run_skips_build_when_must_exit_is_true():
    """Test that run() skips plan and build phases when must_exit is True."""
    captured_build_plan = None

    def capture_from_context(*args, **kwargs):
        nonlocal captured_build_plan
        captured_build_plan = context_vars.current_build_plan.get()
        return Path("/tmp/cache"), True  # must_exit = True

    with patch("pychub.package.main.get_version", return_value="1.0.0"), \
            patch("pychub.package.main.init_project", side_effect=capture_from_context), \
            patch("pychub.package.main.plan_build") as mock_plan, \
            patch("pychub.package.main.execute_build") as mock_execute, \
            patch("pychub.package.main.emit_audit_log"):
        run()

        # Verify plan and execute were NOT called
        mock_plan.assert_not_called()
        mock_execute.assert_not_called()

        # Verify an ACTION audit event was added
        assert captured_build_plan is not None
        action_events = [e for e in captured_build_plan.audit_log
                         if e.stage == "LIFECYCLE" and e.event_type == "ACTION"]
        assert len(action_events) == 1
        assert "Completed immediate operation and exiting" in action_events[0].message


def test_run_adds_fail_audit_event_on_exception():
    """Test that run() adds a FAIL audit event when an exception occurs."""
    error_message = "Test error during init"
    captured_build_plan = None

    def capture_and_fail(*args, **kwargs):
        nonlocal captured_build_plan
        captured_build_plan = context_vars.current_build_plan.get()
        raise RuntimeError(error_message)

    with patch("pychub.package.main.get_version", return_value="1.0.0"), \
            patch("pychub.package.main.init_project", side_effect=capture_and_fail), \
            patch("pychub.package.main.emit_audit_log"):
        with pytest.raises(RuntimeError, match=error_message):
            run()

        assert captured_build_plan is not None
        fail_events = [e for e in captured_build_plan.audit_log
                       if e.stage == "LIFECYCLE" and e.event_type == "FAIL"]
        assert len(fail_events) == 1
        assert error_message in fail_events[0].message


def test_run_emits_audit_log_on_exception():
    """Test that run() emits audit log even when an exception occurs."""
    with patch("pychub.package.main.get_version", return_value="1.0.0"), \
            patch("pychub.package.main.init_project", side_effect=RuntimeError("Test error")), \
            patch("pychub.package.main.emit_audit_log") as mock_emit:
        with pytest.raises(RuntimeError):
            run()

        # Audit log should still be emitted
        mock_emit.assert_called_once()


def test_run_raises_exception_after_handling():
    """Test that run() re-raises exceptions after handling them."""
    expected_error = RuntimeError("Test error")

    with patch("pychub.package.main.get_version", return_value="1.0.0"), \
            patch("pychub.package.main.init_project", side_effect=expected_error), \
            patch("pychub.package.main.emit_audit_log"):
        with pytest.raises(RuntimeError, match="Test error"):
            run()


def test_run_exception_during_plan_build():
    """Test that run() handles exceptions during plan_build phase."""
    mock_cache_path = Path("/tmp/cache")
    error_message = "Planning failed"

    with patch("pychub.package.main.get_version", return_value="1.0.0"), \
            patch("pychub.package.main.init_project", return_value=(mock_cache_path, False)), \
            patch("pychub.package.main.plan_build", side_effect=RuntimeError(error_message)), \
            patch("pychub.package.main.emit_audit_log") as mock_emit:
        with pytest.raises(RuntimeError, match=error_message):
            run()

        mock_emit.assert_called_once()


def test_run_exception_during_execute_build():
    """Test that run() handles exceptions during execute_build phase."""
    mock_cache_path = Path("/tmp/cache")
    error_message = "Build execution failed"

    with patch("pychub.package.main.get_version", return_value="1.0.0"), \
            patch("pychub.package.main.init_project", return_value=(mock_cache_path, False)), \
            patch("pychub.package.main.plan_build"), \
            patch("pychub.package.main.execute_build", side_effect=RuntimeError(error_message)), \
            patch("pychub.package.main.emit_audit_log") as mock_emit:
        with pytest.raises(RuntimeError, match=error_message):
            run()

        mock_emit.assert_called_once()


def test_run_calls_stages_in_correct_order():
    """Test that run() calls lifecycle stages in the correct order."""
    mock_cache_path = Path("/tmp/cache")
    mock_chub_path = Path("/tmp/test.chub")
    call_order = []

    def track_init(*args, **kwargs):
        call_order.append("init")
        return mock_cache_path, False

    def track_plan(*args, **kwargs):
        call_order.append("plan")

    def track_execute(*args, **kwargs):
        call_order.append("execute")
        return mock_chub_path

    def track_emit(*args, **kwargs):
        call_order.append("emit")

    with patch("pychub.package.main.get_version", return_value="1.0.0"), \
            patch("pychub.package.main.init_project", side_effect=track_init), \
            patch("pychub.package.main.plan_build", side_effect=track_plan), \
            patch("pychub.package.main.execute_build", side_effect=track_execute), \
            patch("pychub.package.main.emit_audit_log", side_effect=track_emit):
        run()

        assert call_order == ["init", "plan", "execute", "emit"]


def test_run_expands_and_resolves_chubproject_path(tmp_path):
    """Test that run() properly expands and resolves the chubproject path."""
    # Create a path with a parent directory
    chubproject_path = tmp_path / "project" / "chubproject.toml"
    chubproject_path.parent.mkdir(parents=True, exist_ok=True)
    chubproject_path.write_text("")

    captured_build_plan = None

    def capture_from_context(*args, **kwargs):
        nonlocal captured_build_plan
        captured_build_plan = context_vars.current_build_plan.get()
        return Path("/tmp/cache"), False

    with patch("pychub.package.main.get_version", return_value="1.0.0"), \
            patch("pychub.package.main.init_project", side_effect=capture_from_context), \
            patch("pychub.package.main.plan_build"), \
            patch("pychub.package.main.execute_build", return_value=Path("/tmp/test.chub")), \
            patch("pychub.package.main.emit_audit_log"):
        run(chubproject_path=chubproject_path)

        assert captured_build_plan is not None
        # The project_dir should be the parent directory, resolved
        expected_path = chubproject_path.expanduser().resolve().parent
        assert captured_build_plan.project_dir == expected_path


def test_run_passes_strategies_to_plan_build():
    """Test that run() passes the correct resolution strategies to plan_build."""
    mock_cache_path = Path("/tmp/cache")

    with patch("pychub.package.main.get_version", return_value="1.0.0"), \
            patch("pychub.package.main.init_project", return_value=(mock_cache_path, False)), \
            patch("pychub.package.main.plan_build") as mock_plan, \
            patch("pychub.package.main.execute_build", return_value=Path("/tmp/test.chub")), \
            patch("pychub.package.main.emit_audit_log"):
        run()

        # Verify plan_build was called with cache_path and a list of strategies
        mock_plan.assert_called_once()
        args = mock_plan.call_args[0]
        assert args[0] == mock_cache_path
        assert len(args[1]) == 2  # IndexResolutionStrategy and PathResolutionStrategy
        # Verify the strategy types
        from pychub.package.lifecycle.plan.dep_resolution.wheeldeps.index_resolution_strategy import IndexResolutionStrategy
        from pychub.package.lifecycle.plan.dep_resolution.wheeldeps.path_resolution_strategy import PathResolutionStrategy
        assert isinstance(args[1][0], IndexResolutionStrategy)
        assert isinstance(args[1][1], PathResolutionStrategy)


# ===========================
# main() tests
# ===========================

def test_main_calls_run_successfully():
    """Test that main() calls run() successfully."""
    with patch("pychub.package.main.run") as mock_run:
        main()
        mock_run.assert_called_once_with()


def test_main_exits_with_1_on_keyboard_interrupt():
    """Test that main() exits with code 1 on KeyboardInterrupt."""
    with patch("pychub.package.main.run", side_effect=KeyboardInterrupt), \
            patch("sys.exit") as mock_exit:
        main()
        mock_exit.assert_called_once_with(1)


def test_main_exits_with_1_on_exception():
    """Test that main() exits with code 1 on exception."""
    with patch("pychub.package.main.run", side_effect=RuntimeError("Test error")), \
            patch("sys.exit") as mock_exit, \
            patch("builtins.print"):
        main()
        mock_exit.assert_called_once_with(1)


def test_main_prints_error_message_on_exception():
    """Test that main() prints error message to stderr on exception."""
    error_message = "Test error message"

    with patch("pychub.package.main.run", side_effect=RuntimeError(error_message)), \
            patch("sys.exit"), \
            patch("builtins.print") as mock_print:
        main()

        # Check that print was called with error message and file=sys.stderr
        mock_print.assert_called_once()
        call_args = mock_print.call_args
        assert error_message in str(call_args[0][0])
        assert call_args[1]["file"] == sys.stderr


def test_main_does_not_exit_on_success():
    """Test that main() does not call sys.exit on success."""
    with patch("pychub.package.main.run"), \
            patch("sys.exit") as mock_exit:
        main()
        mock_exit.assert_not_called()


def test_main_handles_different_exception_types():
    """Test that main() handles different exception types."""
    exceptions = [
        RuntimeError("Runtime error"),
        ValueError("Value error"),
        FileNotFoundError("File not found"),
        ImportError("Import error"),
    ]

    for exc in exceptions:
        with patch("pychub.package.main.run", side_effect=exc), \
                patch("sys.exit") as mock_exit, \
                patch("builtins.print"):
            main()
            mock_exit.assert_called_once_with(1)


@pytest.mark.parametrize("exception_class,message", [
    (RuntimeError, "Runtime error occurred"),
    (ValueError, "Invalid value provided"),
    (FileNotFoundError, "File missing"),
    (OSError, "OS operation failed"),
    (ImportError, "Cannot import module"),
])
def test_main_parametrized_exceptions(exception_class, message):
    """Parametrized test for main() handling different exceptions."""
    with patch("pychub.package.main.run", side_effect=exception_class(message)), \
            patch("sys.exit") as mock_exit, \
            patch("builtins.print") as mock_print:
        main()

        mock_exit.assert_called_once_with(1)
        assert mock_print.called
        printed_text = str(mock_print.call_args[0][0])
        assert message in printed_text
        assert "pychub: error:" in printed_text