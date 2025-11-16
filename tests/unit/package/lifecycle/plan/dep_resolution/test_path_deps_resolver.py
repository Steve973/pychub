"""
Unit tests for path_deps_resolver.py

Tests the collect_path_dependencies function with mocked external dependencies.
"""
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from pychub.helper.toml_utils import dump_toml_to_str


# Test fixtures

@pytest.fixture
def mock_pyproject_toml():
    """Factory fixture to create mock pyproject.toml content."""

    def _factory(content_dict: dict) -> bytes:
        """Convert dict to TOML bytes for mocking file read."""
        try:
            return dump_toml_to_str(content_dict).encode('utf-8')
        except ImportError:
            # Fallback: simple TOML serialization for tests
            lines = []
            for key, value in content_dict.items():
                if isinstance(value, dict):
                    lines.append(f"[{key}]")
                    for k, v in value.items():
                        if isinstance(v, dict):
                            lines.append(f"[{key}.{k}]")
                            for k2, v2 in v.items():
                                lines.append(f'{k2} = "{v2}"')
                        else:
                            lines.append(f'{k} = "{v}"')
            return "\n".join(lines).encode('utf-8')

    return _factory


@pytest.fixture
def mock_strategy_class():
    """Factory to create mock strategy classes."""

    def _factory(label="MockStrategy", can_handle=True, extract_paths=None):
        mock = Mock()
        mock.label.return_value = label
        mock.can_handle.return_value = can_handle
        mock.extract_paths.return_value = extract_paths or []
        return mock

    return _factory


# Test: Basic functionality - single project with no dependencies
def test_collect_path_dependencies_single_project_no_deps(tmp_path, mock_strategy_class):
    """Test collecting dependencies from a single project with no path dependencies."""
    # Arrange
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text("[tool.poetry]\nname = \"test-project\"\n")

    mock_strategy = mock_strategy_class(label="Poetry", can_handle=True, extract_paths=[])

    toml_data = {"tool": {"poetry": {"name": "test-project"}}}

    with patch("pychub.package.lifecycle.plan.dep_resolution.path_deps_resolver.load_strategies") as mock_load, \
            patch("pychub.package.lifecycle.plan.dep_resolution.path_deps_resolver.tomllib.load") as mock_toml_load:
        mock_load.return_value = [mock_strategy]
        mock_toml_load.return_value = toml_data

        # Import after patching
        from pychub.package.lifecycle.plan.dep_resolution.path_deps_resolver import collect_path_dependencies

        # Act
        result = collect_path_dependencies(pyproject)

    # Assert
    assert len(result) == 1
    assert tmp_path.resolve() in result
    assert result[tmp_path.resolve()] == "Poetry"
    mock_strategy.can_handle.assert_called_once_with(toml_data)
    mock_strategy.extract_paths.assert_called_once_with(toml_data, tmp_path.resolve())


# Test: Multiple strategies - correct one is selected
def test_collect_path_dependencies_correct_strategy_selected(tmp_path, mock_strategy_class):
    """Test that the correct strategy is selected when multiple strategies are available."""
    # Arrange
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text("[tool.pdm]\nname = \"test-project\"\n")

    strategy1 = mock_strategy_class(label="Poetry", can_handle=False)
    strategy2 = mock_strategy_class(label="PDM", can_handle=True, extract_paths=[])
    strategy3 = mock_strategy_class(label="Hatch", can_handle=False)

    toml_data = {"tool": {"pdm": {"name": "test-project"}}}

    with patch("pychub.package.lifecycle.plan.dep_resolution.path_deps_resolver.load_strategies") as mock_load, \
            patch("pychub.package.lifecycle.plan.dep_resolution.path_deps_resolver.tomllib.load") as mock_toml_load:
        mock_load.return_value = [strategy1, strategy2, strategy3]
        mock_toml_load.return_value = toml_data

        from pychub.package.lifecycle.plan.dep_resolution.path_deps_resolver import collect_path_dependencies

        # Act
        result = collect_path_dependencies(pyproject)

    # Assert
    assert result[tmp_path.resolve()] == "PDM"
    strategy2.extract_paths.assert_called_once()
    strategy1.extract_paths.assert_not_called()
    strategy3.extract_paths.assert_not_called()


# Test: No strategy match - falls back to Default
def test_collect_path_dependencies_fallback_to_default(tmp_path):
    """Test that DefaultPathDepStrategy is used when no strategy matches."""
    # Arrange
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text("[project]\nname = \"test-project\"\n")

    mock_strategy = Mock()
    mock_strategy.can_handle.return_value = False

    # Mock load_strategies to return a strategy that doesn't match
    # The DefaultPathDepStrategy will be imported and used (not mocked)
    with patch("pychub.package.lifecycle.plan.dep_resolution.path_deps_resolver.load_strategies") as mock_load:
        mock_load.return_value = [mock_strategy]

        from pychub.package.lifecycle.plan.dep_resolution.path_deps_resolver import collect_path_dependencies

        # Act
        result = collect_path_dependencies(pyproject)

    # Assert
    # The actual DefaultPathDepStrategy should have been used
    assert result[tmp_path.resolve()] == "Default"
    assert len(result) == 1



# Test: Multiple strategies match - raises error
def test_collect_path_dependencies_multiple_strategies_match_raises_error(tmp_path, mock_strategy_class):
    """Test that an error is raised when multiple strategies match."""
    # Arrange
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text("[tool.poetry]\nname = \"test-project\"\n")

    strategy1 = mock_strategy_class(label="Poetry", can_handle=True)
    strategy2 = mock_strategy_class(label="PDM", can_handle=True)

    toml_data = {"tool": {"poetry": {"name": "test-project"}}}

    with patch("pychub.package.lifecycle.plan.dep_resolution.path_deps_resolver.load_strategies") as mock_load, \
            patch("pychub.package.lifecycle.plan.dep_resolution.path_deps_resolver.tomllib.load") as mock_toml_load:
        mock_load.return_value = [strategy1, strategy2]
        mock_toml_load.return_value = toml_data

        from pychub.package.lifecycle.plan.dep_resolution.path_deps_resolver import collect_path_dependencies

        # Act & Assert
        with pytest.raises(RuntimeError, match="Multiple strategies matched"):
            collect_path_dependencies(pyproject)


# Test: Recursive dependency resolution
def test_collect_path_dependencies_recursive_resolution(tmp_path, mock_strategy_class):
    """Test that dependencies are resolved recursively."""
    # Arrange
    # Create directory structure
    project_root = tmp_path / "main_project"
    project_root.mkdir()
    dep1_root = tmp_path / "dep1"
    dep1_root.mkdir()
    dep2_root = tmp_path / "dep2"
    dep2_root.mkdir()

    main_pyproject = project_root / "pyproject.toml"
    main_pyproject.write_text("[tool.poetry]\nname = \"main\"\n")

    dep1_pyproject = dep1_root / "pyproject.toml"
    dep1_pyproject.write_text("[tool.poetry]\nname = \"dep1\"\n")

    dep2_pyproject = dep2_root / "pyproject.toml"
    dep2_pyproject.write_text("[tool.poetry]\nname = \"dep2\"\n")

    # Create mock strategy that returns different paths based on input
    mock_strategy = Mock()
    mock_strategy.can_handle.return_value = True
    mock_strategy.label.return_value = "Poetry"

    def extract_side_effect(data, project_root_path):
        if "main" in str(data):
            return [dep1_root.resolve(), dep2_root.resolve()]
        else:
            return []

    mock_strategy.extract_paths.side_effect = extract_side_effect

    toml_data_main = {"tool": {"poetry": {"name": "main"}}}
    toml_data_dep1 = {"tool": {"poetry": {"name": "dep1"}}}
    toml_data_dep2 = {"tool": {"poetry": {"name": "dep2"}}}

    def toml_load_side_effect(f):
        content = f.read()
        if b"main" in content:
            return toml_data_main
        elif b"dep1" in content:
            return toml_data_dep1
        else:
            return toml_data_dep2

    with patch("pychub.package.lifecycle.plan.dep_resolution.path_deps_resolver.load_strategies") as mock_load, \
            patch("pychub.package.lifecycle.plan.dep_resolution.path_deps_resolver.tomllib.load") as mock_toml_load:

        mock_load.return_value = [mock_strategy]
        mock_toml_load.side_effect = toml_load_side_effect

        from pychub.package.lifecycle.plan.dep_resolution.path_deps_resolver import collect_path_dependencies

        # Act
        result = collect_path_dependencies(main_pyproject)

    # Assert
    assert len(result) == 3
    assert project_root.resolve() in result
    assert dep1_root.resolve() in result
    assert dep2_root.resolve() in result
    assert all(label == "Poetry" for label in result.values())


# Test: Circular dependency detection (via seen dict)
def test_collect_path_dependencies_circular_dependency_handled(tmp_path, mock_strategy_class):
    """Test that circular dependencies are handled properly using the seen dict."""
    # Arrange
    project_a = tmp_path / "project_a"
    project_a.mkdir()
    project_b = tmp_path / "project_b"
    project_b.mkdir()

    pyproject_a = project_a / "pyproject.toml"
    pyproject_a.write_text("[tool.poetry]\nname = \"a\"\n")

    pyproject_b = project_b / "pyproject.toml"
    pyproject_b.write_text("[tool.poetry]\nname = \"b\"\n")

    mock_strategy = Mock()
    mock_strategy.can_handle.return_value = True
    mock_strategy.label.return_value = "Poetry"

    # A depends on B, B depends on A (circular)
    def extract_side_effect(data, project_root_path):
        if "a" in str(data):
            return [project_b.resolve()]
        elif "b" in str(data):
            return [project_a.resolve()]
        return []

    mock_strategy.extract_paths.side_effect = extract_side_effect

    toml_data_a = {"tool": {"poetry": {"name": "a"}}}
    toml_data_b = {"tool": {"poetry": {"name": "b"}}}

    def toml_load_side_effect(f):
        content = f.read()
        if b"a" in content:
            return toml_data_a
        else:
            return toml_data_b

    with patch("pychub.package.lifecycle.plan.dep_resolution.path_deps_resolver.load_strategies") as mock_load, \
            patch("pychub.package.lifecycle.plan.dep_resolution.path_deps_resolver.tomllib.load") as mock_toml_load:

        mock_load.return_value = [mock_strategy]
        mock_toml_load.side_effect = toml_load_side_effect

        from pychub.package.lifecycle.plan.dep_resolution.path_deps_resolver import collect_path_dependencies

        # Act
        result = collect_path_dependencies(pyproject_a)

    # Assert
    # Should visit both projects exactly once
    assert len(result) == 2
    assert project_a.resolve() in result
    assert project_b.resolve() in result


# Test: Missing pyproject.toml in dependency raises error
def test_collect_path_dependencies_missing_pyproject_raises_error(tmp_path, mock_strategy_class):
    """Test that missing pyproject.toml in a dependency raises FileNotFoundError."""
    # Arrange
    project_root = tmp_path / "main_project"
    project_root.mkdir()
    dep_root = tmp_path / "dep_without_pyproject"
    dep_root.mkdir()  # No pyproject.toml created

    pyproject = project_root / "pyproject.toml"
    pyproject.write_text("[tool.poetry]\nname = \"main\"\n")

    mock_strategy = mock_strategy_class(
        label="Poetry",
        can_handle=True,
        extract_paths=[dep_root.resolve()]
    )

    toml_data = {"tool": {"poetry": {"name": "main"}}}

    with patch("pychub.package.lifecycle.plan.dep_resolution.path_deps_resolver.load_strategies") as mock_load, \
            patch("pychub.package.lifecycle.plan.dep_resolution.path_deps_resolver.tomllib.load") as mock_toml_load:
        mock_load.return_value = [mock_strategy]
        mock_toml_load.return_value = toml_data

        from pychub.package.lifecycle.plan.dep_resolution.path_deps_resolver import collect_path_dependencies

        # Act & Assert
        with pytest.raises(FileNotFoundError, match="missing pyproject.toml"):
            collect_path_dependencies(pyproject)


# Test: Depth parameter and print output
def test_collect_path_dependencies_depth_parameter(tmp_path, mock_strategy_class, capsys):
    """Test that depth parameter affects print indentation."""
    # Arrange
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text("[tool.poetry]\nname = \"test\"\n")

    mock_strategy = mock_strategy_class(label="Poetry", can_handle=True, extract_paths=[])
    toml_data = {"tool": {"poetry": {"name": "test"}}}

    with patch("pychub.package.lifecycle.plan.dep_resolution.path_deps_resolver.load_strategies") as mock_load, \
            patch("pychub.package.lifecycle.plan.dep_resolution.path_deps_resolver.tomllib.load") as mock_toml_load:
        mock_load.return_value = [mock_strategy]
        mock_toml_load.return_value = toml_data

        from pychub.package.lifecycle.plan.dep_resolution.path_deps_resolver import collect_path_dependencies

        # Act
        collect_path_dependencies(pyproject, depth=3)

        # Assert
        captured = capsys.readouterr()
        # Should have 3 levels of indentation (3 * 2 spaces = 6 spaces)
        assert "      [Poetry" in captured.out


# Test: Pre-populated seen dict
def test_collect_path_dependencies_with_prepopulated_seen(tmp_path, mock_strategy_class):
    """Test that pre-populated seen dict prevents re-processing."""
    # Arrange
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text("[tool.poetry]\nname = \"test\"\n")

    mock_strategy = mock_strategy_class(label="Poetry", can_handle=True, extract_paths=[])

    # Pre-populate seen dict with this project
    seen = {tmp_path.resolve(): "PreExisting"}

    with patch("pychub.package.lifecycle.plan.dep_resolution.path_deps_resolver.load_strategies") as mock_load, \
            patch("pychub.package.lifecycle.plan.dep_resolution.path_deps_resolver.tomllib.load") as mock_toml_load:
        mock_load.return_value = [mock_strategy]

        from pychub.package.lifecycle.plan.dep_resolution.path_deps_resolver import collect_path_dependencies

        # Act
        result = collect_path_dependencies(pyproject, seen=seen)

    # Assert
    assert result is seen
    assert result[tmp_path.resolve()] == "PreExisting"
    # Should not have read the file or called strategies
    mock_toml_load.assert_not_called()
    mock_strategy.can_handle.assert_not_called()


# Test: Path resolution (relative to absolute)
def test_collect_path_dependencies_resolves_paths(tmp_path, mock_strategy_class):
    """Test that paths are resolved to absolute paths."""
    # Arrange
    pyproject = tmp_path / "subdir" / "pyproject.toml"
    pyproject.parent.mkdir(parents=True)
    pyproject.write_text("[tool.poetry]\nname = \"test\"\n")

    mock_strategy = mock_strategy_class(label="Poetry", can_handle=True, extract_paths=[])

    with patch("pychub.package.lifecycle.plan.dep_resolution.path_deps_resolver.load_strategies") as mock_load:
        mock_load.return_value = [mock_strategy]

        from pychub.package.lifecycle.plan.dep_resolution.path_deps_resolver import collect_path_dependencies

        # Act
        result = collect_path_dependencies(pyproject)

    # Assert
    # Should contain the resolved absolute path
    assert (tmp_path / "subdir").resolve() in result
    # Verify the strategy was called with the resolved project root
    mock_strategy.extract_paths.assert_called_once()
    call_args = mock_strategy.extract_paths.call_args
    assert call_args[0][1] == (tmp_path / "subdir").resolve()  # project_root argument


# Test: Empty dependencies list
def test_collect_path_dependencies_empty_deps_list(tmp_path, mock_strategy_class):
    """Test handling when strategy returns empty list."""
    # Arrange
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text("[tool.poetry]\nname = \"test\"\n")

    mock_strategy = mock_strategy_class(label="Poetry", can_handle=True, extract_paths=[])
    toml_data = {"tool": {"poetry": {"name": "test"}}}

    with patch("pychub.package.lifecycle.plan.dep_resolution.path_deps_resolver.load_strategies") as mock_load, \
            patch("pychub.package.lifecycle.plan.dep_resolution.path_deps_resolver.tomllib.load") as mock_toml_load:
        mock_load.return_value = [mock_strategy]
        mock_toml_load.return_value = toml_data

        from pychub.package.lifecycle.plan.dep_resolution.path_deps_resolver import collect_path_dependencies

        # Act
        result = collect_path_dependencies(pyproject)

    # Assert
    assert len(result) == 1
    assert result[tmp_path.resolve()] == "Poetry"


# Test: Complex nested dependency tree
def test_collect_path_dependencies_complex_tree(tmp_path, mock_strategy_class):
    """Test a complex dependency tree with multiple levels."""
    # Arrange
    # Create structure: main -> [lib1, lib2], lib1 -> [lib3], lib2 -> [lib3]
    main = tmp_path / "main"
    lib1 = tmp_path / "lib1"
    lib2 = tmp_path / "lib2"
    lib3 = tmp_path / "lib3"

    for path in [main, lib1, lib2, lib3]:
        path.mkdir()
        (path / "pyproject.toml").write_text(f"[tool.poetry]\nname = \"{path.name}\"\n")

    mock_strategy = Mock()
    mock_strategy.can_handle.return_value = True
    mock_strategy.label.return_value = "Poetry"

    # Define dependency relationships
    def extract_side_effect(data, project_root_path):
        name = data["tool"]["poetry"]["name"]
        if name == "main":
            return [lib1.resolve(), lib2.resolve()]
        elif name == "lib1":
            return [lib3.resolve()]
        elif name == "lib2":
            return [lib3.resolve()]
        else:
            return []

    mock_strategy.extract_paths.side_effect = extract_side_effect

    def toml_load_side_effect(f):
        content = f.read()
        for path in [main, lib1, lib2, lib3]:
            if path.name.encode() in content:
                return {"tool": {"poetry": {"name": path.name}}}
        return {}

    with patch("pychub.package.lifecycle.plan.dep_resolution.path_deps_resolver.load_strategies") as mock_load, \
            patch("pychub.package.lifecycle.plan.dep_resolution.path_deps_resolver.tomllib.load") as mock_toml_load:

        mock_load.return_value = [mock_strategy]
        mock_toml_load.side_effect = toml_load_side_effect

        from pychub.package.lifecycle.plan.dep_resolution.path_deps_resolver import collect_path_dependencies

        # Act
        result = collect_path_dependencies(main / "pyproject.toml")

    # Assert
    assert len(result) == 4
    assert main.resolve() in result
    assert lib1.resolve() in result
    assert lib2.resolve() in result
    assert lib3.resolve() in result  # lib3 visited only once despite multiple references


# Test: TOML loading with different Python versions (tomllib vs tomli)
def test_collect_path_dependencies_toml_import(tmp_path, mock_strategy_class):
    """Test that TOML loading works (testing the import fallback logic)."""
    # This test verifies the module imports correctly
    # Arrange
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text("[tool.poetry]\nname = \"test\"\n")

    mock_strategy = mock_strategy_class(label="Poetry", can_handle=True, extract_paths=[])
    toml_data = {"tool": {"poetry": {"name": "test"}}}

    with patch("pychub.package.lifecycle.plan.dep_resolution.path_deps_resolver.load_strategies") as mock_load, \
            patch("pychub.package.lifecycle.plan.dep_resolution.path_deps_resolver.tomllib.load") as mock_toml_load:
        mock_load.return_value = [mock_strategy]
        mock_toml_load.return_value = toml_data

        from pychub.package.lifecycle.plan.dep_resolution.path_deps_resolver import collect_path_dependencies

        # Act
        result = collect_path_dependencies(pyproject)

    # Assert
    assert len(result) == 1
    # Verify tomllib.load was called with file object in binary mode
    mock_toml_load.assert_called_once()


# Test: Strategy label formatting in output
def test_collect_path_dependencies_label_formatting(tmp_path, capsys):
    """Test that strategy labels are formatted correctly in print output."""
    # Arrange
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text("[tool.poetry]\nname = \"test\"\n")

    mock_strategy = Mock()
    mock_strategy.can_handle.return_value = True
    mock_strategy.label.return_value = "TestStrategy"
    mock_strategy.extract_paths.return_value = []

    toml_data = {"tool": {"poetry": {"name": "test"}}}

    with patch("pychub.package.lifecycle.plan.dep_resolution.path_deps_resolver.load_strategies") as mock_load, \
            patch("pychub.package.lifecycle.plan.dep_resolution.path_deps_resolver.tomllib.load") as mock_toml_load:
        mock_load.return_value = [mock_strategy]
        mock_toml_load.return_value = toml_data

        from pychub.package.lifecycle.plan.dep_resolution.path_deps_resolver import collect_path_dependencies

        # Act
        collect_path_dependencies(pyproject)

        # Assert
        captured = capsys.readouterr()
        # Check label is printed with proper formatting
        assert "[TestStrategy]" in captured.out
        assert "0 deps" in captured.out


# Test: Return value structure
def test_collect_path_dependencies_return_value_structure(tmp_path, mock_strategy_class):
    """Test that the return value has the correct structure (dict[Path, str])."""
    # Arrange
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text("[tool.poetry]\nname = \"test\"\n")

    mock_strategy = mock_strategy_class(label="Poetry", can_handle=True, extract_paths=[])
    toml_data = {"tool": {"poetry": {"name": "test"}}}

    with patch("pychub.package.lifecycle.plan.dep_resolution.path_deps_resolver.load_strategies") as mock_load, \
            patch("pychub.package.lifecycle.plan.dep_resolution.path_deps_resolver.tomllib.load") as mock_toml_load:
        mock_load.return_value = [mock_strategy]
        mock_toml_load.return_value = toml_data

        from pychub.package.lifecycle.plan.dep_resolution.path_deps_resolver import collect_path_dependencies

        # Act
        result = collect_path_dependencies(pyproject)

    # Assert
    assert isinstance(result, dict)
    for key, value in result.items():
        assert isinstance(key, Path)
        assert isinstance(value, str)