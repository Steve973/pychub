from unittest.mock import patch

import pytest

from pychub.package.lifecycle.plan.dep_resolution.wheeldeps.path_resolution_strategy import PathResolutionStrategy


@pytest.fixture
def strategy():
    """Create a PathResolutionStrategy instance for testing."""
    return PathResolutionStrategy()


@pytest.fixture
def mock_output_dir(tmp_path):
    """Create a temporary output directory."""
    return tmp_path / "output"


def test_strategy_name(strategy):
    """Test that the strategy has the correct name."""
    assert strategy.name == "path"


def test_resolve_creates_output_directory(strategy, tmp_path):
    """Test that resolve creates the output directory if it doesn't exist."""
    output_dir = tmp_path / "output"
    project_path = tmp_path / "project"
    pyproject_path = project_path / "pyproject.toml"

    # Setup project structure
    project_path.mkdir()
    pyproject_path.touch()
    dist_dir = project_path / "dist"
    dist_dir.mkdir()
    wheel = dist_dir / "test-1.0.0-py3-none-any.whl"
    wheel.touch()

    with patch(
            'pychub.package.lifecycle.plan.dep_resolution.wheeldeps.path_resolution_strategy.collect_path_dependencies') as mock_collect:
        mock_collect.return_value = {project_path: "root"}

        strategy.resolve(str(project_path), output_dir)

        assert output_dir.exists()
        assert output_dir.is_dir()


def test_resolve_with_project_directory(strategy, tmp_path):
    """Test resolve with a project directory path."""
    output_dir = tmp_path / "output"
    project_path = tmp_path / "project"
    pyproject_path = project_path / "pyproject.toml"

    # Setup project structure
    project_path.mkdir()
    pyproject_path.touch()
    dist_dir = project_path / "dist"
    dist_dir.mkdir()
    wheel = dist_dir / "test-1.0.0-py3-none-any.whl"
    wheel.touch()

    with patch(
            'pychub.package.lifecycle.plan.dep_resolution.wheeldeps.path_resolution_strategy.collect_path_dependencies') as mock_collect:
        mock_collect.return_value = {project_path: "root"}

        result = strategy.resolve(str(project_path), output_dir)

        assert result == (output_dir / wheel.name).resolve()
        assert (output_dir / wheel.name).exists()


def test_resolve_with_pyproject_toml_path(strategy, tmp_path):
    """Test resolve when given direct path to pyproject.toml."""
    output_dir = tmp_path / "output"
    project_path = tmp_path / "project"
    pyproject_path = project_path / "pyproject.toml"

    # Setup project structure
    project_path.mkdir()
    pyproject_path.touch()
    dist_dir = project_path / "dist"
    dist_dir.mkdir()
    wheel = dist_dir / "test-1.0.0-py3-none-any.whl"
    wheel.touch()

    with patch(
            'pychub.package.lifecycle.plan.dep_resolution.wheeldeps.path_resolution_strategy.collect_path_dependencies') as mock_collect:
        mock_collect.return_value = {project_path: "root"}

        result = strategy.resolve(str(pyproject_path), output_dir)

        assert result == (output_dir / wheel.name).resolve()
        mock_collect.assert_called_once_with(pyproject_path)


def test_resolve_missing_pyproject_toml(strategy, tmp_path):
    """Test that resolve raises FileNotFoundError when pyproject.toml is missing."""
    output_dir = tmp_path / "output"
    project_path = tmp_path / "project"
    project_path.mkdir()

    with pytest.raises(FileNotFoundError, match=r"No pyproject.toml found at"):
        strategy.resolve(str(project_path), output_dir)


def test_resolve_copies_multiple_wheels(strategy, tmp_path):
    """Test that resolve copies all wheels from dist directory."""
    output_dir = tmp_path / "output"
    project_path = tmp_path / "project"
    pyproject_path = project_path / "pyproject.toml"

    # Setup project structure
    project_path.mkdir()
    pyproject_path.touch()
    dist_dir = project_path / "dist"
    dist_dir.mkdir()
    wheel1 = dist_dir / "test-1.0.0-py3-none-any.whl"
    wheel2 = dist_dir / "test-1.0.0-cp39-cp39-linux_x86_64.whl"
    wheel1.touch()
    wheel2.touch()

    with patch(
            'pychub.package.lifecycle.plan.dep_resolution.wheeldeps.path_resolution_strategy.collect_path_dependencies') as mock_collect:
        mock_collect.return_value = {project_path: "root"}

        result = strategy.resolve(str(project_path), output_dir)

        assert (output_dir / wheel1.name).exists()
        assert (output_dir / wheel2.name).exists()
        assert result in [(output_dir / wheel1.name).resolve(), (output_dir / wheel2.name).resolve()]


def test_resolve_multiple_path_dependencies(strategy, tmp_path):
    """Test resolve with multiple path dependencies."""
    output_dir = tmp_path / "output"
    project_path = tmp_path / "project"
    dep1_path = tmp_path / "dep1"
    dep2_path = tmp_path / "dep2"

    # Setup main project
    project_path.mkdir()
    (project_path / "pyproject.toml").touch()
    project_dist = project_path / "dist"
    project_dist.mkdir()
    project_wheel = project_dist / "project-1.0.0-py3-none-any.whl"
    project_wheel.touch()

    # Setup dependency 1
    dep1_path.mkdir()
    dep1_dist = dep1_path / "dist"
    dep1_dist.mkdir()
    dep1_wheel = dep1_dist / "dep1-2.0.0-py3-none-any.whl"
    dep1_wheel.touch()

    # Setup dependency 2
    dep2_path.mkdir()
    dep2_dist = dep2_path / "dist"
    dep2_dist.mkdir()
    dep2_wheel = dep2_dist / "dep2-3.0.0-py3-none-any.whl"
    dep2_wheel.touch()

    with patch(
            'pychub.package.lifecycle.plan.dep_resolution.wheeldeps.path_resolution_strategy.collect_path_dependencies') as mock_collect:
        mock_collect.return_value = {
            project_path: "root",
            dep1_path: "dep1",
            dep2_path: "dep2"
        }

        result = strategy.resolve(str(project_path), output_dir)

        assert (output_dir / project_wheel.name).exists()
        assert (output_dir / dep1_wheel.name).exists()
        assert (output_dir / dep2_wheel.name).exists()


def test_resolve_no_wheels_found(strategy, tmp_path):
    """Test that resolve raises RuntimeError when no wheels are found."""
    output_dir = tmp_path / "output"
    project_path = tmp_path / "project"
    pyproject_path = project_path / "pyproject.toml"

    # Setup project structure without wheels
    project_path.mkdir()
    pyproject_path.touch()
    dist_dir = project_path / "dist"
    dist_dir.mkdir()

    with patch(
            'pychub.package.lifecycle.plan.dep_resolution.wheeldeps.path_resolution_strategy.collect_path_dependencies') as mock_collect:
        mock_collect.return_value = {project_path: "root"}

        with pytest.raises(RuntimeError, match=r"No wheels found in path dependencies"):
            strategy.resolve(str(project_path), output_dir)


def test_resolve_skips_existing_wheels(strategy, tmp_path):
    """Test that resolve doesn't overwrite existing wheels in output_dir."""
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    project_path = tmp_path / "project"
    pyproject_path = project_path / "pyproject.toml"

    # Setup project structure
    project_path.mkdir()
    pyproject_path.touch()
    dist_dir = project_path / "dist"
    dist_dir.mkdir()
    wheel = dist_dir / "test-1.0.0-py3-none-any.whl"
    wheel.write_text("original content")

    # Pre-create wheel in output dir
    existing_wheel = output_dir / wheel.name
    existing_wheel.write_text("existing content")

    with patch(
            'pychub.package.lifecycle.plan.dep_resolution.wheeldeps.path_resolution_strategy.collect_path_dependencies') as mock_collect:
        mock_collect.return_value = {project_path: "root"}

        with patch(
                'pychub.package.lifecycle.plan.dep_resolution.wheeldeps.path_resolution_strategy.shutil.copy2') as mock_copy:
            result = strategy.resolve(str(project_path), output_dir)

            # Verify copy2 was not called since file exists
            mock_copy.assert_not_called()
            assert existing_wheel.read_text() == "existing content"


def test_resolve_uses_shutil_copy2(strategy, tmp_path):
    """Test that resolve uses shutil.copy2 to preserve metadata."""
    output_dir = tmp_path / "output"
    project_path = tmp_path / "project"
    pyproject_path = project_path / "pyproject.toml"

    # Setup project structure
    project_path.mkdir()
    pyproject_path.touch()
    dist_dir = project_path / "dist"
    dist_dir.mkdir()
    wheel = dist_dir / "test-1.0.0-py3-none-any.whl"
    wheel.touch()

    with patch(
            'pychub.package.lifecycle.plan.dep_resolution.wheeldeps.path_resolution_strategy.collect_path_dependencies') as mock_collect:
        mock_collect.return_value = {project_path: "root"}

        with patch(
                'pychub.package.lifecycle.plan.dep_resolution.wheeldeps.path_resolution_strategy.shutil.copy2') as mock_copy:
            strategy.resolve(str(project_path), output_dir)

            mock_copy.assert_called_once_with(wheel, output_dir / wheel.name)


def test_resolve_returns_resolved_path(strategy, tmp_path):
    """Test that resolve returns an absolute resolved path."""
    output_dir = tmp_path / "output"
    project_path = tmp_path / "project"
    pyproject_path = project_path / "pyproject.toml"

    # Setup project structure
    project_path.mkdir()
    pyproject_path.touch()
    dist_dir = project_path / "dist"
    dist_dir.mkdir()
    wheel = dist_dir / "test-1.0.0-py3-none-any.whl"
    wheel.touch()

    with patch(
            'pychub.package.lifecycle.plan.dep_resolution.wheeldeps.path_resolution_strategy.collect_path_dependencies') as mock_collect:
        mock_collect.return_value = {project_path: "root"}

        result = strategy.resolve(str(project_path), output_dir)

        assert result.is_absolute()
        assert result == (output_dir / wheel.name).resolve()


def test_resolve_with_relative_path(strategy, tmp_path, monkeypatch):
    """Test resolve with a relative path input."""
    output_dir = tmp_path / "output"
    project_path = tmp_path / "project"
    pyproject_path = project_path / "pyproject.toml"

    # Setup project structure
    project_path.mkdir()
    pyproject_path.touch()
    dist_dir = project_path / "dist"
    dist_dir.mkdir()
    wheel = dist_dir / "test-1.0.0-py3-none-any.whl"
    wheel.touch()

    # Change to tmp_path directory to make relative path work
    monkeypatch.chdir(tmp_path)

    with patch(
            'pychub.package.lifecycle.plan.dep_resolution.wheeldeps.path_resolution_strategy.collect_path_dependencies') as mock_collect:
        mock_collect.return_value = {project_path: "root"}

        result = strategy.resolve("project", output_dir)

        assert result.is_absolute()
        assert (output_dir / wheel.name).exists()


def test_resolve_collects_path_dependencies_correctly(strategy, tmp_path):
    """Test that resolve passes the correct pyproject_path to collect_path_dependencies."""
    output_dir = tmp_path / "output"
    project_path = tmp_path / "project"
    pyproject_path = project_path / "pyproject.toml"

    # Setup project structure
    project_path.mkdir()
    pyproject_path.touch()
    dist_dir = project_path / "dist"
    dist_dir.mkdir()
    wheel = dist_dir / "test-1.0.0-py3-none-any.whl"
    wheel.touch()

    with patch(
            'pychub.package.lifecycle.plan.dep_resolution.wheeldeps.path_resolution_strategy.collect_path_dependencies') as mock_collect:
        mock_collect.return_value = {project_path: "root"}

        strategy.resolve(str(project_path), output_dir)

        # Verify collect_path_dependencies was called with the resolved pyproject path
        mock_collect.assert_called_once()
        called_path = mock_collect.call_args[0][0]
        assert called_path == pyproject_path


def test_resolve_handles_empty_dist_directory(strategy, tmp_path):
    """Test resolve when dist directory exists but contains no wheels."""
    output_dir = tmp_path / "output"
    project_path = tmp_path / "project"
    pyproject_path = project_path / "pyproject.toml"

    # Setup project structure with empty dist
    project_path.mkdir()
    pyproject_path.touch()
    dist_dir = project_path / "dist"
    dist_dir.mkdir()
    # Add non-wheel file
    (dist_dir / "readme.txt").touch()

    with patch(
            'pychub.package.lifecycle.plan.dep_resolution.wheeldeps.path_resolution_strategy.collect_path_dependencies') as mock_collect:
        mock_collect.return_value = {project_path: "root"}

        with pytest.raises(RuntimeError, match=r"No wheels found in path dependencies"):
            strategy.resolve(str(project_path), output_dir)


def test_resolve_handles_missing_dist_directory(strategy, tmp_path):
    """Test resolve when dist directory doesn't exist."""
    output_dir = tmp_path / "output"
    project_path = tmp_path / "project"
    pyproject_path = project_path / "pyproject.toml"

    # Setup project structure without dist
    project_path.mkdir()
    pyproject_path.touch()

    with patch(
            'pychub.package.lifecycle.plan.dep_resolution.wheeldeps.path_resolution_strategy.collect_path_dependencies') as mock_collect:
        mock_collect.return_value = {project_path: "root"}

        with pytest.raises(RuntimeError, match=r"No wheels found in path dependencies"):
            strategy.resolve(str(project_path), output_dir)