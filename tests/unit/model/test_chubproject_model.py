import zipfile
from pathlib import Path

import pytest

from pychub.model.chubproject_model import ChubProject, resolve_wheels, get_wheel_name_version
from pychub.model.includes_model import IncludeSpec
from pychub.model.scripts_model import Scripts


# ============================================================
# Test resolve_wheels function
# ============================================================

def test_resolve_wheels_with_provided_main_wheel():
    """When main wheel is provided, it should be returned with additional wheels."""
    mw = "dist/mywheel-1.0.0-py3-none-any.whl"
    aw = ["dist/extra-1.0.0-py3-none-any.whl"]

    main, additional = resolve_wheels(mw, aw)

    assert main == mw
    assert additional == aw


def test_resolve_wheels_with_none_additional_wheels():
    """When main wheel is provided but additional is None, it should handle gracefully."""
    mw = "dist/mywheel-1.0.0-py3-none-any.whl"

    main, additional = resolve_wheels(mw, None)

    assert main == mw
    assert additional is None


def test_resolve_wheels_discovers_from_dist(tmp_path, monkeypatch):
    """When no main wheel provided, it should discover from dist directory."""
    # Create a temp dist directory
    dist_dir = tmp_path / "dist"
    dist_dir.mkdir(exist_ok=True)

    # Create some wheel files
    (dist_dir / "aaa-1.0.0-py3-none-any.whl").touch()
    (dist_dir / "bbb-2.0.0-py3-none-any.whl").touch()
    (dist_dir / "ccc-3.0.0-py3-none-any.whl").touch()

    # Monkeypatch os.getcwd to return tmp_path
    monkeypatch.chdir(tmp_path)

    main, additional = resolve_wheels(None, None)

    print(main, additional)

    assert main.endswith("aaa-1.0.0-py3-none-any.whl")
    assert len(additional) == 2
    assert any("bbb-2.0.0" in w for w in additional)
    assert any("ccc-3.0.0" in w for w in additional)


# ============================================================
# Test get_wheel_name_version function
# ============================================================

def test_get_wheel_name_version_success(tmp_path):
    """Successfully extract name and version from wheel METADATA."""
    wheel_path = tmp_path / "test-1.0.0-py3-none-any.whl"

    # Create a minimal wheel with METADATA
    with zipfile.ZipFile(wheel_path, "w") as zf:
        metadata_content = b"Name: test-package\nVersion: 1.0.0\n"
        zf.writestr("test_package-1.0.0.dist-info/METADATA", metadata_content)

    name, version = get_wheel_name_version(wheel_path)

    assert name == "test-package"
    assert version == "1.0.0"


def test_get_wheel_name_version_no_wheel_path():
    """Should raise ValueError when no wheel path provided."""
    with pytest.raises(ValueError, match="Cannot get wheel name and version"):
        get_wheel_name_version(None)


def test_get_wheel_name_version_no_metadata_file(tmp_path):
    """Should raise ValueError when METADATA file not found in wheel."""
    wheel_path = tmp_path / "test-1.0.0-py3-none-any.whl"

    # Create a wheel without METADATA
    with zipfile.ZipFile(wheel_path, "w") as zf:
        zf.writestr("some_file.txt", "content")

    with pytest.raises(ValueError, match="No METADATA file found in wheel"):
        get_wheel_name_version(wheel_path)


def test_get_wheel_name_version_missing_name_or_version(tmp_path):
    """Should raise ValueError when Name or Version not found in METADATA."""
    wheel_path = tmp_path / "test-1.0.0-py3-none-any.whl"

    # Create a wheel with incomplete METADATA
    with zipfile.ZipFile(wheel_path, "w") as zf:
        metadata_content = b"Author: Someone\n"
        zf.writestr("test_package-1.0.0.dist-info/METADATA", metadata_content)

    with pytest.raises(ValueError, match="Name and Version not found"):
        get_wheel_name_version(wheel_path)


# ============================================================
# Test ChubProject.from_mapping factory
# ============================================================

def test_from_mapping_empty():
    """Empty mapping should create default ChubProject."""
    proj = ChubProject.from_mapping(None)

    assert proj.wheel is None
    assert proj.add_wheels == []
    assert proj.includes == []
    assert proj.metadata == {}
    assert proj.scripts is not None


def test_from_mapping_minimal(tmp_path):
    """Minimal mapping with wheel should extract name and version."""
    wheel_path = tmp_path / "test-1.0.0-py3-none-any.whl"
    with zipfile.ZipFile(wheel_path, "w") as zf:
        metadata_content = b"Name: test-package\nVersion: 1.0.0\n"
        zf.writestr("test_package-1.0.0.dist-info/METADATA", metadata_content)

    mapping = {"wheel": str(wheel_path)}
    proj = ChubProject.from_mapping(mapping)

    assert proj.wheel == str(wheel_path)


def test_from_mapping_complete(tmp_path):
    """Complete mapping with all fields should populate ChubProject."""
    wheel_path = tmp_path / "test-1.0.0-py3-none-any.whl"
    with zipfile.ZipFile(wheel_path, "w") as zf:
        metadata_content = b"Name: test-package\nVersion: 1.0.0\n"
        zf.writestr("test_package-1.0.0.dist-info/METADATA", metadata_content)

    mapping = {
        "wheel": str(wheel_path),
        "add_wheels": ["extra.whl"],
        "chub": "output.chub",
        "entrypoint": "main:run",
        "includes": ["src/data.txt", "src/config.yaml::config/config.yaml"],
        "verbose": True,
        "metadata": {"author": "Test Author", "tags": ["test", "demo"]},
        "scripts": {"pre": ["setup.sh"], "post": ["cleanup.sh"]}
    }
    proj = ChubProject.from_mapping(mapping)

    assert proj.wheel == str(wheel_path)
    assert proj.add_wheels == ["extra.whl"]
    assert proj.chub == "output.chub"
    assert proj.entrypoint == "main:run"
    assert len(proj.includes) == 2
    assert proj.verbose is True
    assert proj.metadata["author"] == "Test Author"
    assert proj.scripts.pre == ["setup.sh"]


# ============================================================
# Test ChubProject.from_toml_document factory
# ============================================================

def test_from_toml_document_pyproject_with_tool_pychub_package(tmp_path):
    """pyproject.toml should look for [tool.pychub.package]."""
    wheel_path = tmp_path / "test-1.0.0-py3-none-any.whl"
    with zipfile.ZipFile(wheel_path, "w") as zf:
        metadata_content = b"Name: test-package\nVersion: 1.0.0\n"
        zf.writestr("test_package-1.0.0.dist-info/METADATA", metadata_content)

    doc = {
        "tool": {
            "pychub": {
                "package": {
                    "wheel": str(wheel_path),
                    "entrypoint": "main:run"
                }
            }
        }
    }

    proj = ChubProject.from_toml_document(doc, "pyproject.toml")

    assert proj.entrypoint == "main:run"


def test_from_toml_document_pyproject_package_disabled(capsys):
    """pyproject.toml with enabled=False should return empty project."""
    doc = {
        "tool": {
            "pychub": {
                "package": {
                    "enabled": False,
                    "wheel": "test.whl"
                }
            }
        }
    }

    proj = ChubProject.from_toml_document(doc, "pyproject.toml")
    captured = capsys.readouterr()

    assert "enabled] is False" in captured.out
    assert proj.wheel is None


def test_from_toml_document_chubproject_with_pychub_package(tmp_path):
    """chubproject.toml should look for [pychub.package]."""
    wheel_path = tmp_path / "test-1.0.0-py3-none-any.whl"
    with zipfile.ZipFile(wheel_path, "w") as zf:
        metadata_content = b"Name: test-package\nVersion: 1.0.0\n"
        zf.writestr("test_package-1.0.0.dist-info/METADATA", metadata_content)

    doc = {
        "pychub": {
            "package": {
                "wheel": str(wheel_path),
                "entrypoint": "main:app"
            }
        }
    }

    proj = ChubProject.from_toml_document(doc, "chubproject.toml")

    assert proj.entrypoint == "main:app"


def test_from_toml_document_chubproject_flat_table(tmp_path):
    """chubproject.toml with flat table should work."""
    wheel_path = tmp_path / "test-1.0.0-py3-none-any.whl"
    with zipfile.ZipFile(wheel_path, "w") as zf:
        metadata_content = b"Name: test-package\nVersion: 1.0.0\n"
        zf.writestr("test_package-1.0.0.dist-info/METADATA", metadata_content)

    doc = {
        "wheel": str(wheel_path),
        "entrypoint": "main:cli"
    }

    proj = ChubProject.from_toml_document(doc, "my-chubproject.toml")

    assert proj.entrypoint == "main:cli"


# ============================================================
# Test ChubProject.from_cli_args factory
# ============================================================

def test_from_cli_args_minimal(tmp_path):
    """Minimal CLI args should create valid ChubProject."""
    wheel_path = tmp_path / "test-1.0.0-py3-none-any.whl"
    with zipfile.ZipFile(wheel_path, "w") as zf:
        metadata_content = b"Name: test-package\nVersion: 1.0.0\n"
        zf.writestr("test_package-1.0.0.dist-info/METADATA", metadata_content)

    args = {"wheel": str(wheel_path)}
    proj = ChubProject.from_cli_args(args)

    assert proj.wheel == str(wheel_path)


def test_from_cli_args_complete(tmp_path):
    """Complete CLI args should populate all fields."""
    wheel_path = tmp_path / "test-1.0.0-py3-none-any.whl"
    with zipfile.ZipFile(wheel_path, "w") as zf:
        metadata_content = b"Name: test-package\nVersion: 1.0.0\n"
        zf.writestr("test_package-1.0.0.dist-info/METADATA", metadata_content)

    args = {
        "wheel": str(wheel_path),
        "chub": "output.chub",
        "entrypoint": "main:run",
        "verbose": True,
        "add_wheel": ["extra1.whl", "extra2.whl"],
        "include": ["src/data.txt", "config.yaml::app/config.yaml"],
        "pre_script": ["setup.sh"],
        "post_script": ["cleanup.sh"],
        "metadata_entry": ["author=John Doe", "tags=test,demo"]
    }
    proj = ChubProject.from_cli_args(args)

    assert proj.wheel == str(wheel_path)
    assert proj.chub == "output.chub"
    assert proj.entrypoint == "main:run"
    assert proj.verbose is True
    assert proj.add_wheels == ["extra1.whl", "extra2.whl"]
    assert len(proj.includes) == 2
    assert proj.scripts.pre == ["setup.sh"]
    assert proj.scripts.post == ["cleanup.sh"]
    assert proj.metadata["author"] == "John Doe"
    assert proj.metadata["tags"] == ["test", "demo"]


def test_from_cli_args_comma_separated_values(tmp_path):
    """CLI args with comma-separated values should be split."""
    wheel_path = tmp_path / "test-1.0.0-py3-none-any.whl"
    with zipfile.ZipFile(wheel_path, "w") as zf:
        metadata_content = b"Name: test-package\nVersion: 1.0.0\n"
        zf.writestr("test_package-1.0.0.dist-info/METADATA", metadata_content)

    args = {
        "wheel": str(wheel_path),
        "add_wheel": "extra1.whl,extra2.whl,extra3.whl",
        "include": "file1.txt,file2.txt"
    }
    proj = ChubProject.from_cli_args(args)

    assert proj.add_wheels == ["extra1.whl", "extra2.whl", "extra3.whl"]
    assert len(proj.includes) == 2


def test_from_cli_args_invalid_metadata_entry(tmp_path):
    """Invalid metadata entry without = should raise ValueError."""
    wheel_path = tmp_path / "test-1.0.0-py3-none-any.whl"
    with zipfile.ZipFile(wheel_path, "w") as zf:
        metadata_content = b"Name: test-package\nVersion: 1.0.0\n"
        zf.writestr("test_package-1.0.0.dist-info/METADATA", metadata_content)

    args = {
        "wheel": str(wheel_path),
        "metadata_entry": ["invalid_entry_without_equals"]
    }

    with pytest.raises(ValueError, match="must be key=value"):
        ChubProject.from_cli_args(args)


def test_from_cli_args_no_wheel():
    """CLI args without wheel should handle None gracefully."""
    args = {
        "chub": "output.chub",
        "verbose": True
    }
    proj = ChubProject.from_cli_args(args)

    assert proj.wheel is None
    assert proj.chub == "output.chub"


# ============================================================
# Test ChubProject.merge_from_cli_args
# ============================================================

def test_merge_from_cli_args_additive(tmp_path):
    """Merge should extend lists and preserve existing values."""
    wheel_path = tmp_path / "test-1.0.0-py3-none-any.whl"
    with zipfile.ZipFile(wheel_path, "w") as zf:
        metadata_content = b"Name: test-package\nVersion: 1.0.0\n"
        zf.writestr("test_package-1.0.0.dist-info/METADATA", metadata_content)

    existing = ChubProject(
        wheel=str(wheel_path),
        add_wheels=["extra1.whl"],
        includes=[IncludeSpec(src="file1.txt", dest=None)],
        metadata={"author": "John"},
        scripts=Scripts.from_mapping({"pre": ["setup.sh"], "post": []})
    )

    args = {
        "wheel": str(wheel_path),
        "add_wheel": ["extra2.whl"],
        "include": ["file2.txt"],
        "pre_script": ["init.sh"],
        "metadata_entry": ["version=1.0"]
    }

    merged = ChubProject.merge_from_cli_args(existing, args)

    assert len(merged.add_wheels) == 2
    assert "extra1.whl" in merged.add_wheels
    assert "extra2.whl" in merged.add_wheels
    assert len(merged.includes) == 2
    assert len(merged.scripts.pre) == 2
    assert merged.metadata["author"] == "John"
    assert merged.metadata["version"] == "1.0"


def test_merge_from_cli_args_dedup(tmp_path):
    """Merge should deduplicate lists."""
    wheel_path = tmp_path / "test-1.0.0-py3-none-any.whl"
    with zipfile.ZipFile(wheel_path, "w") as zf:
        metadata_content = b"Name: test-package\nVersion: 1.0.0\n"
        zf.writestr("test_package-1.0.0.dist-info/METADATA", metadata_content)

    existing = ChubProject(
        wheel=str(wheel_path),
        add_wheels=["extra.whl"],
        includes=[IncludeSpec(src="file.txt", dest=None)]
    )

    args = {
        "wheel": str(wheel_path),
        "add_wheel": ["extra.whl"],  # duplicate
        "include": ["file.txt"]  # duplicate
    }

    merged = ChubProject.merge_from_cli_args(existing, args)

    assert len(merged.add_wheels) == 1
    assert len(merged.includes) == 1


def test_merge_from_cli_args_preserve_existing_scalars(tmp_path):
    """Merge should keep existing scalars unless explicitly provided."""
    wheel_path = tmp_path / "test-1.0.0-py3-none-any.whl"
    with zipfile.ZipFile(wheel_path, "w") as zf:
        metadata_content = b"Name: test-package\nVersion: 1.0.0\n"
        zf.writestr("test_package-1.0.0.dist-info/METADATA", metadata_content)

    existing = ChubProject(
        wheel=str(wheel_path),
        chub="existing.chub",
        entrypoint="main:old",
        verbose=False
    )

    args = {}  # No new args

    merged = ChubProject.merge_from_cli_args(existing, args)

    assert merged.wheel == str(wheel_path)
    assert merged.chub == "existing.chub"
    assert merged.entrypoint == "main:old"


# ============================================================
# Test ChubProject.override_from_cli_args
# ============================================================

def test_override_from_cli_args_replace_lists(tmp_path):
    """Override should replace lists wholesale."""
    wheel_path = tmp_path / "test-1.0.0-py3-none-any.whl"
    with zipfile.ZipFile(wheel_path, "w") as zf:
        metadata_content = b"Name: test-package\nVersion: 1.0.0\n"
        zf.writestr("test_package-1.0.0.dist-info/METADATA", metadata_content)

    existing = ChubProject(
        wheel=str(wheel_path),
        add_wheels=["extra1.whl", "extra2.whl"],
        includes=[IncludeSpec(src="old.txt", dest=None)]
    )

    args = {
        "wheel": str(wheel_path),
        "add_wheel": ["new.whl"],
        "include": ["new.txt"]
    }

    overridden = ChubProject.override_from_cli_args(existing, args)

    assert overridden.add_wheels == ["new.whl"]
    assert len(overridden.includes) == 1
    assert overridden.includes[0].src == "new.txt"


def test_override_from_cli_args_replace_scripts(tmp_path):
    """Override should replace scripts wholesale if provided."""
    wheel_path = tmp_path / "test-1.0.0-py3-none-any.whl"
    with zipfile.ZipFile(wheel_path, "w") as zf:
        metadata_content = b"Name: test-package\nVersion: 1.0.0\n"
        zf.writestr("test_package-1.0.0.dist-info/METADATA", metadata_content)

    existing = ChubProject(
        wheel=str(wheel_path),
        scripts=Scripts.from_mapping({"pre": ["old.sh"], "post": ["cleanup.sh"]})
    )

    args = {
        "wheel": str(wheel_path),
        "pre_script": ["new.sh"]
    }

    overridden = ChubProject.override_from_cli_args(existing, args)

    assert overridden.scripts.pre == ["new.sh"]


def test_override_from_cli_args_update_metadata(tmp_path):
    """Override should update metadata keys."""
    wheel_path = tmp_path / "test-1.0.0-py3-none-any.whl"
    with zipfile.ZipFile(wheel_path, "w") as zf:
        metadata_content = b"Name: test-package\nVersion: 1.0.0\n"
        zf.writestr("test_package-1.0.0.dist-info/METADATA", metadata_content)

    existing = ChubProject(
        wheel=str(wheel_path),
        metadata={"author": "John", "version": "1.0"}
    )

    args = {
        "wheel": str(wheel_path),
        "metadata_entry": ["version=2.0", "tags=test"]
    }

    overridden = ChubProject.override_from_cli_args(existing, args)

    assert overridden.metadata["author"] == "John"
    assert overridden.metadata["version"] == "2.0"
    assert overridden.metadata["tags"] == "test"


# ============================================================
# Test ChubProject._select_package_table
# ============================================================

def test_select_package_table_pyproject_enabled(capsys):
    """pyproject.toml with [tool.pychub.package] should be selected."""
    doc = {
        "tool": {
            "pychub": {
                "package": {
                    "wheel": "test.whl"
                }
            }
        }
    }

    result = ChubProject._select_package_table(doc, "pyproject.toml")
    captured = capsys.readouterr()

    assert result is not None
    assert result["wheel"] == "test.whl"
    assert "enabled" in captured.out


def test_select_package_table_pyproject_disabled(capsys):
    """pyproject.toml with enabled=False should return None."""
    doc = {
        "tool": {
            "pychub": {
                "package": {
                    "enabled": False
                }
            }
        }
    }

    result = ChubProject._select_package_table(doc, "pyproject.toml")
    captured = capsys.readouterr()

    assert result is None
    assert "is False" in captured.out


def test_select_package_table_pyproject_missing(capsys):
    """pyproject.toml without [tool.pychub.package] should return None."""
    doc = {"tool": {"other": {}}}

    result = ChubProject._select_package_table(doc, "pyproject.toml")
    captured = capsys.readouterr()

    assert result is None
    assert "not found" in captured.out


def test_select_package_table_chubproject_nested(capsys):
    """chubproject.toml with [pychub.package] should be selected."""
    doc = {
        "pychub": {
            "package": {
                "wheel": "test.whl"
            }
        }
    }

    result = ChubProject._select_package_table(doc, "chubproject.toml")
    captured = capsys.readouterr()

    assert result is not None
    assert result["wheel"] == "test.whl"
    assert "enabled" in captured.out


def test_select_package_table_chubproject_flat(capsys):
    """chubproject.toml with flat table should be selected."""
    doc = {"wheel": "test.whl", "entrypoint": "main:run"}

    result = ChubProject._select_package_table(doc, "my-chubproject.toml")
    captured = capsys.readouterr()

    assert result is not None
    assert result["wheel"] == "test.whl"
    assert "flat table" in captured.out


def test_select_package_table_unrecognized(capsys):
    """Unrecognized filename should return None."""
    doc = {"wheel": "test.whl"}

    result = ChubProject._select_package_table(doc, "random.toml")
    captured = capsys.readouterr()

    assert result is None
    assert "unrecognized" in captured.out


# ============================================================
# Test ChubProject.determine_table_path
# ============================================================

def test_determine_table_path_pyproject():
    """pyproject.toml should always return default table."""
    path = Path("pyproject.toml")

    result = ChubProject.determine_table_path(path, None)

    assert result == "tool.pychub.package"


def test_determine_table_path_chubproject_none():
    """chubproject.toml with None arg should return default table."""
    path = Path("chubproject.toml")

    result = ChubProject.determine_table_path(path, None)

    assert result == "tool.pychub.package"


def test_determine_table_path_chubproject_flat():
    """chubproject.toml with 'flat' arg should return None."""
    path = Path("chubproject.toml")

    result = ChubProject.determine_table_path(path, "flat")

    assert result is None


def test_determine_table_path_chubproject_custom():
    """chubproject.toml with custom table arg should return it."""
    path = Path("my-chubproject.toml")

    result = ChubProject.determine_table_path(path, "pychub.package")

    assert result == "pychub.package"


def test_determine_table_path_invalid_filename():
    """Invalid filename should raise ValueError."""
    path = Path("invalid.toml")

    with pytest.raises(ValueError, match="Invalid chubproject_path"):
        ChubProject.determine_table_path(path, None)


def test_determine_table_path_invalid_table_arg():
    """Invalid table arg should raise ValueError."""
    path = Path("chubproject.toml")

    with pytest.raises(ValueError, match="Invalid table_arg"):
        ChubProject.determine_table_path(path, "invalid.table.name")


# ============================================================
# Test ChubProject._comma_split_maybe
# ============================================================

def test_comma_split_maybe_none():
    """None should return empty list."""
    result = ChubProject._comma_split_maybe(None)
    assert result == []


def test_comma_split_maybe_string():
    """String with commas should be split."""
    result = ChubProject._comma_split_maybe("a,b,c")
    assert result == ["a", "b", "c"]


def test_comma_split_maybe_string_with_spaces():
    """String with commas and spaces should be split and stripped."""
    result = ChubProject._comma_split_maybe("a , b , c ")
    assert result == ["a", "b", "c"]


def test_comma_split_maybe_list():
    """List of strings should be returned as-is."""
    result = ChubProject._comma_split_maybe(["a", "b", "c"])
    assert result == ["a", "b", "c"]


def test_comma_split_maybe_list_with_commas():
    """List containing comma-separated strings should be split."""
    result = ChubProject._comma_split_maybe(["a,b", "c"])
    assert result == ["a", "b", "c"]


def test_comma_split_maybe_empty_string():
    """Empty string should return empty list."""
    result = ChubProject._comma_split_maybe("")
    assert result == []


# ============================================================
# Test ChubProject._flatten
# ============================================================

def test_flatten_none():
    """None should return empty list."""
    result = ChubProject._flatten(None)
    assert result == []


def test_flatten_simple_list():
    """Simple list should be returned as-is."""
    result = ChubProject._flatten(["a", "b", "c"])
    assert result == ["a", "b", "c"]


def test_flatten_nested_list():
    """Nested lists should be flattened."""
    result = ChubProject._flatten([["a", "b"], ["c"]])
    assert result == ["a", "b", "c"]


def test_flatten_mixed():
    """Mixed list and non-list items should be flattened."""
    result = ChubProject._flatten(["a", ["b", "c"], "d"])
    assert result == ["a", "b", "c", "d"]


def test_flatten_empty_list():
    """Empty list should return empty list."""
    result = ChubProject._flatten([])
    assert result == []


# ============================================================
# Test ChubProject._dedup
# ============================================================

def test_dedup_no_duplicates():
    """List without duplicates should remain unchanged."""
    result = ChubProject._dedup(["a", "b", "c"])
    assert result == ["a", "b", "c"]


def test_dedup_with_duplicates():
    """List with duplicates should have duplicates removed."""
    result = ChubProject._dedup(["a", "b", "a", "c", "b"])
    assert result == ["a", "b", "c"]


def test_dedup_preserve_order():
    """Dedup should preserve first occurrence order."""
    result = ChubProject._dedup(["c", "b", "a", "b", "c"])
    assert result == ["c", "b", "a"]


def test_dedup_empty_list():
    """Empty list should return empty list."""
    result = ChubProject._dedup([])
    assert result == []


# ============================================================
# Test ChubProject._dedup_includes
# ============================================================

def test_dedup_includes_no_duplicates():
    """IncludeSpecs without duplicates should remain unchanged."""
    specs = [
        IncludeSpec(src="a.txt", dest=None),
        IncludeSpec(src="b.txt", dest="dest/b.txt")
    ]
    result = ChubProject._dedup_includes(specs, [])

    assert len(result) == 2
    assert result[0].src == "a.txt"
    assert result[1].src == "b.txt"


def test_dedup_includes_with_duplicates():
    """Duplicate IncludeSpecs should be removed."""
    a = [IncludeSpec(src="a.txt", dest=None)]
    b = [IncludeSpec(src="a.txt", dest=None)]

    result = ChubProject._dedup_includes(a, b)

    assert len(result) == 1


def test_dedup_includes_preserve_order():
    """Dedup should preserve first occurrence order."""
    a = [IncludeSpec(src="a.txt", dest=None)]
    b = [
        IncludeSpec(src="b.txt", dest=None),
        IncludeSpec(src="a.txt", dest=None),
        IncludeSpec(src="c.txt", dest=None)
    ]

    result = ChubProject._dedup_includes(a, b)

    assert len(result) == 3
    assert result[0].src == "a.txt"
    assert result[1].src == "b.txt"
    assert result[2].src == "c.txt"


def test_dedup_includes_different_dest():
    """Same src with different dest should be considered different."""
    a = [IncludeSpec(src="a.txt", dest="dest1/a.txt")]
    b = [IncludeSpec(src="a.txt", dest="dest2/a.txt")]

    result = ChubProject._dedup_includes(a, b)

    assert len(result) == 2


# ============================================================
# Test ChubProject.to_mapping
# ============================================================

def test_to_mapping_minimal():
    """Minimal ChubProject should export to mapping."""
    proj = ChubProject(
        wheel="test.whl",
        add_wheels=[],
        includes=[],
        metadata={},
        scripts=Scripts()
    )

    mapping = proj.to_mapping()

    assert mapping["wheel"] == "test.whl"
    assert mapping["add_wheels"] == []
    assert mapping["includes"] == []
    assert mapping["metadata"] == {}
    assert mapping["scripts"] == {"pre": [], "post": []}


def test_to_mapping_complete():
    """Complete ChubProject should export all fields."""
    proj = ChubProject(
        wheel="test.whl",
        add_wheels=["extra.whl"],
        chub="output.chub",
        entrypoint="main:run",
        includes=[IncludeSpec(src="file.txt", dest="dest/file.txt")],
        verbose=True,
        metadata={"author": "John"},
        scripts=Scripts.from_mapping({"pre": ["setup.sh"], "post": ["cleanup.sh"]})
    )

    mapping = proj.to_mapping()

    assert mapping["wheel"] == "test.whl"
    assert mapping["add_wheels"] == ["extra.whl"]
    assert mapping["chub"] == "output.chub"
    assert mapping["entrypoint"] == "main:run"
    assert mapping["includes"] == ["file.txt::dest/file.txt"]
    assert mapping["verbose"] is True
    assert mapping["metadata"]["author"] == "John"
    assert mapping["scripts"]["pre"] == ["setup.sh"]
    assert mapping["scripts"]["post"] == ["cleanup.sh"]


def test_to_mapping_round_trip(tmp_path):
    """Round-trip through to_mapping and from_mapping should preserve data."""
    wheel_path = tmp_path / "test-1.0.0-py3-none-any.whl"
    with zipfile.ZipFile(wheel_path, "w") as zf:
        metadata_content = b"Name: test-package\nVersion: 1.0.0\n"
        zf.writestr("test_package-1.0.0.dist-info/METADATA", metadata_content)

    original = ChubProject(
        wheel=str(wheel_path),
        add_wheels=["extra.whl"],
        chub="output.chub",
        entrypoint="main:run",
        includes=[IncludeSpec(src="file.txt", dest=None)],
        verbose=True,
        metadata={"author": "John"},
        scripts=Scripts.from_mapping({"pre": ["setup.sh"], "post": []})
    )

    mapping = original.to_mapping()
    restored = ChubProject.from_mapping(mapping)

    assert restored.wheel == original.wheel
    assert restored.add_wheels == original.add_wheels
    assert restored.chub == original.chub
    assert restored.entrypoint == original.entrypoint
    assert len(restored.includes) == len(original.includes)
    assert restored.verbose == original.verbose
    assert restored.metadata == original.metadata


# ============================================================
# Edge cases and error handling
# ============================================================

def test_from_mapping_with_string_includes(tmp_path):
    """from_mapping should parse string includes using IncludeSpec.parse."""
    wheel_path = tmp_path / "test-1.0.0-py3-none-any.whl"
    with zipfile.ZipFile(wheel_path, "w") as zf:
        metadata_content = b"Name: test-package\nVersion: 1.0.0\n"
        zf.writestr("test_package-1.0.0.dist-info/METADATA", metadata_content)

    mapping = {
        "wheel": str(wheel_path),
        "includes": ["file1.txt", "file2.txt::dest/file2.txt"]
    }

    proj = ChubProject.from_mapping(mapping)

    assert len(proj.includes) == 2
    assert proj.includes[0].src == "file1.txt"
    assert proj.includes[0].dest is None
    assert proj.includes[1].src == "file2.txt"
    assert proj.includes[1].dest == "dest/file2.txt"


def test_from_cli_args_metadata_with_nested_commas():
    """Metadata values with commas should be split into lists."""
    args = {
        "metadata_entry": ["tags=test,demo,example"]
    }

    proj = ChubProject.from_cli_args(args)

    assert proj.metadata["tags"] == ["test", "demo", "example"]


def test_from_cli_args_metadata_without_commas():
    """Metadata values without commas should remain strings."""
    args = {
        "metadata_entry": ["author=John Doe"]
    }

    proj = ChubProject.from_cli_args(args)

    assert proj.metadata["author"] == "John Doe"


def test_merge_scripts_not_provided():
    """Merge should not replace scripts if none provided in args."""
    existing = ChubProject(
        scripts=Scripts.from_mapping({"pre": ["existing.sh"], "post": []})
    )

    args = {}

    merged = ChubProject.merge_from_cli_args(existing, args)

    assert merged.scripts.pre == ["existing.sh"]


def test_override_keeps_existing_when_not_provided(tmp_path):
    """Override should keep existing values when not provided in args."""
    wheel_path = tmp_path / "test-1.0.0-py3-none-any.whl"
    with zipfile.ZipFile(wheel_path, "w") as zf:
        metadata_content = b"Name: test-package\nVersion: 1.0.0\n"
        zf.writestr("test_package-1.0.0.dist-info/METADATA", metadata_content)

    existing = ChubProject(
        wheel=str(wheel_path),
        add_wheels=["extra.whl"],
        includes=[IncludeSpec(src="file.txt", dest=None)]
    )

    args = {"wheel": str(wheel_path)}

    overridden = ChubProject.override_from_cli_args(existing, args)

    assert overridden.add_wheels == ["extra.whl"]
    assert len(overridden.includes) == 1


# ============================================================
# Test ChubProject.load_file exceptions
# ============================================================

def test_load_file_not_found():
    """load_file should raise ChubProjectError when file doesn't exist."""
    from pychub.model.chubproject_model import ChubProjectError

    with pytest.raises(ChubProjectError, match="Project file not found"):
        ChubProject.load_file("/nonexistent/path/file.toml")


def test_load_file_invalid_toml(tmp_path):
    """load_file should raise ChubProjectError when TOML is invalid."""
    from pychub.model.chubproject_model import ChubProjectError

    bad_toml = tmp_path / "bad.toml"
    bad_toml.write_text("this is not valid = toml [[[]", encoding="utf-8")

    with pytest.raises(ChubProjectError, match="Failed to parse TOML"):
        ChubProject.load_file(bad_toml)


# ============================================================
# Test ChubProject.save_file with raw dict
# ============================================================

def test_save_file_with_raw_dict(tmp_path):
    """save_file should accept a raw dict and convert it via from_mapping."""
    wheel_path = tmp_path / "test-1.0.0-py3-none-any.whl"
    with zipfile.ZipFile(wheel_path, "w") as zf:
        metadata_content = b"Name: test-package\nVersion: 1.0.0\n"
        zf.writestr("test_package-1.0.0.dist-info/METADATA", metadata_content)

    raw_dict = {
        "wheel": str(wheel_path),
        "entrypoint": "main:run",
        "metadata": {"author": "Test"}
    }

    output = tmp_path / "output.toml"
    result = ChubProject.save_file(raw_dict, output, overwrite=True)

    assert result.exists()
    content = result.read_text()
    assert "main:run" in content


# ============================================================
# Test _coerce with Path and set
# ============================================================

def test_save_file_coerce_path(tmp_path):
    """save_file should coerce Path objects to posix strings."""
    wheel_path = tmp_path / "test-1.0.0-py3-none-any.whl"
    with zipfile.ZipFile(wheel_path, "w") as zf:
        metadata_content = b"Name: test-package\nVersion: 1.0.0\n"
        zf.writestr("test_package-1.0.0.dist-info/METADATA", metadata_content)

    proj = ChubProject(
        wheel=str(wheel_path),
        metadata={"path_field": Path("/some/path")}
    )

    output = tmp_path / "output.toml"
    result = ChubProject.save_file(proj, output, overwrite=True)

    assert result.exists()
    content = result.read_text()
    # Path should be converted to posix string
    assert "/some/path" in content


def test_save_file_coerce_set(tmp_path):
    """save_file should coerce sets to sorted lists."""
    wheel_path = tmp_path / "test-1.0.0-py3-none-any.whl"
    with zipfile.ZipFile(wheel_path, "w") as zf:
        metadata_content = b"Name: test-package\nVersion: 1.0.0\n"
        zf.writestr("test_package-1.0.0.dist-info/METADATA", metadata_content)

    proj = ChubProject(
        wheel=str(wheel_path),
        metadata={"tags": {"python", "cli", "app"}}
    )

    output = tmp_path / "output.toml"
    result = ChubProject.save_file(proj, output, overwrite=True)

    assert result.exists()
    content = result.read_text()
    # Set should be sorted
    assert "app" in content
    assert "cli" in content
    assert "python" in content


# ============================================================
# Test to_json and to_yaml methods
# ============================================================

def test_to_json():
    """to_json should serialize ChubProject to JSON string."""
    proj = ChubProject(
        wheel="test.whl",
        entrypoint="main:run",
        metadata={"author": "John"},
        add_wheels=["extra.whl"],
        includes=[],
        scripts=Scripts()
    )

    json_str = proj.to_json()

    assert '"wheel": "test.whl"' in json_str
    assert '"entrypoint": "main:run"' in json_str
    assert '"author": "John"' in json_str


def test_to_json_with_custom_indent():
    """to_json should respect custom indent parameter."""
    proj = ChubProject(
        wheel="test.whl",
        add_wheels=[],
        includes=[],
        scripts=Scripts()
    )

    json_str = proj.to_json(indent=4)

    # 4-space indent should be present
    assert "    " in json_str


def test_to_yaml():
    """to_yaml should serialize ChubProject to YAML string."""
    proj = ChubProject(
        wheel="test.whl",
        entrypoint="main:app",
        metadata={"version": "1.0"},
        add_wheels=["extra.whl"],
        includes=[],
        scripts=Scripts()
    )

    yaml_str = proj.to_yaml()

    assert "wheel: test.whl" in yaml_str
    assert "entrypoint: main:app" in yaml_str
    assert "version: '1.0'" in yaml_str or "version: 1.0" in yaml_str


def test_to_yaml_with_custom_indent():
    """to_yaml should respect custom indent parameter."""
    proj = ChubProject(
        wheel="test.whl",
        add_wheels=[],
        includes=[],
        scripts=Scripts()
    )

    yaml_str = proj.to_yaml(indent=4)

    assert yaml_str


def test_to_yaml_raises_when_yaml_not_installed(monkeypatch):
    """to_yaml should raise RuntimeError when PyYAML is not installed."""
    import pychub.model.chubproject_model as mod

    # Mock yaml module as None to simulate it not being installed
    original_yaml = mod.yaml
    monkeypatch.setattr(mod, "yaml", None)

    proj = ChubProject(
        wheel="test.whl",
        add_wheels=[],
        includes=[],
        scripts=Scripts()
    )

    with pytest.raises(RuntimeError, match="PyYAML not installed"):
        proj.to_yaml()

    # Restore
    monkeypatch.setattr(mod, "yaml", original_yaml)
