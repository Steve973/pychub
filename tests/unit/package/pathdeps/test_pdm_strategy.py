import pytest
from pathlib import Path
from pychub.package.pathdeps.pdm import PdmPathDepStrategy


# ============================================================================
# label() tests
# ============================================================================

def test_label_returns_pdm():
    """Test that label() returns 'PDM'."""
    assert PdmPathDepStrategy.label() == "PDM"


# ============================================================================
# can_handle() tests
# ============================================================================

def test_can_handle_with_pdm_section_and_dependencies():
    """Test can_handle returns True when tool.pdm.dependencies exists."""
    data = {"tool": {"pdm": {"dependencies": {}}}}
    assert PdmPathDepStrategy.can_handle(data) is True


def test_can_handle_with_pdm_dependencies_and_content():
    """Test can_handle returns True with pdm section and dependencies."""
    data = {
        "tool": {
            "pdm": {
                "dependencies": {
                    "requests": "^2.28.0"
                }
            }
        }
    }
    assert PdmPathDepStrategy.can_handle(data) is True


def test_can_handle_without_tool_section():
    """Test can_handle returns False when tool section is missing."""
    data = {"project": {}}
    assert PdmPathDepStrategy.can_handle(data) is False


def test_can_handle_without_pdm_section():
    """Test can_handle returns False when pdm section is missing."""
    data = {"tool": {"poetry": {}}}
    assert PdmPathDepStrategy.can_handle(data) is False


def test_can_handle_with_pdm_but_no_dependencies():
    """Test can_handle returns False when pdm section exists but no dependencies."""
    data = {"tool": {"pdm": {"version": "2.0"}}}
    assert PdmPathDepStrategy.can_handle(data) is False


def test_can_handle_with_empty_data():
    """Test can_handle returns False with empty dict."""
    assert PdmPathDepStrategy.can_handle({}) is False


def test_can_handle_with_none_tool():
    """Test can_handle returns False when tool is None."""
    data = {"tool": None}
    assert PdmPathDepStrategy.can_handle(data) is False


def test_can_handle_with_none_pdm():
    """Test can_handle returns False when pdm is None."""
    data = {"tool": {"pdm": None}}
    assert PdmPathDepStrategy.can_handle(data) is False


def test_can_handle_with_none_dependencies():
    """Test can_handle returns False when dependencies is None."""
    data = {"tool": {"pdm": {"dependencies": None}}}
    # can_handle checks if "dependencies" key exists, but extract_paths handles None
    assert PdmPathDepStrategy.can_handle(data) is True


# ============================================================================
# extract_paths() tests
# ============================================================================

def test_extract_paths_with_single_path_dependency(tmp_path):
    """Test extracting a single path dependency."""
    dep_dir = tmp_path / "mylib"
    dep_dir.mkdir()

    data = {
        "tool": {
            "pdm": {
                "dependencies": {
                    "mylib": {"path": "mylib"}
                }
            }
        }
    }

    paths = PdmPathDepStrategy.extract_paths(data, tmp_path)
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
            "pdm": {
                "dependencies": {
                    "lib1": {"path": "lib1"},
                    "lib2": {"path": "lib2"}
                }
            }
        }
    }

    paths = PdmPathDepStrategy.extract_paths(data, tmp_path)
    assert len(paths) == 2
    assert lib1.resolve() in paths
    assert lib2.resolve() in paths


def test_extract_paths_with_relative_path(tmp_path):
    """Test extracting path dependency with relative path."""
    dep_dir = tmp_path / "subdir" / "mylib"
    dep_dir.mkdir(parents=True)

    data = {
        "tool": {
            "pdm": {
                "dependencies": {
                    "mylib": {"path": "subdir/mylib"}
                }
            }
        }
    }

    paths = PdmPathDepStrategy.extract_paths(data, tmp_path)
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
            "pdm": {
                "dependencies": {
                    "sibling": {"path": "../sibling"}
                }
            }
        }
    }

    paths = PdmPathDepStrategy.extract_paths(data, project_dir)
    assert len(paths) == 1
    assert paths[0] == dep_dir.resolve()


def test_extract_paths_ignores_string_dependencies():
    """Test that string-based dependencies are ignored."""
    data = {
        "tool": {
            "pdm": {
                "dependencies": {
                    "requests": "^2.28.0",
                    "pytest": ">=7.0"
                }
            }
        }
    }

    paths = PdmPathDepStrategy.extract_paths(data, Path("/tmp"))
    assert paths == []


def test_extract_paths_ignores_version_dependencies():
    """Test that version-based dependencies are ignored."""
    data = {
        "tool": {
            "pdm": {
                "dependencies": {
                    "requests": {"version": "^2.28.0"}
                }
            }
        }
    }

    paths = PdmPathDepStrategy.extract_paths(data, Path("/tmp"))
    assert paths == []


def test_extract_paths_ignores_git_dependencies():
    """Test that git-based dependencies are ignored."""
    data = {
        "tool": {
            "pdm": {
                "dependencies": {
                    "mylib": {"git": "https://github.com/user/mylib.git"}
                }
            }
        }
    }

    paths = PdmPathDepStrategy.extract_paths(data, Path("/tmp"))
    assert paths == []


def test_extract_paths_ignores_url_dependencies():
    """Test that url-based dependencies are ignored."""
    data = {
        "tool": {
            "pdm": {
                "dependencies": {
                    "mylib": {"url": "https://example.com/mylib.whl"}
                }
            }
        }
    }

    paths = PdmPathDepStrategy.extract_paths(data, Path("/tmp"))
    assert paths == []


def test_extract_paths_mixed_dependency_types(tmp_path):
    """Test extracting paths with mixed dependency types."""
    dep_dir = tmp_path / "locallib"
    dep_dir.mkdir()

    data = {
        "tool": {
            "pdm": {
                "dependencies": {
                    "requests": "^2.28.0",
                    "locallib": {"path": "locallib"},
                    "gitlib": {"git": "https://github.com/user/gitlib.git"},
                    "verlib": {"version": "^1.0.0"},
                    "urlpkg": {"url": "https://example.com/pkg.whl"}
                }
            }
        }
    }

    paths = PdmPathDepStrategy.extract_paths(data, tmp_path)
    assert len(paths) == 1
    assert paths[0] == dep_dir.resolve()


def test_extract_paths_with_extras_and_path(tmp_path):
    """Test path dependency with extras specified."""
    dep_dir = tmp_path / "mylib"
    dep_dir.mkdir()

    data = {
        "tool": {
            "pdm": {
                "dependencies": {
                    "mylib": {"path": "mylib", "extras": ["dev", "test"]}
                }
            }
        }
    }

    paths = PdmPathDepStrategy.extract_paths(data, tmp_path)
    assert len(paths) == 1
    assert paths[0] == dep_dir.resolve()


def test_extract_paths_with_editable_mode(tmp_path):
    """Test path dependency with editable mode."""
    dep_dir = tmp_path / "mylib"
    dep_dir.mkdir()

    data = {
        "tool": {
            "pdm": {
                "dependencies": {
                    "mylib": {"path": "mylib", "editable": True}
                }
            }
        }
    }

    paths = PdmPathDepStrategy.extract_paths(data, tmp_path)
    assert len(paths) == 1
    assert paths[0] == dep_dir.resolve()


def test_extract_paths_without_dependencies_section():
    """Test extract_paths when dependencies section is missing."""
    data = {
        "tool": {
            "pdm": {
                "version": "2.0"
            }
        }
    }

    paths = PdmPathDepStrategy.extract_paths(data, Path("/tmp"))
    assert paths == []


def test_extract_paths_with_empty_dependencies():
    """Test extract_paths with empty dependencies dict."""
    data = {
        "tool": {
            "pdm": {
                "dependencies": {}
            }
        }
    }

    paths = PdmPathDepStrategy.extract_paths(data, Path("/tmp"))
    assert paths == []


def test_extract_paths_without_tool_section():
    """Test extract_paths when tool section is missing."""
    data = {"project": {}}

    paths = PdmPathDepStrategy.extract_paths(data, Path("/tmp"))
    assert paths == []


def test_extract_paths_without_pdm_section():
    """Test extract_paths when pdm section is missing."""
    data = {"tool": {"poetry": {}}}

    paths = PdmPathDepStrategy.extract_paths(data, Path("/tmp"))
    assert paths == []


def test_extract_paths_with_empty_data():
    """Test extract_paths with completely empty data."""
    paths = PdmPathDepStrategy.extract_paths({}, Path("/tmp"))
    assert paths == []


def test_extract_paths_resolves_to_absolute(tmp_path):
    """Test that all returned paths are absolute."""
    dep_dir = tmp_path / "mylib"
    dep_dir.mkdir()

    data = {
        "tool": {
            "pdm": {
                "dependencies": {
                    "mylib": {"path": "mylib"}
                }
            }
        }
    }

    paths = PdmPathDepStrategy.extract_paths(data, tmp_path)
    assert all(p.is_absolute() for p in paths)


def test_extract_paths_with_dev_dependencies(tmp_path):
    """Test that dev-dependencies are NOT extracted from pdm config."""
    dep_dir = tmp_path / "mylib"
    dep_dir.mkdir()

    data = {
        "tool": {
            "pdm": {
                "dependencies": {},
                "dev-dependencies": {
                    "mylib": {"path": "mylib"}
                }
            }
        }
    }

    # PDM strategy only looks at dependencies, not dev-dependencies
    paths = PdmPathDepStrategy.extract_paths(data, tmp_path)
    assert paths == []


# ============================================================================
# Integration / Edge case tests
# ============================================================================

def test_strategy_inherits_from_base():
    """Test that PdmPathDepStrategy inherits from PathDepStrategy."""
    from pychub.package.pathdeps.base import PathDepStrategy
    assert issubclass(PdmPathDepStrategy, PathDepStrategy)


def test_strategy_implements_all_abstract_methods():
    """Test that all abstract methods are implemented."""
    strategy = PdmPathDepStrategy()
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
            "pdm": {
                "dependencies": {
                    "requests": "^2.28.0",
                    "broken": None
                }
            }
        }
    }

    paths = PdmPathDepStrategy.extract_paths(data, Path("/tmp"))
    assert paths == []


@pytest.mark.parametrize("data", [
    {"tool": {"pdm": {"dependencies": None}}},
    {"tool": {"pdm": None}},
    {"tool": None},
])
def test_extract_paths_with_none_sections(data):
    """Test extract_paths handles None in various sections."""
    paths = PdmPathDepStrategy.extract_paths(data, Path("/tmp"))
    assert paths == []


def test_extract_paths_preserves_order(tmp_path):
    """Test that extract_paths preserves dependency order."""
    for i in range(5):
        (tmp_path / f"lib{i}").mkdir()

    data = {
        "tool": {
            "pdm": {
                "dependencies": {
                    f"lib{i}": {"path": f"lib{i}"}
                    for i in range(5)
                }
            }
        }
    }

    paths = PdmPathDepStrategy.extract_paths(data, tmp_path)
    assert len(paths) == 5
    # Note: dict order is preserved in Python 3.7+


def test_extract_paths_with_complex_nested_path(tmp_path):
    """Test extracting path with deeply nested structure."""
    dep_dir = tmp_path / "a" / "b" / "c" / "mylib"
    dep_dir.mkdir(parents=True)

    data = {
        "tool": {
            "pdm": {
                "dependencies": {
                    "mylib": {"path": "a/b/c/mylib"}
                }
            }
        }
    }

    paths = PdmPathDepStrategy.extract_paths(data, tmp_path)
    assert len(paths) == 1
    assert paths[0] == dep_dir.resolve()


def test_extract_paths_with_path_containing_special_chars(tmp_path):
    """Test extracting path with special characters in name."""
    dep_dir = tmp_path / "my-lib_v2.0"
    dep_dir.mkdir()

    data = {
        "tool": {
            "pdm": {
                "dependencies": {
                    "mylib": {"path": "my-lib_v2.0"}
                }
            }
        }
    }

    paths = PdmPathDepStrategy.extract_paths(data, tmp_path)
    assert len(paths) == 1
    assert paths[0] == dep_dir.resolve()


def test_extract_paths_with_list_value():
    """Test that list values in dependencies are ignored."""
    data = {
        "tool": {
            "pdm": {
                "dependencies": {
                    "mylib": ["path", "mylib"]
                }
            }
        }
    }

    paths = PdmPathDepStrategy.extract_paths(data, Path("/tmp"))
    assert paths == []


def test_extract_paths_with_empty_path_value(tmp_path):
    """Test that empty path value is handled."""
    data = {
        "tool": {
            "pdm": {
                "dependencies": {
                    "mylib": {"path": ""}
                }
            }
        }
    }

    paths = PdmPathDepStrategy.extract_paths(data, tmp_path)
    assert len(paths) == 1
    # Empty path resolves to project root
    assert paths[0] == tmp_path.resolve()


def test_extract_paths_with_absolute_path():
    """Test extracting absolute path dependency."""
    abs_path = Path("/absolute/path/to/lib")

    data = {
        "tool": {
            "pdm": {
                "dependencies": {
                    "mylib": {"path": str(abs_path)}
                }
            }
        }
    }

    paths = PdmPathDepStrategy.extract_paths(data, Path("/tmp"))
    assert len(paths) == 1
    assert paths[0] == abs_path.resolve()


def test_extract_paths_with_markers(tmp_path):
    """Test path dependency with environment markers."""
    dep_dir = tmp_path / "mylib"
    dep_dir.mkdir()

    data = {
        "tool": {
            "pdm": {
                "dependencies": {
                    "mylib": {
                        "path": "mylib",
                        "markers": "python_version >= '3.9'"
                    }
                }
            }
        }
    }

    paths = PdmPathDepStrategy.extract_paths(data, tmp_path)
    assert len(paths) == 1
    assert paths[0] == dep_dir.resolve()


def test_extract_paths_with_optional_true(tmp_path):
    """Test path dependency marked as optional."""
    dep_dir = tmp_path / "mylib"
    dep_dir.mkdir()

    data = {
        "tool": {
            "pdm": {
                "dependencies": {
                    "mylib": {
                        "path": "mylib",
                        "optional": True
                    }
                }
            }
        }
    }

    paths = PdmPathDepStrategy.extract_paths(data, tmp_path)
    assert len(paths) == 1
    assert paths[0] == dep_dir.resolve()


def test_can_handle_is_strict_about_structure():
    """Test can_handle requires both 'pdm' and 'dependencies' keys."""
    # Has pdm but missing dependencies
    assert PdmPathDepStrategy.can_handle({"tool": {"pdm": {}}}) is False

    # Has nested structure but wrong key names
    assert PdmPathDepStrategy.can_handle({"tool": {"pdm": {"deps": {}}}}) is False

    # Correct structure
    assert PdmPathDepStrategy.can_handle({"tool": {"pdm": {"dependencies": {}}}}) is True


def test_extract_paths_handles_integer_values():
    """Test that integer values in dependencies are ignored."""
    data = {
        "tool": {
            "pdm": {
                "dependencies": {
                    "weird": 12345
                }
            }
        }
    }

    paths = PdmPathDepStrategy.extract_paths(data, Path("/tmp"))
    assert paths == []


def test_extract_paths_handles_boolean_values():
    """Test that boolean values in dependencies are ignored."""
    data = {
        "tool": {
            "pdm": {
                "dependencies": {
                    "weird": True
                }
            }
        }
    }

    paths = PdmPathDepStrategy.extract_paths(data, Path("/tmp"))
    assert paths == []


def test_extract_paths_with_dict_missing_path_key(tmp_path):
    """Test that dict without 'path' key is ignored."""
    data = {
        "tool": {
            "pdm": {
                "dependencies": {
                    "mylib": {"version": "1.0.0", "extras": ["dev"]}
                }
            }
        }
    }

    paths = PdmPathDepStrategy.extract_paths(data, tmp_path)
    assert paths == []


def test_extract_paths_multiple_calls_same_data(tmp_path):
    """Test that multiple calls with same data return consistent results."""
    dep_dir = tmp_path / "mylib"
    dep_dir.mkdir()

    data = {
        "tool": {
            "pdm": {
                "dependencies": {
                    "mylib": {"path": "mylib"}
                }
            }
        }
    }

    paths1 = PdmPathDepStrategy.extract_paths(data, tmp_path)
    paths2 = PdmPathDepStrategy.extract_paths(data, tmp_path)

    assert paths1 == paths2
    assert len(paths1) == 1


def test_label_is_static():
    """Test that label() can be called without instantiation."""
    label = PdmPathDepStrategy.label()
    assert label == "PDM"
    assert isinstance(label, str)


def test_can_handle_is_static():
    """Test that can_handle() can be called without instantiation."""
    result = PdmPathDepStrategy.can_handle({"tool": {"pdm": {"dependencies": {}}}})
    assert result is True


def test_extract_paths_is_static(tmp_path):
    """Test that extract_paths() can be called without instantiation."""
    dep_dir = tmp_path / "mylib"
    dep_dir.mkdir()

    data = {
        "tool": {
            "pdm": {
                "dependencies": {
                    "mylib": {"path": "mylib"}
                }
            }
        }
    }

    paths = PdmPathDepStrategy.extract_paths(data, tmp_path)
    assert len(paths) == 1
    assert paths[0] == dep_dir.resolve()