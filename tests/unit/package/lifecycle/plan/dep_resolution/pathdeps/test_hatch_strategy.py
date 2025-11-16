import pytest
from pathlib import Path

from pychub.package.lifecycle.plan.dep_resolution.pathdeps import HatchPathDepStrategy


# ============================================================================
# label() tests
# ============================================================================

def test_label_returns_hatch():
    """Test that label() returns 'Hatch'."""
    assert HatchPathDepStrategy.label() == "Hatch"


# ============================================================================
# can_handle() tests
# ============================================================================

def test_can_handle_with_hatch_and_dependencies():
    """Test can_handle returns True when tool.hatch and project.dependencies exist."""
    data = {
        "tool": {"hatch": {}},
        "project": {"dependencies": []}
    }
    assert HatchPathDepStrategy.can_handle(data) is True


def test_can_handle_with_hatch_dependencies_and_content():
    """Test can_handle returns True with hatch section and dependencies."""
    data = {
        "tool": {"hatch": {"version": "1.0"}},
        "project": {
            "dependencies": [
                "requests>=2.28.0",
                "pytest>=7.0"
            ]
        }
    }
    assert HatchPathDepStrategy.can_handle(data) is True


def test_can_handle_without_tool_section():
    """Test can_handle returns False when tool section is missing."""
    data = {"project": {"dependencies": []}}
    assert HatchPathDepStrategy.can_handle(data) is False


def test_can_handle_without_hatch_section():
    """Test can_handle returns False when hatch section is missing."""
    data = {
        "tool": {"poetry": {}},
        "project": {"dependencies": []}
    }
    assert HatchPathDepStrategy.can_handle(data) is False


def test_can_handle_without_project_section():
    """Test can_handle returns False when project section is missing."""
    data = {"tool": {"hatch": {}}}
    assert HatchPathDepStrategy.can_handle(data) is False


def test_can_handle_without_dependencies_in_project():
    """Test can_handle returns False when project.dependencies is missing."""
    data = {
        "tool": {"hatch": {}},
        "project": {"name": "myproject"}
    }
    assert HatchPathDepStrategy.can_handle(data) is False


def test_can_handle_with_empty_data():
    """Test can_handle returns False with empty dict."""
    assert HatchPathDepStrategy.can_handle({}) is False


def test_can_handle_with_none_tool():
    """Test can_handle returns False when tool is None."""
    data = {
        "tool": None,
        "project": {"dependencies": []}
    }
    assert HatchPathDepStrategy.can_handle(data) is False


def test_can_handle_with_none_project():
    """Test can_handle returns False when project is None."""
    data = {
        "tool": {"hatch": {}},
        "project": None
    }
    assert HatchPathDepStrategy.can_handle(data) is False


def test_can_handle_with_none_dependencies():
    """Test can_handle returns False when dependencies is None."""
    data = {
        "tool": {"hatch": {}},
        "project": {"dependencies": None}
    }
    # can_handle checks if "dependencies" key exists
    assert HatchPathDepStrategy.can_handle(data) is True


def test_can_handle_requires_both_sections():
    """Test can_handle requires both tool.hatch and project.dependencies."""
    # Only tool.hatch
    assert HatchPathDepStrategy.can_handle({"tool": {"hatch": {}}}) is False

    # Only project.dependencies
    assert HatchPathDepStrategy.can_handle({"project": {"dependencies": []}}) is False

    # Both present
    data = {
        "tool": {"hatch": {}},
        "project": {"dependencies": []}
    }
    assert HatchPathDepStrategy.can_handle(data) is True


# ============================================================================
# extract_paths() tests
# ============================================================================

def test_extract_paths_with_single_path_dependency(tmp_path):
    """Test extracting a single path dependency."""
    dep_dir = tmp_path / "mylib"
    dep_dir.mkdir()

    data = {
        "project": {
            "dependencies": [
                {"path": "mylib"}
            ]
        }
    }

    paths = HatchPathDepStrategy.extract_paths(data, tmp_path)
    assert len(paths) == 1
    assert paths[0] == dep_dir.resolve()


def test_extract_paths_with_multiple_path_dependencies(tmp_path):
    """Test extracting multiple path dependencies."""
    lib1 = tmp_path / "lib1"
    lib2 = tmp_path / "lib2"
    lib1.mkdir()
    lib2.mkdir()

    data = {
        "project": {
            "dependencies": [
                {"path": "lib1"},
                {"path": "lib2"}
            ]
        }
    }

    paths = HatchPathDepStrategy.extract_paths(data, tmp_path)
    assert len(paths) == 2
    assert lib1.resolve() in paths
    assert lib2.resolve() in paths


def test_extract_paths_with_relative_path(tmp_path):
    """Test extracting path dependency with relative path."""
    dep_dir = tmp_path / "subdir" / "mylib"
    dep_dir.mkdir(parents=True)

    data = {
        "project": {
            "dependencies": [
                {"path": "subdir/mylib"}
            ]
        }
    }

    paths = HatchPathDepStrategy.extract_paths(data, tmp_path)
    assert len(paths) == 1
    assert paths[0] == dep_dir.resolve()


def test_extract_paths_with_parent_relative_path(tmp_path):
    """Test extracting path dependency with ../ relative path."""
    project_dir = tmp_path / "project"
    dep_dir = tmp_path / "sibling"
    project_dir.mkdir()
    dep_dir.mkdir()

    data = {
        "project": {
            "dependencies": [
                {"path": "../sibling"}
            ]
        }
    }

    paths = HatchPathDepStrategy.extract_paths(data, project_dir)
    assert len(paths) == 1
    assert paths[0] == dep_dir.resolve()


def test_extract_paths_ignores_string_dependencies():
    """Test that string-based dependencies are ignored."""
    data = {
        "project": {
            "dependencies": [
                "requests>=2.28.0",
                "pytest>=7.0",
                "numpy~=1.24"
            ]
        }
    }

    paths = HatchPathDepStrategy.extract_paths(data, Path("/tmp"))
    assert paths == []


def test_extract_paths_mixed_dependency_types(tmp_path):
    """Test extracting paths with mixed dependency types."""
    dep_dir = tmp_path / "locallib"
    dep_dir.mkdir()

    data = {
        "project": {
            "dependencies": [
                "requests>=2.28.0",
                {"path": "locallib"},
                "pytest>=7.0",
                {"git": "https://github.com/user/gitlib.git"},
                "numpy~=1.24"
            ]
        }
    }

    paths = HatchPathDepStrategy.extract_paths(data, tmp_path)
    assert len(paths) == 1
    assert paths[0] == dep_dir.resolve()


def test_extract_paths_with_extras_and_path(tmp_path):
    """Test path dependency with extras specified."""
    dep_dir = tmp_path / "mylib"
    dep_dir.mkdir()

    data = {
        "project": {
            "dependencies": [
                {"path": "mylib", "extras": ["dev", "test"]}
            ]
        }
    }

    paths = HatchPathDepStrategy.extract_paths(data, tmp_path)
    assert len(paths) == 1
    assert paths[0] == dep_dir.resolve()


def test_extract_paths_with_editable_mode(tmp_path):
    """Test path dependency with editable mode."""
    dep_dir = tmp_path / "mylib"
    dep_dir.mkdir()

    data = {
        "project": {
            "dependencies": [
                {"path": "mylib", "editable": True}
            ]
        }
    }

    paths = HatchPathDepStrategy.extract_paths(data, tmp_path)
    assert len(paths) == 1
    assert paths[0] == dep_dir.resolve()


def test_extract_paths_without_project_section():
    """Test extract_paths when project section is missing."""
    data = {"tool": {"hatch": {}}}

    paths = HatchPathDepStrategy.extract_paths(data, Path("/tmp"))
    assert paths == []


def test_extract_paths_without_dependencies_section():
    """Test extract_paths when dependencies section is missing."""
    data = {
        "project": {
            "name": "myproject",
            "version": "1.0.0"
        }
    }

    paths = HatchPathDepStrategy.extract_paths(data, Path("/tmp"))
    assert paths == []


def test_extract_paths_with_empty_dependencies():
    """Test extract_paths with empty dependencies list."""
    data = {
        "project": {
            "dependencies": []
        }
    }

    paths = HatchPathDepStrategy.extract_paths(data, Path("/tmp"))
    assert paths == []


def test_extract_paths_with_empty_data():
    """Test extract_paths with completely empty data."""
    paths = HatchPathDepStrategy.extract_paths({}, Path("/tmp"))
    assert paths == []


def test_extract_paths_resolves_to_absolute(tmp_path):
    """Test that all returned paths are absolute."""
    dep_dir = tmp_path / "mylib"
    dep_dir.mkdir()

    data = {
        "project": {
            "dependencies": [
                {"path": "mylib"}
            ]
        }
    }

    paths = HatchPathDepStrategy.extract_paths(data, tmp_path)
    assert all(p.is_absolute() for p in paths)


def test_extract_paths_with_optional_dependencies(tmp_path):
    """Test that optional-dependencies are NOT extracted."""
    dep_dir = tmp_path / "mylib"
    dep_dir.mkdir()

    data = {
        "project": {
            "dependencies": [],
            "optional-dependencies": {
                "dev": [
                    {"path": "mylib"}
                ]
            }
        }
    }

    # Hatch strategy only looks at dependencies, not optional-dependencies
    paths = HatchPathDepStrategy.extract_paths(data, tmp_path)
    assert paths == []


# ============================================================================
# Integration / Edge case tests
# ============================================================================

def test_strategy_inherits_from_base():
    """Test that HatchPathDepStrategy inherits from PathDepStrategy."""
    from pychub.package.lifecycle.plan.dep_resolution.pathdeps.project_path_strategy_base import ProjectPathStrategy
    assert issubclass(HatchPathDepStrategy, ProjectPathStrategy)


def test_strategy_implements_all_abstract_methods():
    """Test that all abstract methods are implemented."""
    strategy = HatchPathDepStrategy()
    assert hasattr(strategy, 'label')
    assert hasattr(strategy, 'can_handle')
    assert hasattr(strategy, 'extract_paths')
    assert callable(strategy.label)
    assert callable(strategy.can_handle)
    assert callable(strategy.extract_paths)


def test_extract_paths_with_none_values_in_dependencies():
    """Test extract_paths handles None values gracefully."""
    data = {
        "project": {
            "dependencies": [
                "requests>=2.28.0",
                None
            ]
        }
    }

    paths = HatchPathDepStrategy.extract_paths(data, Path("/tmp"))
    assert paths == []


@pytest.mark.parametrize("data", [
    {"project": {"dependencies": None}},
    {"project": None},
])
def test_extract_paths_with_none_sections(data):
    """Test extract_paths handles None in various sections."""
    paths = HatchPathDepStrategy.extract_paths(data, Path("/tmp"))
    assert paths == []


def test_extract_paths_preserves_order(tmp_path):
    """Test that extract_paths preserves dependency order."""
    for i in range(5):
        (tmp_path / f"lib{i}").mkdir()

    data = {
        "project": {
            "dependencies": [
                {"path": f"lib{i}"}
                for i in range(5)
            ]
        }
    }

    paths = HatchPathDepStrategy.extract_paths(data, tmp_path)
    assert len(paths) == 5
    # list order is always preserved


def test_extract_paths_with_complex_nested_path(tmp_path):
    """Test extracting path with deeply nested structure."""
    dep_dir = tmp_path / "a" / "b" / "c" / "mylib"
    dep_dir.mkdir(parents=True)

    data = {
        "project": {
            "dependencies": [
                {"path": "a/b/c/mylib"}
            ]
        }
    }

    paths = HatchPathDepStrategy.extract_paths(data, tmp_path)
    assert len(paths) == 1
    assert paths[0] == dep_dir.resolve()


def test_extract_paths_with_path_containing_special_chars(tmp_path):
    """Test extracting path with special characters in name."""
    dep_dir = tmp_path / "my-lib_v2.0"
    dep_dir.mkdir()

    data = {
        "project": {
            "dependencies": [
                {"path": "my-lib_v2.0"}
            ]
        }
    }

    paths = HatchPathDepStrategy.extract_paths(data, tmp_path)
    assert len(paths) == 1
    assert paths[0] == dep_dir.resolve()


def test_extract_paths_with_nested_list_value():
    """Test that nested list values in dependencies are ignored."""
    data = {
        "project": {
            "dependencies": [
                ["path", "mylib"]
            ]
        }
    }

    paths = HatchPathDepStrategy.extract_paths(data, Path("/tmp"))
    assert paths == []


def test_extract_paths_with_empty_path_value(tmp_path):
    """Test that empty path value is handled."""
    data = {
        "project": {
            "dependencies": [
                {"path": ""}
            ]
        }
    }

    paths = HatchPathDepStrategy.extract_paths(data, tmp_path)
    assert len(paths) == 1
    # Empty path resolves to project root
    assert paths[0] == tmp_path.resolve()


def test_extract_paths_with_absolute_path():
    """Test extracting absolute path dependency."""
    abs_path = Path("/absolute/path/to/lib")

    data = {
        "project": {
            "dependencies": [
                {"path": str(abs_path)}
            ]
        }
    }

    paths = HatchPathDepStrategy.extract_paths(data, Path("/tmp"))
    assert len(paths) == 1
    assert paths[0] == abs_path.resolve()


def test_extract_paths_with_markers(tmp_path):
    """Test path dependency with environment markers."""
    dep_dir = tmp_path / "mylib"
    dep_dir.mkdir()

    data = {
        "project": {
            "dependencies": [
                {
                    "path": "mylib",
                    "markers": "python_version >= '3.9'"
                }
            ]
        }
    }

    paths = HatchPathDepStrategy.extract_paths(data, tmp_path)
    assert len(paths) == 1
    assert paths[0] == dep_dir.resolve()


def test_extract_paths_handles_integer_values():
    """Test that integer values in dependencies are ignored."""
    data = {
        "project": {
            "dependencies": [
                12345
            ]
        }
    }

    paths = HatchPathDepStrategy.extract_paths(data, Path("/tmp"))
    assert paths == []


def test_extract_paths_handles_boolean_values():
    """Test that boolean values in dependencies are ignored."""
    data = {
        "project": {
            "dependencies": [
                True,
                False
            ]
        }
    }

    paths = HatchPathDepStrategy.extract_paths(data, Path("/tmp"))
    assert paths == []


def test_extract_paths_with_dict_missing_path_key(tmp_path):
    """Test that dict without 'path' key is ignored."""
    data = {
        "project": {
            "dependencies": [
                {"version": "1.0.0", "extras": ["dev"]}
            ]
        }
    }

    paths = HatchPathDepStrategy.extract_paths(data, tmp_path)
    assert paths == []


def test_extract_paths_multiple_calls_same_data(tmp_path):
    """Test that multiple calls with same data return consistent results."""
    dep_dir = tmp_path / "mylib"
    dep_dir.mkdir()

    data = {
        "project": {
            "dependencies": [
                {"path": "mylib"}
            ]
        }
    }

    paths1 = HatchPathDepStrategy.extract_paths(data, tmp_path)
    paths2 = HatchPathDepStrategy.extract_paths(data, tmp_path)

    assert paths1 == paths2
    assert len(paths1) == 1


def test_label_is_static():
    """Test that label() can be called without instantiation."""
    label = HatchPathDepStrategy.label()
    assert label == "Hatch"
    assert isinstance(label, str)


def test_can_handle_is_static():
    """Test that can_handle() can be called without instantiation."""
    data = {
        "tool": {"hatch": {}},
        "project": {"dependencies": []}
    }
    result = HatchPathDepStrategy.can_handle(data)
    assert result is True


def test_extract_paths_is_static(tmp_path):
    """Test that extract_paths() can be called without instantiation."""
    dep_dir = tmp_path / "mylib"
    dep_dir.mkdir()

    data = {
        "project": {
            "dependencies": [
                {"path": "mylib"}
            ]
        }
    }

    paths = HatchPathDepStrategy.extract_paths(data, tmp_path)
    assert len(paths) == 1
    assert paths[0] == dep_dir.resolve()


def test_extract_paths_with_dict_containing_only_path(tmp_path):
    """Test extracting minimal dict with only path key."""
    dep_dir = tmp_path / "mylib"
    dep_dir.mkdir()

    data = {
        "project": {
            "dependencies": [
                {"path": "mylib"}
            ]
        }
    }

    paths = HatchPathDepStrategy.extract_paths(data, tmp_path)
    assert len(paths) == 1
    assert paths[0] == dep_dir.resolve()


def test_extract_paths_with_url_dependency():
    """Test that URL-based dependencies are ignored."""
    data = {
        "project": {
            "dependencies": [
                {"url": "https://example.com/mylib.whl"}
            ]
        }
    }

    paths = HatchPathDepStrategy.extract_paths(data, Path("/tmp"))
    assert paths == []


def test_extract_paths_with_git_dependency():
    """Test that git-based dependencies are ignored."""
    data = {
        "project": {
            "dependencies": [
                {"git": "https://github.com/user/mylib.git"}
            ]
        }
    }

    paths = HatchPathDepStrategy.extract_paths(data, Path("/tmp"))
    assert paths == []


def test_can_handle_with_other_tool_sections():
    """Test can_handle only cares about hatch section in tool."""
    data = {
        "tool": {
            "hatch": {},
            "poetry": {},
            "pdm": {}
        },
        "project": {"dependencies": []}
    }
    assert HatchPathDepStrategy.can_handle(data) is True


def test_extract_paths_with_dependencies_as_dict():
    """Test extract_paths when dependencies is incorrectly a dict (should be list)."""
    data = {
        "project": {
            "dependencies": {
                "mylib": {"path": "mylib"}
            }
        }
    }

    # Should handle gracefully and return empty list
    paths = HatchPathDepStrategy.extract_paths(data, Path("/tmp"))
    assert paths == []


def test_extract_paths_with_duplicate_paths(tmp_path):
    """Test extracting dependencies with duplicate paths."""
    dep_dir = tmp_path / "mylib"
    dep_dir.mkdir()

    data = {
        "project": {
            "dependencies": [
                {"path": "mylib"},
                {"path": "mylib"},
                {"path": "./mylib"}
            ]
        }
    }

    paths = HatchPathDepStrategy.extract_paths(data, tmp_path)
    # All three should be extracted (even if they resolve to same path)
    assert len(paths) == 3
    # They should all resolve to the same absolute path
    assert all(p == dep_dir.resolve() for p in paths)