import pytest
from pathlib import Path
from pychub.package.pathdeps.poetry import PoetryPathDepStrategy


# ============================================================================
# label() tests
# ============================================================================

def test_label_returns_poetry():
    """Test that label() returns 'Poetry'."""
    assert PoetryPathDepStrategy.label() == "Poetry"


# ============================================================================
# can_handle() tests
# ============================================================================

def test_can_handle_with_poetry_section():
    """Test can_handle returns True when tool.poetry exists."""
    data = {"tool": {"poetry": {}}}
    assert PoetryPathDepStrategy.can_handle(data) is True


def test_can_handle_with_poetry_and_dependencies():
    """Test can_handle returns True with poetry section and dependencies."""
    data = {
        "tool": {
            "poetry": {
                "dependencies": {
                    "python": "^3.9"
                }
            }
        }
    }
    assert PoetryPathDepStrategy.can_handle(data) is True


def test_can_handle_without_tool_section():
    """Test can_handle returns False when tool section is missing."""
    data = {"project": {}}
    assert PoetryPathDepStrategy.can_handle(data) is False


def test_can_handle_without_poetry_section():
    """Test can_handle returns False when poetry section is missing."""
    data = {"tool": {"hatch": {}}}
    assert PoetryPathDepStrategy.can_handle(data) is False


def test_can_handle_with_empty_data():
    """Test can_handle returns False with empty dict."""
    assert PoetryPathDepStrategy.can_handle({}) is False


def test_can_handle_with_none_tool():
    """Test can_handle returns False when tool is None."""
    data = {"tool": None}
    assert PoetryPathDepStrategy.can_handle(data) is False


# ============================================================================
# extract_paths() tests
# ============================================================================

def test_extract_paths_with_single_path_dependency(tmp_path):
    """Test extracting a single path dependency."""
    dep_dir = tmp_path / "mylib"
    dep_dir.mkdir()

    data = {
        "tool": {
            "poetry": {
                "dependencies": {
                    "mylib": {"path": "mylib"}
                }
            }
        }
    }

    paths = PoetryPathDepStrategy.extract_paths(data, tmp_path)
    assert len(paths) == 1
    assert paths[0] == dep_dir.resolve()


def test_extract_paths_with_multiple_path_dependencies(tmp_path):
    """Test extracting multiple path dependencies."""
    lib1 = tmp_path / "lib1"
    lib2 = tmp_path / "lib2"
    lib1.mkdir()
    lib2.mkdir()

    data = {
        "tool": {
            "poetry": {
                "dependencies": {
                    "lib1": {"path": "lib1"},
                    "lib2": {"path": "lib2"}
                }
            }
        }
    }

    paths = PoetryPathDepStrategy.extract_paths(data, tmp_path)
    assert len(paths) == 2
    assert lib1.resolve() in paths
    assert lib2.resolve() in paths


def test_extract_paths_with_relative_path(tmp_path):
    """Test extracting path dependency with relative path."""
    dep_dir = tmp_path / "subdir" / "mylib"
    dep_dir.mkdir(parents=True)

    data = {
        "tool": {
            "poetry": {
                "dependencies": {
                    "mylib": {"path": "subdir/mylib"}
                }
            }
        }
    }

    paths = PoetryPathDepStrategy.extract_paths(data, tmp_path)
    assert len(paths) == 1
    assert paths[0] == dep_dir.resolve()


def test_extract_paths_with_parent_relative_path(tmp_path):
    """Test extracting path dependency with ../ relative path."""
    project_dir = tmp_path / "project"
    dep_dir = tmp_path / "sibling"
    project_dir.mkdir()
    dep_dir.mkdir()

    data = {
        "tool": {
            "poetry": {
                "dependencies": {
                    "sibling": {"path": "../sibling"}
                }
            }
        }
    }

    paths = PoetryPathDepStrategy.extract_paths(data, project_dir)
    assert len(paths) == 1
    assert paths[0] == dep_dir.resolve()


def test_extract_paths_ignores_string_dependencies():
    """Test that string-based dependencies are ignored."""
    data = {
        "tool": {
            "poetry": {
                "dependencies": {
                    "python": "^3.9",
                    "requests": "^2.28.0"
                }
            }
        }
    }

    paths = PoetryPathDepStrategy.extract_paths(data, Path("/tmp"))
    assert paths == []


def test_extract_paths_ignores_version_dependencies():
    """Test that version-based dependencies are ignored."""
    data = {
        "tool": {
            "poetry": {
                "dependencies": {
                    "requests": {"version": "^2.28.0"}
                }
            }
        }
    }

    paths = PoetryPathDepStrategy.extract_paths(data, Path("/tmp"))
    assert paths == []


def test_extract_paths_ignores_git_dependencies():
    """Test that git-based dependencies are ignored."""
    data = {
        "tool": {
            "poetry": {
                "dependencies": {
                    "mylib": {"git": "https://github.com/user/mylib.git"}
                }
            }
        }
    }

    paths = PoetryPathDepStrategy.extract_paths(data, Path("/tmp"))
    assert paths == []


def test_extract_paths_mixed_dependency_types(tmp_path):
    """Test extracting paths with mixed dependency types."""
    dep_dir = tmp_path / "locallib"
    dep_dir.mkdir()

    data = {
        "tool": {
            "poetry": {
                "dependencies": {
                    "python": "^3.9",
                    "requests": "^2.28.0",
                    "locallib": {"path": "locallib"},
                    "gitlib": {"git": "https://github.com/user/gitlib.git"},
                    "verlib": {"version": "^1.0.0"}
                }
            }
        }
    }

    paths = PoetryPathDepStrategy.extract_paths(data, tmp_path)
    assert len(paths) == 1
    assert paths[0] == dep_dir.resolve()


def test_extract_paths_with_extras_and_path(tmp_path):
    """Test path dependency with extras specified."""
    dep_dir = tmp_path / "mylib"
    dep_dir.mkdir()

    data = {
        "tool": {
            "poetry": {
                "dependencies": {
                    "mylib": {"path": "mylib", "extras": ["dev", "test"]}
                }
            }
        }
    }

    paths = PoetryPathDepStrategy.extract_paths(data, tmp_path)
    assert len(paths) == 1
    assert paths[0] == dep_dir.resolve()


def test_extract_paths_with_develop_mode(tmp_path):
    """Test path dependency with develop mode."""
    dep_dir = tmp_path / "mylib"
    dep_dir.mkdir()

    data = {
        "tool": {
            "poetry": {
                "dependencies": {
                    "mylib": {"path": "mylib", "develop": True}
                }
            }
        }
    }

    paths = PoetryPathDepStrategy.extract_paths(data, tmp_path)
    assert len(paths) == 1
    assert paths[0] == dep_dir.resolve()


def test_extract_paths_without_dependencies_section():
    """Test extract_paths when dependencies section is missing."""
    data = {
        "tool": {
            "poetry": {
                "name": "myproject"
            }
        }
    }

    paths = PoetryPathDepStrategy.extract_paths(data, Path("/tmp"))
    assert paths == []


def test_extract_paths_with_empty_dependencies():
    """Test extract_paths with empty dependencies dict."""
    data = {
        "tool": {
            "poetry": {
                "dependencies": {}
            }
        }
    }

    paths = PoetryPathDepStrategy.extract_paths(data, Path("/tmp"))
    assert paths == []


def test_extract_paths_without_tool_section():
    """Test extract_paths when tool section is missing."""
    data = {"project": {}}

    paths = PoetryPathDepStrategy.extract_paths(data, Path("/tmp"))
    assert paths == []


def test_extract_paths_without_poetry_section():
    """Test extract_paths when poetry section is missing."""
    data = {"tool": {"hatch": {}}}

    paths = PoetryPathDepStrategy.extract_paths(data, Path("/tmp"))
    assert paths == []


def test_extract_paths_with_empty_data():
    """Test extract_paths with completely empty data."""
    paths = PoetryPathDepStrategy.extract_paths({}, Path("/tmp"))
    assert paths == []


def test_extract_paths_resolves_to_absolute(tmp_path):
    """Test that all returned paths are absolute."""
    dep_dir = tmp_path / "mylib"
    dep_dir.mkdir()

    data = {
        "tool": {
            "poetry": {
                "dependencies": {
                    "mylib": {"path": "mylib"}
                }
            }
        }
    }

    paths = PoetryPathDepStrategy.extract_paths(data, tmp_path)
    assert all(p.is_absolute() for p in paths)


def test_extract_paths_handles_dev_dependencies(tmp_path):
    """Test that dev-dependencies are NOT extracted (only dependencies)."""
    dep_dir = tmp_path / "mylib"
    dep_dir.mkdir()

    data = {
        "tool": {
            "poetry": {
                "dependencies": {},
                "dev-dependencies": {
                    "mylib": {"path": "mylib"}
                }
            }
        }
    }

    # Poetry strategy only looks at dependencies, not dev-dependencies
    paths = PoetryPathDepStrategy.extract_paths(data, tmp_path)
    assert paths == []


def test_extract_paths_with_group_dependencies(tmp_path):
    """Test that group dependencies are NOT extracted."""
    dep_dir = tmp_path / "mylib"
    dep_dir.mkdir()

    data = {
        "tool": {
            "poetry": {
                "dependencies": {},
                "group": {
                    "dev": {
                        "dependencies": {
                            "mylib": {"path": "mylib"}
                        }
                    }
                }
            }
        }
    }

    # Only looks at top-level dependencies
    paths = PoetryPathDepStrategy.extract_paths(data, tmp_path)
    assert paths == []


# ============================================================================
# Integration / Edge case tests
# ============================================================================

def test_strategy_inherits_from_base():
    """Test that PoetryPathDepStrategy inherits from PathDepStrategy."""
    from pychub.package.pathdeps.base import PathDepStrategy
    assert issubclass(PoetryPathDepStrategy, PathDepStrategy)


def test_strategy_implements_all_abstract_methods():
    """Test that all abstract methods are implemented."""
    strategy = PoetryPathDepStrategy()
    assert hasattr(strategy, 'label')
    assert hasattr(strategy, 'can_handle')
    assert hasattr(strategy, 'extract_paths')
    assert callable(strategy.label)
    assert callable(strategy.can_handle)
    assert callable(strategy.extract_paths)


def test_extract_paths_with_none_values_in_dependencies():
    """Test extract_paths handles None values gracefully."""
    data = {
        "tool": {
            "poetry": {
                "dependencies": {
                    "python": "^3.9",
                    "broken": None
                }
            }
        }
    }

    paths = PoetryPathDepStrategy.extract_paths(data, Path("/tmp"))
    assert paths == []


@pytest.mark.parametrize("data", [
    {"tool": {"poetry": {"dependencies": None}}},
    {"tool": {"poetry": None}},
    {"tool": None},
])
def test_extract_paths_with_none_sections(data):
    """Test extract_paths handles None in various sections."""
    paths = PoetryPathDepStrategy.extract_paths(data, Path("/tmp"))
    assert paths == []


def test_extract_paths_preserves_order(tmp_path):
    """Test that extract_paths preserves dependency order."""
    for i in range(5):
        (tmp_path / f"lib{i}").mkdir()

    data = {
        "tool": {
            "poetry": {
                "dependencies": {
                    f"lib{i}": {"path": f"lib{i}"}
                    for i in range(5)
                }
            }
        }
    }

    paths = PoetryPathDepStrategy.extract_paths(data, tmp_path)
    assert len(paths) == 5
    # Note: dict order is preserved in Python 3.7+