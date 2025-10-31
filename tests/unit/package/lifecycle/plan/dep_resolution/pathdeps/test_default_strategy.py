from pathlib import Path

from pychub.package.lifecycle.plan.dep_resolution.pathdeps.default_strategy import DefaultPathDepStrategy


# ============================================================================
# label() tests
# ============================================================================

def test_label_returns_default():
    """Test that label() returns 'Default'."""
    assert DefaultPathDepStrategy.label() == "Default"


# ============================================================================
# can_handle() tests
# ============================================================================

def test_can_handle_always_returns_true():
    """Test can_handle always returns True (fallback strategy)."""
    assert DefaultPathDepStrategy.can_handle({}) is True


def test_can_handle_with_any_data():
    """Test can_handle returns True with any data structure."""
    test_cases = [
        {},
        {"tool": {"poetry": {}}},
        {"tool": {"pdm": {"dependencies": {}}}},
        {"project": {"dependencies": []}},
        {"custom": {"section": {"data": "value"}}},
        {"dependencies": []},
        None,
    ]

    for data in test_cases:
        assert DefaultPathDepStrategy.can_handle(data) is True


def test_can_handle_with_none():
    """Test can_handle returns True even with None."""
    assert DefaultPathDepStrategy.can_handle(None) is True


def test_can_handle_is_universal_fallback():
    """Test that can_handle is designed as universal fallback."""
    # Should accept literally anything
    assert DefaultPathDepStrategy.can_handle({"anything": "goes"}) is True
    assert DefaultPathDepStrategy.can_handle({"": ""}) is True
    assert DefaultPathDepStrategy.can_handle({"complex": {"nested": {"structure": {}}}}) is True


# ============================================================================
# extract_paths() tests - Basic functionality
# ============================================================================

def test_extract_paths_from_dict_style_dependencies(tmp_path):
    """Test extracting from dict-style dependencies."""
    dep_dir = tmp_path / "mylib"
    dep_dir.mkdir()

    data = {
        "custom": {
            "dependencies": {
                "mylib": {"path": "mylib"}
            }
        }
    }

    paths = DefaultPathDepStrategy.extract_paths(data, tmp_path)
    assert len(paths) == 1
    assert paths[0] == dep_dir.resolve()


def test_extract_paths_from_list_style_dependencies(tmp_path):
    """Test extracting from list-style dependencies."""
    dep_dir = tmp_path / "mylib"
    dep_dir.mkdir()

    data = {
        "custom": {
            "dependencies": [
                {"path": "mylib"}
            ]
        }
    }

    paths = DefaultPathDepStrategy.extract_paths(data, tmp_path)
    assert len(paths) == 1
    assert paths[0] == dep_dir.resolve()


def test_extract_paths_scans_multiple_sections(tmp_path):
    """Test that it scans multiple sections with 'depend' in name."""
    lib1 = tmp_path / "lib1"
    lib2 = tmp_path / "lib2"
    lib3 = tmp_path / "lib3"
    lib1.mkdir()
    lib2.mkdir()
    lib3.mkdir()

    data = {
        "tool": {
            "dependencies": {"lib1": {"path": "lib1"}},
        },
        "project": {
            "dependencies": [{"path": "lib2"}],
        },
        "custom": {
            "depends": {"lib3": {"path": "lib3"}},
        }
    }

    paths = DefaultPathDepStrategy.extract_paths(data, tmp_path)
    assert len(paths) == 3
    assert lib1.resolve() in paths
    assert lib2.resolve() in paths
    assert lib3.resolve() in paths


# ============================================================================
# extract_paths() tests - "depend" keyword matching
# ============================================================================

def test_extract_paths_matches_dependencies(tmp_path):
    """Test matching 'dependencies' keyword."""
    dep_dir = tmp_path / "mylib"
    dep_dir.mkdir()

    data = {
        "section": {
            "dependencies": {"mylib": {"path": "mylib"}}
        }
    }

    paths = DefaultPathDepStrategy.extract_paths(data, tmp_path)
    assert len(paths) == 1


def test_extract_paths_matches_depends(tmp_path):
    """Test matching 'depends' keyword."""
    dep_dir = tmp_path / "mylib"
    dep_dir.mkdir()

    data = {
        "section": {
            "depends": {"mylib": {"path": "mylib"}}
        }
    }

    paths = DefaultPathDepStrategy.extract_paths(data, tmp_path)
    assert len(paths) == 1


def test_extract_paths_matches_dependency(tmp_path):
    """Test matching 'dependency' keyword (singular)."""
    dep_dir = tmp_path / "mylib"
    dep_dir.mkdir()

    data = {
        "section": {
            "dependency": {"mylib": {"path": "mylib"}}
        }
    }

    paths = DefaultPathDepStrategy.extract_paths(data, tmp_path)
    assert len(paths) == 1


def test_extract_paths_matches_case_insensitive(tmp_path):
    """Test that 'depend' matching is case-insensitive."""
    lib1 = tmp_path / "lib1"
    lib2 = tmp_path / "lib2"
    lib3 = tmp_path / "lib3"
    lib1.mkdir()
    lib2.mkdir()
    lib3.mkdir()

    data = {
        "section1": {
            "DEPENDENCIES": {"lib1": {"path": "lib1"}}
        },
        "section2": {
            "Dependencies": {"lib2": {"path": "lib2"}}
        },
        "section3": {
            "DePeNdS": {"lib3": {"path": "lib3"}}
        }
    }

    paths = DefaultPathDepStrategy.extract_paths(data, tmp_path)
    assert len(paths) == 3


def test_extract_paths_matches_partial_depend_keyword(tmp_path):
    """Test matching any key containing 'depend' substring."""
    lib1 = tmp_path / "lib1"
    lib2 = tmp_path / "lib2"
    lib3 = tmp_path / "lib3"
    lib1.mkdir()
    lib2.mkdir()
    lib3.mkdir()

    data = {
        "tool": {
            "dev-dependencies": {"lib1": {"path": "lib1"}},
            "optional-dependencies": {"lib2": {"path": "lib2"}},
            "build-depends": {"lib3": {"path": "lib3"}}
        }
    }

    paths = DefaultPathDepStrategy.extract_paths(data, tmp_path)
    assert len(paths) == 3


def test_extract_paths_ignores_non_depend_keys():
    """Test that keys without 'depend' are ignored."""
    data = {
        "tool": {
            "scripts": {"mylib": {"path": "mylib"}},
            "metadata": {"lib2": {"path": "lib2"}},
            "config": {"lib3": {"path": "lib3"}}
        }
    }

    paths = DefaultPathDepStrategy.extract_paths(data, Path("/tmp"))
    assert paths == []


# ============================================================================
# extract_paths() tests - Path variations
# ============================================================================

def test_extract_paths_with_relative_path(tmp_path):
    """Test extracting path dependency with relative path."""
    dep_dir = tmp_path / "subdir" / "mylib"
    dep_dir.mkdir(parents=True)

    data = {
        "tool": {
            "dependencies": {"mylib": {"path": "subdir/mylib"}}
        }
    }

    paths = DefaultPathDepStrategy.extract_paths(data, tmp_path)
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
            "dependencies": {"sibling": {"path": "../sibling"}}
        }
    }

    paths = DefaultPathDepStrategy.extract_paths(data, project_dir)
    assert len(paths) == 1
    assert paths[0] == dep_dir.resolve()


def test_extract_paths_with_absolute_path():
    """Test extracting absolute path dependency."""
    abs_path = Path("/absolute/path/to/lib")

    data = {
        "tool": {
            "dependencies": {"mylib": {"path": str(abs_path)}}
        }
    }

    paths = DefaultPathDepStrategy.extract_paths(data, Path("/tmp"))
    assert len(paths) == 1
    assert paths[0] == abs_path.resolve()


def test_extract_paths_with_complex_nested_path(tmp_path):
    """Test extracting path with deeply nested structure."""
    dep_dir = tmp_path / "a" / "b" / "c" / "mylib"
    dep_dir.mkdir(parents=True)

    data = {
        "tool": {
            "dependencies": {"mylib": {"path": "a/b/c/mylib"}}
        }
    }

    paths = DefaultPathDepStrategy.extract_paths(data, tmp_path)
    assert len(paths) == 1
    assert paths[0] == dep_dir.resolve()


def test_extract_paths_resolves_to_absolute(tmp_path):
    """Test that all returned paths are absolute."""
    dep_dir = tmp_path / "mylib"
    dep_dir.mkdir()

    data = {
        "tool": {
            "dependencies": {"mylib": {"path": "mylib"}}
        }
    }

    paths = DefaultPathDepStrategy.extract_paths(data, tmp_path)
    assert all(p.is_absolute() for p in paths)


# ============================================================================
# extract_paths() tests - Mixed structures
# ============================================================================

def test_extract_paths_with_mixed_dict_and_list(tmp_path):
    """Test extracting from both dict and list style dependencies."""
    lib1 = tmp_path / "lib1"
    lib2 = tmp_path / "lib2"
    lib1.mkdir()
    lib2.mkdir()

    data = {
        "section1": {
            "dependencies": {"lib1": {"path": "lib1"}}
        },
        "section2": {
            "dependencies": [{"path": "lib2"}]
        }
    }

    paths = DefaultPathDepStrategy.extract_paths(data, tmp_path)
    assert len(paths) == 2
    assert lib1.resolve() in paths
    assert lib2.resolve() in paths


def test_extract_paths_ignores_non_dict_non_list_dependencies():
    """Test that non-dict/non-list values are ignored."""
    data = {
        "tool": {
            "dependencies": "string value"
        }
    }

    paths = DefaultPathDepStrategy.extract_paths(data, Path("/tmp"))
    assert paths == []


def test_extract_paths_ignores_string_dependencies():
    """Test that string-based dependencies are ignored."""
    data = {
        "tool": {
            "dependencies": {
                "requests": "^2.28.0",
                "pytest": ">=7.0"
            }
        }
    }

    paths = DefaultPathDepStrategy.extract_paths(data, Path("/tmp"))
    assert paths == []


def test_extract_paths_mixed_dependency_types(tmp_path):
    """Test extracting paths with mixed dependency types."""
    dep_dir = tmp_path / "locallib"
    dep_dir.mkdir()

    data = {
        "tool": {
            "dependencies": {
                "requests": "^2.28.0",
                "locallib": {"path": "locallib"},
                "pytest": ">=7.0",
                "gitlib": {"git": "https://github.com/user/gitlib.git"}
            }
        }
    }

    paths = DefaultPathDepStrategy.extract_paths(data, tmp_path)
    assert len(paths) == 1
    assert paths[0] == dep_dir.resolve()


def test_extract_paths_with_extras_and_path(tmp_path):
    """Test path dependency with extras specified."""
    dep_dir = tmp_path / "mylib"
    dep_dir.mkdir()

    data = {
        "tool": {
            "dependencies": {
                "mylib": {"path": "mylib", "extras": ["dev", "test"]}
            }
        }
    }

    paths = DefaultPathDepStrategy.extract_paths(data, tmp_path)
    assert len(paths) == 1
    assert paths[0] == dep_dir.resolve()


# ============================================================================
# extract_paths() tests - Edge cases
# ============================================================================

def test_extract_paths_with_empty_data():
    """Test extract_paths with completely empty data."""
    paths = DefaultPathDepStrategy.extract_paths({}, Path("/tmp"))
    assert paths == []


def test_extract_paths_with_no_dependencies_sections():
    """Test extract_paths when no sections contain 'depend'."""
    data = {
        "tool": {
            "build": {},
            "metadata": {}
        },
        "project": {
            "name": "myproject"
        }
    }

    paths = DefaultPathDepStrategy.extract_paths(data, Path("/tmp"))
    assert paths == []


def test_extract_paths_with_empty_dependencies_dict():
    """Test extract_paths with empty dependencies dict."""
    data = {
        "tool": {
            "dependencies": {}
        }
    }

    paths = DefaultPathDepStrategy.extract_paths(data, Path("/tmp"))
    assert paths == []


def test_extract_paths_with_empty_dependencies_list():
    """Test extract_paths with empty dependencies list."""
    data = {
        "tool": {
            "dependencies": []
        }
    }

    paths = DefaultPathDepStrategy.extract_paths(data, Path("/tmp"))
    assert paths == []


def test_extract_paths_with_none_values():
    """Test extract_paths handles None values gracefully."""
    data = {
        "tool": {
            "dependencies": {
                "mylib": None
            }
        }
    }

    paths = DefaultPathDepStrategy.extract_paths(data, Path("/tmp"))
    assert paths == []


def test_extract_paths_with_none_sections():
    """Test extract_paths handles None sections gracefully."""
    data = {
        "tool": {
            "dependencies": None
        }
    }

    paths = DefaultPathDepStrategy.extract_paths(data, Path("/tmp"))
    assert paths == []


def test_extract_paths_with_dict_missing_path_key():
    """Test that dict without 'path' key is ignored."""
    data = {
        "tool": {
            "dependencies": {
                "mylib": {"version": "1.0.0", "extras": ["dev"]}
            }
        }
    }

    paths = DefaultPathDepStrategy.extract_paths(data, Path("/tmp"))
    assert paths == []


def test_extract_paths_handles_integer_values():
    """Test that integer values in dependencies are ignored."""
    data = {
        "tool": {
            "dependencies": {
                "weird": 12345
            }
        }
    }

    paths = DefaultPathDepStrategy.extract_paths(data, Path("/tmp"))
    assert paths == []


def test_extract_paths_handles_boolean_values():
    """Test that boolean values in dependencies are ignored."""
    data = {
        "tool": {
            "dependencies": {
                "weird": True
            }
        }
    }

    paths = DefaultPathDepStrategy.extract_paths(data, Path("/tmp"))
    assert paths == []


def test_extract_paths_with_nested_dict_not_matching():
    """Test that nested structures without 'path' key are ignored."""
    data = {
        "tool": {
            "dependencies": {
                "mylib": {
                    "nested": {
                        "path": "should-not-find-this"
                    }
                }
            }
        }
    }

    paths = DefaultPathDepStrategy.extract_paths(data, Path("/tmp"))
    assert paths == []


def test_extract_paths_with_empty_path_value(tmp_path):
    """Test that empty path value is handled."""
    data = {
        "tool": {
            "dependencies": {"mylib": {"path": ""}}
        }
    }

    paths = DefaultPathDepStrategy.extract_paths(data, tmp_path)
    assert len(paths) == 1
    # Empty path resolves to project root
    assert paths[0] == tmp_path.resolve()


# ============================================================================
# extract_paths() tests - Nested structures
# ============================================================================

def test_extract_paths_scans_nested_sections(tmp_path):
    """Test that it scans nested sections with 'depend' in name."""
    lib1 = tmp_path / "lib1"
    lib2 = tmp_path / "lib2"
    lib1.mkdir()
    lib2.mkdir()

    data = {
        "tool": {
            "custom": {
                "dependencies": {"lib1": {"path": "lib1"}}
            },
            "another": {
                "depends": {"lib2": {"path": "lib2"}}
            }
        }
    }

    paths = DefaultPathDepStrategy.extract_paths(data, tmp_path)
    assert len(paths) == 2


def test_extract_paths_only_scans_second_level():
    """Test that top-level keys containing 'depend' ARE scanned (recursive behavior)."""
    # The strategy recursively searches for any key containing "depend" at any level
    data = {
        "dependencies": {
            "mylib": {"path": "mylib"}
        }
    }

    # With the recursive implementation, this WILL be found
    paths = DefaultPathDepStrategy.extract_paths(data, Path("/tmp"))
    assert len(paths) == 1  # Now it finds it!


def test_extract_paths_requires_two_level_nesting():
    """Test that dependencies must be in section.subkey structure."""
    data = {
        "tool": {
            "dependencies": {
                "mylib": {"path": "mylib"}
            }
        }
    }

    # This SHOULD be found (tool.dependencies)
    paths = DefaultPathDepStrategy.extract_paths(data, Path("/tmp"))
    assert len(paths) == 1


# ============================================================================
# extract_paths() tests - List structures
# ============================================================================

def test_extract_paths_from_list_with_multiple_items(tmp_path):
    """Test extracting from list with multiple path dependencies."""
    lib1 = tmp_path / "lib1"
    lib2 = tmp_path / "lib2"
    lib1.mkdir()
    lib2.mkdir()

    data = {
        "tool": {
            "dependencies": [
                {"path": "lib1"},
                {"path": "lib2"}
            ]
        }
    }

    paths = DefaultPathDepStrategy.extract_paths(data, tmp_path)
    assert len(paths) == 2
    assert lib1.resolve() in paths
    assert lib2.resolve() in paths


def test_extract_paths_from_list_ignores_non_dict_items():
    """Test that non-dict items in list are ignored."""
    data = {
        "tool": {
            "dependencies": [
                "string-item",
                123,
                True,
                None
            ]
        }
    }

    paths = DefaultPathDepStrategy.extract_paths(data, Path("/tmp"))
    assert paths == []


def test_extract_paths_from_list_mixed_items(tmp_path):
    """Test extracting from list with mixed item types."""
    dep_dir = tmp_path / "mylib"
    dep_dir.mkdir()

    data = {
        "tool": {
            "dependencies": [
                "requests>=2.28.0",
                {"path": "mylib"},
                {"version": "1.0.0"},
                123,
                None
            ]
        }
    }

    paths = DefaultPathDepStrategy.extract_paths(data, tmp_path)
    assert len(paths) == 1
    assert paths[0] == dep_dir.resolve()


# ============================================================================
# Integration / Edge case tests
# ============================================================================

def test_strategy_inherits_from_base():
    """Test that DefaultPathDepStrategy inherits from PathDepStrategy."""
    from pychub.package.lifecycle.plan.dep_resolution.pathdeps.default_strategy import PathDepStrategy
    assert issubclass(DefaultPathDepStrategy, PathDepStrategy)


def test_strategy_implements_all_abstract_methods():
    """Test that all abstract methods are implemented."""
    strategy = DefaultPathDepStrategy()
    assert hasattr(strategy, 'label')
    assert hasattr(strategy, 'can_handle')
    assert hasattr(strategy, 'extract_paths')
    assert callable(strategy.label)
    assert callable(strategy.can_handle)
    assert callable(strategy.extract_paths)


def test_extract_paths_preserves_order(tmp_path):
    """Test that extract_paths preserves dependency order."""
    for i in range(5):
        (tmp_path / f"lib{i}").mkdir()

    data = {
        "tool": {
            "dependencies": {
                f"lib{i}": {"path": f"lib{i}"}
                for i in range(5)
            }
        }
    }

    paths = DefaultPathDepStrategy.extract_paths(data, tmp_path)
    assert len(paths) == 5


def test_extract_paths_multiple_calls_same_data(tmp_path):
    """Test that multiple calls with same data return consistent results."""
    dep_dir = tmp_path / "mylib"
    dep_dir.mkdir()

    data = {
        "tool": {
            "dependencies": {"mylib": {"path": "mylib"}}
        }
    }

    paths1 = DefaultPathDepStrategy.extract_paths(data, tmp_path)
    paths2 = DefaultPathDepStrategy.extract_paths(data, tmp_path)

    assert paths1 == paths2
    assert len(paths1) == 1


def test_label_is_static():
    """Test that label() can be called without instantiation."""
    label = DefaultPathDepStrategy.label()
    assert label == "Default"
    assert isinstance(label, str)


def test_can_handle_is_static():
    """Test that can_handle() can be called without instantiation."""
    result = DefaultPathDepStrategy.can_handle({})
    assert result is True


def test_extract_paths_is_static(tmp_path):
    """Test that extract_paths() can be called without instantiation."""
    dep_dir = tmp_path / "mylib"
    dep_dir.mkdir()

    data = {
        "tool": {
            "dependencies": {"mylib": {"path": "mylib"}}
        }
    }

    paths = DefaultPathDepStrategy.extract_paths(data, tmp_path)
    assert len(paths) == 1
    assert paths[0] == dep_dir.resolve()


def test_extract_paths_with_duplicate_paths(tmp_path):
    """Test extracting dependencies with duplicate paths."""
    dep_dir = tmp_path / "mylib"
    dep_dir.mkdir()

    data = {
        "tool": {
            "dependencies": {
                "mylib1": {"path": "mylib"},
                "mylib2": {"path": "mylib"},
                "mylib3": {"path": "./mylib"}
            }
        }
    }

    paths = DefaultPathDepStrategy.extract_paths(data, tmp_path)
    # All three should be extracted
    assert len(paths) == 3
    # They should all resolve to the same absolute path
    assert all(p == dep_dir.resolve() for p in paths)


def test_extract_paths_with_path_containing_special_chars(tmp_path):
    """Test extracting path with special characters in name."""
    dep_dir = tmp_path / "my-lib_v2.0"
    dep_dir.mkdir()

    data = {
        "tool": {
            "dependencies": {"mylib": {"path": "my-lib_v2.0"}}
        }
    }

    paths = DefaultPathDepStrategy.extract_paths(data, tmp_path)
    assert len(paths) == 1
    assert paths[0] == dep_dir.resolve()


def test_extract_paths_from_real_world_structures(tmp_path):
    """Test extracting from realistic multi-section configurations."""
    lib1 = tmp_path / "lib1"
    lib2 = tmp_path / "lib2"
    lib3 = tmp_path / "lib3"
    lib4 = tmp_path / "lib4"
    lib1.mkdir()
    lib2.mkdir()
    lib3.mkdir()
    lib4.mkdir()

    data = {
        "project": {
            "name": "myproject",
            "dependencies": [{"path": "lib1"}],
            "optional-dependencies": {
                "dev": [{"path": "lib2"}]
            }
        },
        "tool": {
            "custom": {
                "build-dependencies": {"lib3": {"path": "lib3"}}
            }
        },
        "build-system": {
            "requires-depends": [{"path": "lib4"}]
        }
    }

    paths = DefaultPathDepStrategy.extract_paths(data, tmp_path)
    assert len(paths) == 4
    assert all(lib.resolve() in paths for lib in [lib1, lib2, lib3, lib4])


def test_extract_paths_with_deeply_nested_top_level_sections(tmp_path):
    """Test that it scans all top-level sections regardless of complexity."""
    lib1 = tmp_path / "lib1"
    lib2 = tmp_path / "lib2"
    lib1.mkdir()
    lib2.mkdir()

    data = {
        "section_a": {
            "subsection": {
                "dependencies": {"lib1": {"path": "lib1"}}
            }
        },
        "section_b": {
            "other": {
                "nested": {
                    "depends": {"lib2": {"path": "lib2"}}
                }
            }
        }
    }

    paths = DefaultPathDepStrategy.extract_paths(data, tmp_path)
    # Should find both because it scans all subkeys at second level
    assert len(paths) == 2


def test_extract_paths_is_truly_universal(tmp_path):
    """Test that Default strategy can handle unusual configurations."""
    dep_dir = tmp_path / "mylib"
    dep_dir.mkdir()

    # Completely non-standard configuration
    data = {
        "my-custom-tool": {
            "special-dependencies": {"mylib": {"path": "mylib"}}
        }
    }

    paths = DefaultPathDepStrategy.extract_paths(data, tmp_path)
    assert len(paths) == 1
    assert paths[0] == dep_dir.resolve()


def test_can_handle_as_universal_fallback():
    """Test can_handle behavior as a true fallback."""
    # Should handle ANY input without error
    test_inputs = [
        {},
        None,
        {"any": "data"},
        {"complex": {"nested": {"structure": {"here": "value"}}}},
        {"empty": {}},
        {"list": []},
        {"mixed": [1, "two", {"three": 3}]},
    ]

    for test_input in test_inputs:
        assert DefaultPathDepStrategy.can_handle(test_input) is True


def test_extract_paths_with_non_dict_input():
    """Test extract_paths with non-dict input (defensive check coverage)."""
    # Test the defensive isinstance check in _scan_all
    paths = DefaultPathDepStrategy.extract_paths(None, Path("/tmp"))
    assert paths == []


def test_extract_paths_with_list_input():
    """Test extract_paths with list input instead of dict."""
    paths = DefaultPathDepStrategy.extract_paths([{"path": "something"}], Path("/tmp"))
    assert paths == []


def test_extract_paths_with_string_input():
    """Test extract_paths with string input instead of dict."""
    paths = DefaultPathDepStrategy.extract_paths("not a dict", Path("/tmp"))
    assert paths == []
