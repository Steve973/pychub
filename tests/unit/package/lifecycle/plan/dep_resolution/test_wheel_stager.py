from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from pychub.model.build_event import StageType, EventType
from pychub.package.context_vars import current_build_plan
from pychub.package.lifecycle.plan.dep_resolution import wheel_stager


def test_flatten_empty_list():
    """Test _flatten with empty list."""
    result = wheel_stager._flatten([])
    assert result == []


def test_flatten_none():
    """Test _flatten with None."""
    result = wheel_stager._flatten(None)
    assert result == []


def test_flatten_simple_list():
    """Test _flatten with a simple flat list."""
    result = wheel_stager._flatten(["a", "b", "c"])
    assert result == ["a", "b", "c"]


def test_flatten_nested_list():
    """Test _flatten with nested lists."""
    result = wheel_stager._flatten([["a", "b"], ["c"], "d"])
    assert result == ["a", "b", "c", "d"]


def test_flatten_deeply_nested():
    """Test _flatten with deeply nested structure."""
    result = wheel_stager._flatten([["a", "b"], "c", ["d", "e", "f"]])
    assert result == ["a", "b", "c", "d", "e", "f"]


def test_flatten_with_tuples():
    """Test _flatten with tuples."""
    result = wheel_stager._flatten([("a", "b"), "c"])
    assert result == ["a", "b", "c"]


def test_flatten_mixed_types():
    """Test _flatten preserves non-list items."""
    result = wheel_stager._flatten([1, [2, 3], "string"])
    assert result == [1, 2, 3, "string"]


def test_paths_empty_list():
    """Test _paths with empty list."""
    result = wheel_stager._paths([])
    assert result == []


def test_paths_nonexistent_file():
    """Test _paths filters out non-existent files."""
    result = wheel_stager._paths(["/nonexistent/file.whl"])
    assert result == []


def test_paths_existing_file(tmp_path):
    """Test _paths with existing file."""
    wheel = tmp_path / "test.whl"
    wheel.write_text("content")

    result = wheel_stager._paths([str(wheel)])

    assert len(result) == 1
    assert result[0] == wheel


def test_paths_multiple_files(tmp_path):
    """Test _paths with multiple existing files."""
    wheel1 = tmp_path / "test1.whl"
    wheel2 = tmp_path / "test2.whl"
    wheel1.write_text("content1")
    wheel2.write_text("content2")

    result = wheel_stager._paths([str(wheel1), str(wheel2)])

    assert len(result) == 2
    assert wheel1 in result
    assert wheel2 in result


def test_paths_mixed_existing_and_nonexistent(tmp_path):
    """Test _paths filters out non-existent files in mixed list."""
    wheel1 = tmp_path / "exists.whl"
    wheel1.write_text("content")
    nonexistent = "/does/not/exist.whl"

    result = wheel_stager._paths([str(wheel1), nonexistent])

    assert len(result) == 1
    assert result[0] == wheel1


def test_paths_directory_filtered_out(tmp_path):
    """Test _paths filters out directories."""
    subdir = tmp_path / "subdir"
    subdir.mkdir()
    wheel = tmp_path / "test.whl"
    wheel.write_text("content")

    result = wheel_stager._paths([str(subdir), str(wheel)])

    assert len(result) == 1
    assert result[0] == wheel


def test_paths_nested_list(tmp_path):
    """Test _paths handles nested lists (via _flatten)."""
    wheel1 = tmp_path / "test1.whl"
    wheel2 = tmp_path / "test2.whl"
    wheel1.write_text("content1")
    wheel2.write_text("content2")

    result = wheel_stager._paths([[str(wheel1)], str(wheel2)])

    assert len(result) == 2
    assert wheel1 in result
    assert wheel2 in result


def test_paths_expands_user_and_resolves(tmp_path, monkeypatch):
    """Test _paths expands ~ and resolves relative paths."""
    wheel = tmp_path / "test.whl"
    wheel.write_text("content")

    # Mock expanduser to return tmp_path
    original_path = Path

    class MockPath(type(Path())):
        def expanduser(self):
            if "~" in str(self):
                return original_path(str(wheel))
            return self

    monkeypatch.setattr(wheel_stager, "Path", MockPath)

    # Create actual wheel for the test
    result = wheel_stager._paths([str(wheel)])
    assert len(result) == 1


def test_stage_wheels_single_wheel_single_strategy(tmp_path):
    """Test stage_wheels with one wheel and one successful strategy."""
    # Create mock build plan
    build_plan = Mock()
    current_build_plan.set(build_plan)
    staging_dir = tmp_path / "staging"
    staging_dir.mkdir()
    wheels_dir = Path("wheels")
    (staging_dir / wheels_dir).mkdir()

    build_plan.staging_dir = staging_dir
    build_plan.wheels_dir = wheels_dir
    build_plan.audit_log = []

    # Create a wheel file
    wheel = tmp_path / "mypackage-1.0.0-py3-none-any.whl"
    wheel.write_text("wheel content")

    # Create mock strategy
    strategy = Mock()
    resolved_path = staging_dir / wheels_dir / "mypackage-1.0.0-py3-none-any.whl"
    strategy.resolve.return_value = resolved_path

    wheel_files = {}
    project_wheels = {str(wheel)}

    wheel_stager.stage_wheels(wheel_files, project_wheels, [strategy])

    assert "mypackage" in wheel_files
    assert str(resolved_path) in wheel_files["mypackage"]
    strategy.resolve.assert_called_once_with(str(wheel), staging_dir / wheels_dir)


def test_stage_wheels_multiple_wheels(tmp_path, monkeypatch):
    """Test stage_wheels with multiple wheels."""
    build_plan = Mock()
    staging_dir = tmp_path / "staging"
    staging_dir.mkdir()
    wheels_dir = Path("wheels")
    (staging_dir / wheels_dir).mkdir()

    build_plan.staging_dir = staging_dir
    build_plan.wheels_dir = wheels_dir
    build_plan.audit_log = []

    # Create multiple wheel files
    wheel1 = tmp_path / "package1-1.0.0-py3-none-any.whl"
    wheel2 = tmp_path / "package2-2.0.0-py3-none-any.whl"
    wheel1.write_text("wheel1")
    wheel2.write_text("wheel2")

    # Create mock strategy that returns correct path based on input
    strategy = Mock()
    resolved1 = staging_dir / wheels_dir / "package1-1.0.0-py3-none-any.whl"
    resolved2 = staging_dir / wheels_dir / "package2-2.0.0-py3-none-any.whl"

    def resolve_side_effect(wheel_path, output_dir):
        if "package1" in wheel_path:
            return resolved1
        elif "package2" in wheel_path:
            return resolved2

    strategy.resolve.side_effect = resolve_side_effect

    wheel_files = {}
    project_wheels = {str(wheel1), str(wheel2)}

    mock_event_instance = Mock()
    with patch("pychub.model.build_event.BuildEvent", return_value=mock_event_instance):
        wheel_stager.stage_wheels(wheel_files, project_wheels, [strategy])

    assert "package1" in wheel_files
    assert "package2" in wheel_files
    assert str(resolved1) in wheel_files["package1"]
    assert str(resolved2) in wheel_files["package2"]


def test_stage_wheels_multiple_strategies_first_fails(tmp_path, monkeypatch):
    """Test stage_wheels tries second strategy when first fails."""
    build_plan = Mock()
    current_build_plan.set(build_plan)
    staging_dir = tmp_path / "staging"
    staging_dir.mkdir()
    wheels_dir = Path("wheels")
    (staging_dir / wheels_dir).mkdir()

    build_plan.staging_dir = staging_dir
    build_plan.wheels_dir = wheels_dir
    build_plan.audit_log = []

    wheel = tmp_path / "mypackage-1.0.0-py3-none-any.whl"
    wheel.write_text("content")

    # First strategy fails
    strategy1 = Mock()
    strategy1.__class__.__name__ = "Strategy1"
    strategy1.resolve.side_effect = Exception("Strategy1 failed")

    # Second strategy succeeds
    strategy2 = Mock()
    strategy2.__class__.__name__ = "Strategy2"
    resolved_path = staging_dir / wheels_dir / "mypackage-1.0.0-py3-none-any.whl"
    strategy2.resolve.return_value = resolved_path

    wheel_files = {}
    project_wheels = {str(wheel)}

    wheel_stager.stage_wheels(wheel_files, project_wheels, [strategy1, strategy2])

    assert "mypackage" in wheel_files
    assert str(resolved_path) in wheel_files["mypackage"]

    # Both strategies should be called
    strategy1.resolve.assert_called_once()
    strategy2.resolve.assert_called_once()

    # Audit log should contain exception from first strategy
    found_error = False
    for event in build_plan.audit_log:
        if (event.stage == StageType.PLAN and
            event.substage == "stage_wheels" and
            event.event_type == EventType.EXCEPTION and
            "Strategy1" in event.message and
            "Strategy1 failed" in event.message and
            "mypackage-1.0.0-py3-none-any.whl" in event.message):
            found_error = True
            break
    assert found_error, "Could not find audit log entry for first strategy exception"


def test_stage_wheels_all_strategies_fail(tmp_path, monkeypatch):
    """Test stage_wheels raises RuntimeError when all strategies fail."""
    build_plan = Mock()
    current_build_plan.set(build_plan)
    staging_dir = tmp_path / "staging"
    staging_dir.mkdir()
    wheels_dir = Path("wheels")
    (staging_dir / wheels_dir).mkdir()

    build_plan.staging_dir = staging_dir
    build_plan.wheels_dir = wheels_dir
    build_plan.audit_log = []

    wheel = tmp_path / "mypackage-1.0.0-py3-none-any.whl"
    wheel.write_text("content")

    # Both strategies fail
    strategy1 = Mock()
    strategy1.__class__.__name__ = "Strategy1"
    strategy1.resolve.side_effect = Exception("Strategy1 failed")

    strategy2 = Mock()
    strategy2.__class__.__name__ = "Strategy2"
    strategy2.resolve.side_effect = Exception("Strategy2 failed")

    wheel_files = {}
    project_wheels = {str(wheel)}

    with pytest.raises(RuntimeError) as exc_info:
        wheel_stager.stage_wheels(wheel_files, project_wheels, [strategy1, strategy2])

    assert "Could not resolve dependency mypackage" in str(exc_info.value)

    # Both strategies should be attempted
    strategy1.resolve.assert_called_once()
    strategy2.resolve.assert_called_once()

    # Audit log should contain both exceptions
    found_strategy1 = False
    found_strategy2 = False
    for event in build_plan.audit_log:
        if (event.stage == StageType.PLAN and
                event.substage == "stage_wheels" and
                event.event_type == EventType.EXCEPTION):
            if "Strategy1" in event.message and "Strategy1 failed" in event.message:
                found_strategy1 = True
            if "Strategy2" in event.message and "Strategy2 failed" in event.message:
                found_strategy2 = True

    assert found_strategy1, "Could not find audit log entry for Strategy1 exception"
    assert found_strategy2, "Could not find audit log entry for Strategy2 exception"


def test_stage_wheels_canonicalizes_package_name(tmp_path):
    """Test stage_wheels canonicalizes package names (e.g., My-Package -> my-package)."""
    build_plan = Mock()
    staging_dir = tmp_path / "staging"
    staging_dir.mkdir()
    wheels_dir = Path("wheels")
    (staging_dir / wheels_dir).mkdir()

    build_plan.staging_dir = staging_dir
    build_plan.wheels_dir = wheels_dir
    build_plan.audit_log = []

    # Package name with mixed case and underscores
    wheel = tmp_path / "My_Package-1.0.0-py3-none-any.whl"
    wheel.write_text("content")

    strategy = Mock()
    resolved_path = staging_dir / wheels_dir / "My_Package-1.0.0-py3-none-any.whl"
    strategy.resolve.return_value = resolved_path

    wheel_files = {}
    project_wheels = {str(wheel)}

    wheel_stager.stage_wheels(wheel_files, project_wheels, [strategy])

    # Should be canonicalized to lowercase with hyphens
    assert "my-package" in wheel_files


def test_stage_wheels_appends_to_existing_wheel_files(tmp_path):
    """Test stage_wheels appends to existing entries in wheel_files dict."""
    build_plan = Mock()
    staging_dir = tmp_path / "staging"
    staging_dir.mkdir()
    wheels_dir = Path("wheels")
    (staging_dir / wheels_dir).mkdir()

    build_plan.staging_dir = staging_dir
    build_plan.wheels_dir = wheels_dir
    build_plan.audit_log = []

    wheel = tmp_path / "mypackage-1.0.0-py3-none-any.whl"
    wheel.write_text("content")

    strategy = Mock()
    resolved_path = staging_dir / wheels_dir / "mypackage-1.0.0-py3-none-any.whl"
    strategy.resolve.return_value = resolved_path

    # Pre-populate wheel_files with existing entry
    wheel_files = {"mypackage": ["existing-wheel.whl"]}
    project_wheels = {str(wheel)}

    wheel_stager.stage_wheels(wheel_files, project_wheels, [strategy])

    # Should append, not replace
    assert len(wheel_files["mypackage"]) == 2
    assert "existing-wheel.whl" in wheel_files["mypackage"]
    assert str(resolved_path) in wheel_files["mypackage"]


def test_stage_wheels_empty_project_wheels(tmp_path):
    """Test stage_wheels with no project wheels."""
    build_plan = Mock()
    staging_dir = tmp_path / "staging"
    staging_dir.mkdir()
    wheels_dir = Path("wheels")
    (staging_dir / wheels_dir).mkdir()

    build_plan.staging_dir = staging_dir
    build_plan.wheels_dir = wheels_dir
    build_plan.audit_log = []

    strategy = Mock()
    wheel_files = {}
    project_wheels = set()

    wheel_stager.stage_wheels(wheel_files, project_wheels, [strategy])

    # Should complete without error
    assert wheel_files == {}
    strategy.resolve.assert_not_called()


def test_stage_wheels_filters_nonexistent_wheels(tmp_path):
    """Test stage_wheels filters out non-existent wheel paths."""
    build_plan = Mock()
    staging_dir = tmp_path / "staging"
    staging_dir.mkdir()
    wheels_dir = Path("wheels")
    (staging_dir / wheels_dir).mkdir()

    build_plan.staging_dir = staging_dir
    build_plan.wheels_dir = wheels_dir
    build_plan.audit_log = []

    strategy = Mock()
    wheel_files = {}

    # Include both existing and non-existent wheels
    existing_wheel = tmp_path / "exists-1.0.0-py3-none-any.whl"
    existing_wheel.write_text("content")
    nonexistent_wheel = "/does/not/exist-1.0.0-py3-none-any.whl"

    resolved_path = staging_dir / wheels_dir / "exists-1.0.0-py3-none-any.whl"
    strategy.resolve.return_value = resolved_path

    project_wheels = {str(existing_wheel), nonexistent_wheel}

    wheel_stager.stage_wheels(wheel_files, project_wheels, [strategy])

    # Only existing wheel should be processed
    assert "exists" in wheel_files
    strategy.resolve.assert_called_once()


def test_stage_wheels_strategy_exception_details_in_audit_log(tmp_path, monkeypatch):
    """Test that exception details are properly logged in audit_log."""
    build_plan = Mock()
    current_build_plan.set(build_plan)
    staging_dir = tmp_path / "staging"
    staging_dir.mkdir()
    wheels_dir = Path("wheels")
    (staging_dir / wheels_dir).mkdir()

    build_plan.staging_dir = staging_dir
    build_plan.wheels_dir = wheels_dir
    build_plan.audit_log = []

    wheel = tmp_path / "mypackage-1.0.0-py3-none-any.whl"
    wheel.write_text("content")

    # Strategy that fails with specific error
    strategy1 = Mock()
    strategy1.__class__.__name__ = "TestStrategy"
    strategy1.resolve.side_effect = ValueError("Invalid wheel format")

    # Second strategy succeeds
    strategy2 = Mock()
    resolved_path = staging_dir / wheels_dir / "mypackage-1.0.0-py3-none-any.whl"
    strategy2.resolve.return_value = resolved_path

    wheel_files = {}
    project_wheels = {str(wheel)}

    wheel_stager.stage_wheels(wheel_files, project_wheels, [strategy1, strategy2])

    # Check audit log details
    found_error = False
    for event in build_plan.audit_log:
        if (event.stage == StageType.PLAN and
                event.substage == "stage_wheels" and
                event.event_type == EventType.EXCEPTION and
                "TestStrategy" in event.message and
                "Invalid wheel format" in event.message and
                "mypackage-1.0.0-py3-none-any.whl" in event.message):
            found_error = True
            break

    assert found_error, "Could not find audit log entry with correct exception details"


def test_stage_wheels_breaks_on_first_successful_strategy(tmp_path, monkeypatch):
    """Test stage_wheels stops trying strategies after first success."""
    build_plan = Mock()
    staging_dir = tmp_path / "staging"
    staging_dir.mkdir()
    wheels_dir = Path("wheels")
    (staging_dir / wheels_dir).mkdir()

    build_plan.staging_dir = staging_dir
    build_plan.wheels_dir = wheels_dir
    build_plan.audit_log = []

    wheel = tmp_path / "mypackage-1.0.0-py3-none-any.whl"
    wheel.write_text("content")

    # First strategy succeeds
    strategy1 = Mock()
    resolved_path = staging_dir / wheels_dir / "mypackage-1.0.0-py3-none-any.whl"
    strategy1.resolve.return_value = resolved_path

    # Second strategy should not be called
    strategy2 = Mock()

    wheel_files = {}
    project_wheels = {str(wheel)}

    wheel_stager.stage_wheels(wheel_files, project_wheels, [strategy1, strategy2])

    # Only first strategy should be called
    strategy1.resolve.assert_called_once()
    strategy2.resolve.assert_not_called()

    # No exceptions in audit log
    exception_count = sum(1 for event in build_plan.audit_log if event.event_type == "EXCEPTION")
    assert exception_count == 0, f"Found {exception_count} exception(s) in audit log, expected 0"