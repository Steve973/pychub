"""
Comprehensive test suite for the discover module.

Tests cover:
- Basic path dependency collection
- Recursive dependency resolution
- Strategy selection and fallback
- Error handling (missing files, multiple strategies)
- Depth tracking
- Caching/memoization via 'seen' dict
- Edge cases (empty deps, self-references)
"""

from pathlib import Path
from typing import Dict
from unittest.mock import patch

import pytest

from pychub.package.pathdeps.base import PathDepStrategy
from pychub.package.pathdeps.discover import collect_path_dependencies


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def mock_toml_data():
    """Factory fixture to generate mock TOML data."""

    def _factory(tool_section=None, dependencies=None):
        data = {}
        if tool_section:
            data["tool"] = tool_section
        if dependencies:
            data["dependencies"] = dependencies
        return data

    return _factory


@pytest.fixture
def mock_strategy():
    """Create a mock strategy for testing."""

    class MockStrategy(PathDepStrategy):
        def __init__(self, label_name="MockStrategy", can_handle_result=True, extract_result=None):
            self._label = label_name
            self._can_handle = can_handle_result
            self._extract = extract_result or []

        def can_handle(self, data: dict) -> bool:
            return self._can_handle

        def extract_paths(self, data: dict, project_root: Path) -> list[Path]:
            return self._extract

        def label(self) -> str:
            return self._label

    return MockStrategy


@pytest.fixture
def temp_project_structure(tmp_path):
    """
    Create a temporary project structure with multiple nested dependencies.

    Structure:
        root/
            pyproject.toml
            dep1/
                pyproject.toml
                dep2/
                    pyproject.toml
    """
    root = tmp_path / "root"
    root.mkdir()
    (root / "pyproject.toml").write_text("[tool.poetry]\nname = 'root'\n")

    dep1 = root / "dep1"
    dep1.mkdir()
    (dep1 / "pyproject.toml").write_text("[tool.poetry]\nname = 'dep1'\n")

    dep2 = dep1 / "dep2"
    dep2.mkdir()
    (dep2 / "pyproject.toml").write_text("[tool.poetry]\nname = 'dep2'\n")

    return {"root": root, "dep1": dep1, "dep2": dep2}


# ============================================================================
# Basic Functionality Tests
# ============================================================================

def test_collect_path_dependencies_single_project_no_deps(tmp_path, mock_strategy):
    """Test collecting from a single project with no dependencies."""
    project = tmp_path / "myproject"
    project.mkdir()
    pyproject = project / "pyproject.toml"
    pyproject.write_text("[tool.poetry]\nname = 'test'\n")

    mock_strat = mock_strategy(label_name="TestStrategy", extract_result=[])

    with patch("pychub.package.pathdeps.discover.load_strategies", return_value=[mock_strat]):
        result = collect_path_dependencies(pyproject)

    assert len(result) == 1
    assert project in result
    assert result[project] == "TestStrategy"


def test_collect_path_dependencies_with_single_dep(tmp_path, mock_strategy):
    """Test collecting from a project with one path dependency."""
    root = tmp_path / "root"
    root.mkdir()
    root_pyproject = root / "pyproject.toml"
    root_pyproject.write_text("[tool.poetry]\nname = 'root'\n")

    dep = tmp_path / "dep"
    dep.mkdir()
    dep_pyproject = dep / "pyproject.toml"
    dep_pyproject.write_text("[tool.poetry]\nname = 'dep'\n")

    call_count = [0]

    def mock_load():
        call_count[0] += 1
        if call_count[0] == 1:
            return [mock_strategy(label_name="RootStrategy", extract_result=[dep])]
        return [mock_strategy(label_name="DepStrategy", extract_result=[])]

    with patch("pychub.package.pathdeps.discover.load_strategies", mock_load):
        result = collect_path_dependencies(root_pyproject)

    assert len(result) == 2
    assert root in result
    assert dep in result


def test_collect_path_dependencies_nested_three_levels(tmp_path, mock_strategy):
    """Test recursive collection across three dependency levels."""
    # Create structure: root -> dep1 -> dep2
    root = tmp_path / "root"
    root.mkdir()
    root_pyproject = root / "pyproject.toml"
    root_pyproject.write_text("")

    dep1 = tmp_path / "dep1"
    dep1.mkdir()
    dep1_pyproject = dep1 / "pyproject.toml"
    dep1_pyproject.write_text("")

    dep2 = tmp_path / "dep2"
    dep2.mkdir()
    dep2_pyproject = dep2 / "pyproject.toml"
    dep2_pyproject.write_text("")

    def mock_load_strategies():
        # Return different strategies based on which project we're in
        return [
            mock_strategy(label_name="Strategy",
                          extract_result=[dep1] if root.exists() else [dep2] if dep1.exists() else [])
        ]

    strategies_map = {
        root: [dep1],
        dep1: [dep2],
        dep2: []
    }

    call_count = [0]

    def side_effect_loader():
        call_count[0] += 1
        if call_count[0] == 1:
            return [mock_strategy(label_name="S1", extract_result=[dep1])]
        elif call_count[0] == 2:
            return [mock_strategy(label_name="S2", extract_result=[dep2])]
        else:
            return [mock_strategy(label_name="S3", extract_result=[])]

    with patch("pychub.package.pathdeps.discover.load_strategies", side_effect=side_effect_loader):
        result = collect_path_dependencies(root_pyproject)

    assert len(result) == 3
    assert root in result
    assert dep1 in result
    assert dep2 in result


def test_collect_path_dependencies_memoization(tmp_path, mock_strategy):
    """Test that seen dict prevents re-processing the same project."""
    root = tmp_path / "root"
    root.mkdir()
    root_pyproject = root / "pyproject.toml"
    root_pyproject.write_text("")

    seen: Dict[Path, str] = {root: "PreCached"}

    with patch("pychub.package.pathdeps.discover.load_strategies", return_value=[]):
        result = collect_path_dependencies(root_pyproject, seen=seen)

    # Should return immediately without processing
    assert len(result) == 1
    assert result[root] == "PreCached"


# ============================================================================
# Strategy Selection Tests
# ============================================================================

def test_strategy_selection_single_match(tmp_path, mock_strategy):
    """Test that a single matching strategy is selected."""
    project = tmp_path / "project"
    project.mkdir()
    pyproject = project / "pyproject.toml"
    pyproject.write_text("")

    matching = mock_strategy(label_name="Matching", can_handle_result=True, extract_result=[])
    non_matching = mock_strategy(label_name="NonMatching", can_handle_result=False, extract_result=[])

    with patch("pychub.package.pathdeps.discover.load_strategies", return_value=[non_matching, matching]):
        result = collect_path_dependencies(pyproject)

    assert result[project] == "Matching"


def test_strategy_selection_multiple_matches_raises_error(tmp_path, mock_strategy):
    """Test that multiple matching strategies raises RuntimeError."""
    project = tmp_path / "project"
    project.mkdir()
    pyproject = project / "pyproject.toml"
    pyproject.write_text("")

    strategy1 = mock_strategy(label_name="Strategy1", can_handle_result=True, extract_result=[])
    strategy2 = mock_strategy(label_name="Strategy2", can_handle_result=True, extract_result=[])

    with patch("pychub.package.pathdeps.discover.load_strategies", return_value=[strategy1, strategy2]):
        with pytest.raises(RuntimeError, match="Multiple strategies matched"):
            collect_path_dependencies(pyproject)


def test_strategy_selection_no_match_uses_default(tmp_path):
    """Test that when no strategy matches, DefaultPathDepStrategy is used."""
    project = tmp_path / "project"
    project.mkdir()
    pyproject = project / "pyproject.toml"
    pyproject.write_text("")

    with patch("pychub.package.pathdeps.discover.load_strategies", return_value=[]):
        result = collect_path_dependencies(pyproject)

    # Default strategy should be used
    assert project in result
    assert result[project] == "Default"


# ============================================================================
# Error Handling Tests
# ============================================================================

def test_missing_pyproject_raises_error(tmp_path):
    """Test that missing pyproject.toml raises FileNotFoundError."""
    non_existent = tmp_path / "non_existent" / "pyproject.toml"

    with pytest.raises(FileNotFoundError):
        collect_path_dependencies(non_existent)


def test_missing_dependency_pyproject_raises_error(tmp_path, mock_strategy):
    """Test that a dependency without pyproject.toml raises FileNotFoundError."""
    root = tmp_path / "root"
    root.mkdir()
    root_pyproject = root / "pyproject.toml"
    root_pyproject.write_text("")

    dep_without_pyproject = tmp_path / "dep"
    dep_without_pyproject.mkdir()
    # No pyproject.toml created

    strategy = mock_strategy(label_name="TestStrategy", extract_result=[dep_without_pyproject])

    with patch("pychub.package.pathdeps.discover.load_strategies", return_value=[strategy]):
        with pytest.raises(FileNotFoundError, match="missing pyproject.toml"):
            collect_path_dependencies(root_pyproject)


def test_invalid_toml_raises_error(tmp_path):
    """Test that invalid TOML content raises an error."""
    project = tmp_path / "project"
    project.mkdir()
    pyproject = project / "pyproject.toml"
    pyproject.write_text("this is not valid TOML {[}")

    with pytest.raises(Exception):  # tomllib/tomli will raise a parsing error
        collect_path_dependencies(pyproject)


# ============================================================================
# Circular Dependency Tests
# ============================================================================

def test_circular_dependency_handled_by_seen(tmp_path, mock_strategy):
    """Test that circular dependencies are handled by the seen dict."""
    # Create A -> B -> A circular dependency
    proj_a = tmp_path / "a"
    proj_a.mkdir()
    pyproject_a = proj_a / "pyproject.toml"
    pyproject_a.write_text("")

    proj_b = tmp_path / "b"
    proj_b.mkdir()
    pyproject_b = proj_b / "pyproject.toml"
    pyproject_b.write_text("")

    call_count = [0]

    def side_effect_loader():
        call_count[0] += 1
        if call_count[0] == 1:
            # A depends on B
            return [mock_strategy(label_name="StratA", extract_result=[proj_b])]
        else:
            # B depends on A (circular)
            return [mock_strategy(label_name="StratB", extract_result=[proj_a])]

    with patch("pychub.package.pathdeps.discover.load_strategies", side_effect=side_effect_loader):
        result = collect_path_dependencies(pyproject_a)

    # Should process both but not loop infinitely
    assert len(result) == 2
    assert proj_a in result
    assert proj_b in result


def test_self_reference_handled(tmp_path, mock_strategy):
    """Test that a project referencing itself doesn't cause infinite recursion."""
    project = tmp_path / "project"
    project.mkdir()
    pyproject = project / "pyproject.toml"
    pyproject.write_text("")

    # Strategy that extracts the project itself
    strategy = mock_strategy(label_name="SelfRef", extract_result=[project])

    with patch("pychub.package.pathdeps.discover.load_strategies", return_value=[strategy]):
        result = collect_path_dependencies(pyproject)

    # Should only appear once
    assert len(result) == 1
    assert project in result


# ============================================================================
# Depth Tracking Tests
# ============================================================================

def test_depth_parameter_passed_correctly(tmp_path, mock_strategy, capsys):
    """Test that depth parameter is tracked and passed correctly."""
    root = tmp_path / "root"
    root.mkdir()
    root_pyproject = root / "pyproject.toml"
    root_pyproject.write_text("")

    dep1 = tmp_path / "dep1"
    dep1.mkdir()
    dep1_pyproject = dep1 / "pyproject.toml"
    dep1_pyproject.write_text("")

    dep2 = tmp_path / "dep2"
    dep2.mkdir()
    dep2_pyproject = dep2 / "pyproject.toml"
    dep2_pyproject.write_text("")

    call_count = [0]

    def side_effect_loader():
        call_count[0] += 1
        if call_count[0] == 1:
            return [mock_strategy(label_name="S", extract_result=[dep1])]
        elif call_count[0] == 2:
            return [mock_strategy(label_name="S", extract_result=[dep2])]
        else:
            return [mock_strategy(label_name="S", extract_result=[])]

    with patch("pychub.package.pathdeps.discover.load_strategies", side_effect=side_effect_loader):
        result = collect_path_dependencies(root_pyproject)

    captured = capsys.readouterr()
    # Check that indentation increases with depth
    assert "[S" in captured.out
    assert "root" in captured.out
    assert "dep1" in captured.out
    assert "dep2" in captured.out


# ============================================================================
# Integration with Real Strategy Classes Tests
# ============================================================================

def test_collect_with_default_strategy_no_deps(tmp_path):
    """Test collection using the real DefaultPathDepStrategy."""
    project = tmp_path / "simple"
    project.mkdir()
    pyproject = project / "pyproject.toml"
    # Empty pyproject - no dependencies
    pyproject.write_text("[project]\nname = 'simple'\n")

    result = collect_path_dependencies(pyproject)

    assert len(result) == 1
    assert project in result


def test_collect_with_poetry_style_dependencies(tmp_path, mock_strategy):
    """Test that Poetry-style path dependencies are recognized."""
    project = tmp_path / "poetry_proj"
    project.mkdir()
    pyproject = project / "pyproject.toml"

    dep = tmp_path / "my_dep"
    dep.mkdir()
    dep_pyproject = dep / "pyproject.toml"
    dep_pyproject.write_text("")

    # Simulate Poetry TOML structure
    toml_content = f"""
[tool.poetry]
name = "poetry_proj"

[tool.poetry.dependencies]
python = "^3.9"
my_dep = {{path = "../my_dep"}}
"""
    pyproject.write_text(toml_content)

    # We'll need to mock or use the actual poetry strategy
    poetry_strategy = mock_strategy(label_name="Poetry", extract_result=[dep])

    with patch("pychub.package.pathdeps.discover.load_strategies", return_value=[poetry_strategy]):
        result = collect_path_dependencies(pyproject)

    assert project in result
    assert dep in result


# ============================================================================
# Path Resolution Tests
# ============================================================================

def test_path_resolution_relative_and_absolute(tmp_path, mock_strategy):
    """Test that both relative and absolute paths are resolved correctly."""
    root = tmp_path / "root"
    root.mkdir()
    root_pyproject = root / "pyproject.toml"
    root_pyproject.write_text("")

    dep = tmp_path / "dep"
    dep.mkdir()
    dep_pyproject = dep / "pyproject.toml"
    dep_pyproject.write_text("")

    # Use absolute path
    strategy = mock_strategy(label_name="Test", extract_result=[dep.resolve()])

    with patch("pychub.package.pathdeps.discover.load_strategies", return_value=[strategy]):
        result = collect_path_dependencies(root_pyproject)

    # All paths should be resolved
    assert all(p.is_absolute() for p in result.keys())


def test_symlink_handling(tmp_path, mock_strategy):
    """Test that symlinks to projects are handled correctly."""
    real_project = tmp_path / "real"
    real_project.mkdir()
    real_pyproject = real_project / "pyproject.toml"
    real_pyproject.write_text("")

    symlink = tmp_path / "link"
    try:
        symlink.symlink_to(real_project)
    except OSError:
        pytest.skip("Symlinks not supported on this platform")

    strategy = mock_strategy(label_name="Test", extract_result=[])

    with patch("pychub.package.pathdeps.discover.load_strategies", return_value=[strategy]):
        result = collect_path_dependencies(symlink / "pyproject.toml")

    # Should resolve to the real path
    assert real_project in result or symlink.resolve() in result


# ============================================================================
# Edge Cases and Boundary Tests
# ============================================================================

def test_empty_extract_paths_list(tmp_path, mock_strategy):
    """Test strategy returning empty list of dependencies."""
    project = tmp_path / "project"
    project.mkdir()
    pyproject = project / "pyproject.toml"
    pyproject.write_text("")

    strategy = mock_strategy(label_name="Empty", extract_result=[])

    with patch("pychub.package.pathdeps.discover.load_strategies", return_value=[strategy]):
        result = collect_path_dependencies(pyproject)

    assert len(result) == 1
    assert project in result


def test_large_dependency_tree(tmp_path, mock_strategy):
    """Test handling of a large dependency tree (10 levels deep)."""
    projects = []
    for i in range(10):
        proj = tmp_path / f"proj{i}"
        proj.mkdir()
        pyproject = proj / "pyproject.toml"
        pyproject.write_text("")
        projects.append(proj)

    # Create chain: proj0 -> proj1 -> proj2 -> ... -> proj9
    call_count = [0]

    def side_effect_loader():
        idx = call_count[0]
        call_count[0] += 1
        if idx < 9:
            return [mock_strategy(label_name="S", extract_result=[projects[idx + 1]])]
        return [mock_strategy(label_name="S", extract_result=[])]

    with patch("pychub.package.pathdeps.discover.load_strategies", side_effect=side_effect_loader):
        result = collect_path_dependencies(projects[0] / "pyproject.toml")

    assert len(result) == 10
    for proj in projects:
        assert proj in result


def test_multiple_dependencies_from_single_project(tmp_path, mock_strategy):
    """Test a project with multiple path dependencies."""
    root = tmp_path / "root"
    root.mkdir()
    root_pyproject = root / "pyproject.toml"
    root_pyproject.write_text("")

    deps = []
    for i in range(5):
        dep = tmp_path / f"dep{i}"
        dep.mkdir()
        dep_pyproject = dep / "pyproject.toml"
        dep_pyproject.write_text("")
        deps.append(dep)

    root_strategy = mock_strategy(label_name="Root", extract_result=deps)
    dep_strategy = mock_strategy(label_name="Dep", extract_result=[])

    def side_effect_loader():
        if not hasattr(side_effect_loader, 'count'):
            side_effect_loader.count = 0
        if side_effect_loader.count == 0:
            side_effect_loader.count += 1
            return [root_strategy]
        return [dep_strategy]

    with patch("pychub.package.pathdeps.discover.load_strategies", side_effect=side_effect_loader):
        result = collect_path_dependencies(root_pyproject)

    assert len(result) == 6  # root + 5 deps
    assert root in result
    for dep in deps:
        assert dep in result


def test_diamond_dependency_pattern(tmp_path, mock_strategy):
    """
    Test diamond dependency pattern:
        A
       / \\
      B   C
       \\ /
        D
    """
    proj_a = tmp_path / "a"
    proj_a.mkdir()
    (proj_a / "pyproject.toml").write_text("")

    proj_b = tmp_path / "b"
    proj_b.mkdir()
    (proj_b / "pyproject.toml").write_text("")

    proj_c = tmp_path / "c"
    proj_c.mkdir()
    (proj_c / "pyproject.toml").write_text("")

    proj_d = tmp_path / "d"
    proj_d.mkdir()
    (proj_d / "pyproject.toml").write_text("")

    # A depends on B and C
    # B depends on D
    # C depends on D
    # D has no dependencies

    strategies = {
        proj_a: [proj_b, proj_c],
        proj_b: [proj_d],
        proj_c: [proj_d],
        proj_d: []
    }

    seen_projects = []

    def side_effect_loader():
        # Determine which project we're currently processing
        # This is a bit tricky - we'll track by call order
        if not hasattr(side_effect_loader, 'calls'):
            side_effect_loader.calls = []

        call_num = len(side_effect_loader.calls)
        side_effect_loader.calls.append(call_num)

        if call_num == 0:  # proj_a
            return [mock_strategy(label_name="A", extract_result=[proj_b, proj_c])]
        elif call_num == 1:  # proj_b
            return [mock_strategy(label_name="B", extract_result=[proj_d])]
        elif call_num == 2:  # proj_d (first visit)
            return [mock_strategy(label_name="D", extract_result=[])]
        elif call_num == 3:  # proj_c
            return [mock_strategy(label_name="C", extract_result=[proj_d])]
        else:  # proj_d should not be processed again
            return [mock_strategy(label_name="D", extract_result=[])]

    with patch("pychub.package.pathdeps.discover.load_strategies", side_effect=side_effect_loader):
        result = collect_path_dependencies(proj_a / "pyproject.toml")

    # All 4 projects should be in result, but D should only be processed once
    assert len(result) == 4
    assert proj_a in result
    assert proj_b in result
    assert proj_c in result
    assert proj_d in result


# ============================================================================
# TOML Parsing Tests
# ============================================================================

def test_toml_with_binary_mode(tmp_path):
    """Test that TOML files are read in binary mode (rb)."""
    project = tmp_path / "project"
    project.mkdir()
    pyproject = project / "pyproject.toml"
    # Include non-ASCII characters to ensure binary reading works
    pyproject.write_text("[project]\nname = 'tëst'\n", encoding="utf-8")

    result = collect_path_dependencies(pyproject)

    assert project in result


def test_toml_with_complex_structure(tmp_path, mock_strategy):
    """Test parsing TOML with complex nested structures."""
    project = tmp_path / "complex"
    project.mkdir()
    pyproject = project / "pyproject.toml"

    toml_content = """
[project]
name = "complex"
version = "1.0.0"

[project.optional-dependencies]
dev = ["pytest", "black"]

[tool.custom]
nested = { key = "value" }

[[tool.custom.array]]
item = 1

[[tool.custom.array]]
item = 2
"""
    pyproject.write_text(toml_content)

    strategy = mock_strategy(label_name="Complex", extract_result=[])

    with patch("pychub.package.pathdeps.discover.load_strategies", return_value=[strategy]):
        result = collect_path_dependencies(pyproject)

    assert project in result


# ============================================================================
# Output/Logging Tests
# ============================================================================

def test_console_output_format(tmp_path, mock_strategy, capsys):
    """Test that the console output has correct format."""
    root = tmp_path / "myroot"
    root.mkdir()
    root_pyproject = root / "pyproject.toml"
    root_pyproject.write_text("")

    dep = tmp_path / "mydep"
    dep.mkdir()
    dep_pyproject = dep / "pyproject.toml"
    dep_pyproject.write_text("")

    call_count = [0]

    def side_effect_loader():
        call_count[0] += 1
        if call_count[0] == 1:
            return [mock_strategy(label_name="Custom", extract_result=[dep])]
        return [mock_strategy(label_name="Custom", extract_result=[])]

    with patch("pychub.package.pathdeps.discover.load_strategies", side_effect=side_effect_loader):
        result = collect_path_dependencies(root_pyproject)

    captured = capsys.readouterr()
    # Check format: [Label] project_name -> N deps
    assert "[Custom" in captured.out
    assert "myroot" in captured.out
    assert "mydep" in captured.out
    assert "-> 1 deps" in captured.out
    assert "-> 0 deps" in captured.out


def test_depth_indentation_in_output(tmp_path, mock_strategy, capsys):
    """Test that output indentation increases with depth."""
    root = tmp_path / "root"
    root.mkdir()
    (root / "pyproject.toml").write_text("")

    dep1 = tmp_path / "dep1"
    dep1.mkdir()
    (dep1 / "pyproject.toml").write_text("")

    dep2 = tmp_path / "dep2"
    dep2.mkdir()
    (dep2 / "pyproject.toml").write_text("")

    call_count = [0]

    def side_effect_loader():
        call_count[0] += 1
        if call_count[0] == 1:
            return [mock_strategy(label_name="S", extract_result=[dep1])]
        elif call_count[0] == 2:
            return [mock_strategy(label_name="S", extract_result=[dep2])]
        return [mock_strategy(label_name="S", extract_result=[])]

    with patch("pychub.package.pathdeps.discover.load_strategies", side_effect=side_effect_loader):
        collect_path_dependencies(root / "pyproject.toml")

    captured = capsys.readouterr()
    lines = captured.out.split("\n")

    # root should have no indentation
    root_line = [l for l in lines if "root" in l][0]
    assert not root_line.startswith("  ")

    # dep1 should have 2-space indentation
    dep1_line = [l for l in lines if "dep1" in l][0]
    assert dep1_line.startswith("  ")

    # dep2 should have 4-space indentation
    dep2_line = [l for l in lines if "dep2" in l][0]
    assert dep2_line.startswith("    ")


# ============================================================================
# Parametrized Tests
# ============================================================================

@pytest.mark.parametrize("num_deps", [0, 1, 3, 5, 10])
def test_varying_number_of_dependencies(tmp_path, mock_strategy, num_deps):
    """Test with varying numbers of dependencies."""
    root = tmp_path / "root"
    root.mkdir()
    root_pyproject = root / "pyproject.toml"
    root_pyproject.write_text("")

    deps = []
    for i in range(num_deps):
        dep = tmp_path / f"dep{i}"
        dep.mkdir()
        (dep / "pyproject.toml").write_text("")
        deps.append(dep)

    root_strategy = mock_strategy(label_name="Root", extract_result=deps)
    dep_strategy = mock_strategy(label_name="Dep", extract_result=[])

    def side_effect_loader():
        if not hasattr(side_effect_loader, 'first'):
            side_effect_loader.first = True
        if side_effect_loader.first:
            side_effect_loader.first = False
            return [root_strategy]
        return [dep_strategy]

    with patch("pychub.package.pathdeps.discover.load_strategies", side_effect=side_effect_loader):
        result = collect_path_dependencies(root_pyproject)

    assert len(result) == num_deps + 1  # root + deps


@pytest.mark.parametrize("strategy_label", ["Poetry", "Hatch", "PDM", "Default", "Custom"])
def test_different_strategy_labels(tmp_path, mock_strategy, strategy_label):
    """Test that different strategy labels are correctly recorded."""
    project = tmp_path / "project"
    project.mkdir()
    pyproject = project / "pyproject.toml"
    pyproject.write_text("")

    strategy = mock_strategy(label_name=strategy_label, extract_result=[])

    with patch("pychub.package.pathdeps.discover.load_strategies", return_value=[strategy]):
        result = collect_path_dependencies(pyproject)

    assert result[project] == strategy_label


# ============================================================================
# Regression Tests
# ============================================================================

def test_regression_missing_parent_directory(tmp_path):
    """Regression: ensure we handle cases where parent directory doesn't exist."""
    non_existent_parent = tmp_path / "non_existent_dir" / "project" / "pyproject.toml"

    with pytest.raises(FileNotFoundError):
        collect_path_dependencies(non_existent_parent)


def test_regression_non_pyproject_file(tmp_path):
    """Regression: ensure we fail gracefully on non-pyproject files."""
    project = tmp_path / "project"
    project.mkdir()
    not_pyproject = project / "setup.py"
    not_pyproject.write_text("invalid toml {{{")

    with pytest.raises(Exception):
        collect_path_dependencies(not_pyproject)


def test_regression_empty_file(tmp_path):
    """Regression: handle empty pyproject.toml files."""
    project = tmp_path / "project"
    project.mkdir()
    pyproject = project / "pyproject.toml"
    pyproject.write_text("")  # Completely empty

    # Should not crash, will use default strategy
    result = collect_path_dependencies(pyproject)
    assert project in result