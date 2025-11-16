import io
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from pychub.model.chubproject_model import ChubProject, ChubProjectError, get_wheel_name_version
from pychub.model.includes_model import IncludeSpec
from pychub.model.scripts_model import Scripts


# ===========================
# project_hash tests
# ===========================

def test_project_hash_generates_16_char_hash():
    """Test that project_hash generates a 16-character hash."""
    chubproject = ChubProject(name="test", version="1.0.0")
    result = chubproject.project_hash()

    assert len(result) == 16
    assert result.isalnum()


def test_project_hash_is_deterministic():
    """Test that project_hash produces the same hash for the same data."""
    chubproject1 = ChubProject(name="test", version="1.0.0")
    chubproject2 = ChubProject(name="test", version="1.0.0")

    hash1 = chubproject1.project_hash()
    hash2 = chubproject2.project_hash()

    assert hash1 == hash2


def test_project_hash_differs_for_different_data():
    """Test that project_hash produces different hashes for different data."""
    chubproject1 = ChubProject(name="test1", version="1.0.0")
    chubproject2 = ChubProject(name="test2", version="1.0.0")

    hash1 = chubproject1.project_hash()
    hash2 = chubproject2.project_hash()

    assert hash1 != hash2


# ============================================================
# Test get_wheel_name_version function (mocking zipfile)
# ============================================================

def test_get_wheel_name_version_success():
    """Successfully extract name and version from wheel METADATA."""
    mock_zipfile = MagicMock()
    mock_zipfile.__enter__.return_value.namelist.return_value = [
        "test_package-1.0.0.dist-info/METADATA",
        "test_package-1.0.0.dist-info/WHEEL"
    ]

    metadata_content = b"Name: test-package\nVersion: 1.0.0\nAuthor: Someone\n"
    mock_zipfile.__enter__.return_value.open.return_value.__enter__.return_value = io.BytesIO(metadata_content)

    with patch("pychub.model.chubproject_model.zipfile.ZipFile", return_value=mock_zipfile):
        name, version = get_wheel_name_version(Path("/fake/path/test.whl"))

    assert name == "test-package"
    assert version == "1.0.0"


def test_get_wheel_name_version_no_wheel_path():
    """Should raise ValueError when no wheel path provided."""
    with pytest.raises(ValueError, match="Cannot get wheel name and version"):
        get_wheel_name_version(None)


def test_get_wheel_name_version_no_metadata_file():
    """Should raise ValueError when METADATA file not found in wheel."""
    mock_zipfile = MagicMock()
    mock_zipfile.__enter__.return_value.namelist.return_value = ["some_file.txt"]

    with patch("pychub.model.chubproject_model.zipfile.ZipFile", return_value=mock_zipfile):
        with pytest.raises(ValueError, match="No METADATA file found in wheel"):
            get_wheel_name_version(Path("/fake/test.whl"))


def test_get_wheel_name_version_missing_name_or_version():
    """Should raise ValueError when Name or Version not found in METADATA."""
    mock_zipfile = MagicMock()
    mock_zipfile.__enter__.return_value.namelist.return_value = ["test-1.0.0.dist-info/METADATA"]

    metadata_content = b"Author: Someone\nDescription: A package\n"
    mock_zipfile.__enter__.return_value.open.return_value.__enter__.return_value = io.BytesIO(metadata_content)

    with patch("pychub.model.chubproject_model.zipfile.ZipFile", return_value=mock_zipfile):
        with pytest.raises(ValueError, match="Name and Version not found"):
            get_wheel_name_version(Path("/fake/test.whl"))


# ============================================================
# Test ChubProject.from_mapping factory
# ============================================================

def test_from_mapping_empty():
    """Empty mapping should create default ChubProject."""
    proj = ChubProject.from_mapping(None)

    assert proj.wheels == []
    assert proj.includes == []
    assert proj.metadata == {}
    assert proj.scripts is not None


def test_from_mapping_minimal():
    """Minimal mapping should create ChubProject with defaults."""
    with patch("pychub.model.chubproject_model.get_wheel_name_version", return_value=("test-pkg", "1.0.0")):
        with patch("pychub.model.chubproject_model.os.getcwd", return_value="/fake/cwd"):
            mapping = {"wheels": ["/fake/test.whl"]}
            proj = ChubProject.from_mapping(mapping)

            assert proj.wheels == ["/fake/test.whl"]
            assert proj.name == "test-pkg"
            assert proj.version == "1.0.0"


def test_from_mapping_complete():
    """Complete mapping with all fields should populate ChubProject."""
    with patch("pychub.model.chubproject_model.get_wheel_name_version", return_value=("test-pkg", "1.0.0")):
        mapping = {
            "wheels": ["/fake/test.whl", "extra.whl"],
            "chub": "output.chub",
            "entrypoint": "main:run",
            "includes": ["src/data.txt", "src/config.yaml::config/config.yaml"],
            "verbose": True,
            "metadata": {"author": "Test Author", "tags": ["test", "demo"]},
            "scripts": {"pre": ["setup.sh"], "post": ["cleanup.sh"]},
            "project_path": "/fake/project"
        }
        proj = ChubProject.from_mapping(mapping)

        assert proj.wheels == ["/fake/test.whl", "extra.whl"]
        assert proj.chub == "output.chub"
        assert proj.entrypoint == "main:run"
        assert len(proj.includes) == 2
        assert proj.verbose is True
        assert proj.metadata["author"] == "Test Author"
        assert proj.scripts.pre == ["setup.sh"]


def test_from_mapping_without_wheel():
    """Mapping without wheel should handle gracefully."""
    with patch("pychub.model.chubproject_model.os.getcwd", return_value="/fake/cwd"):
        mapping = {
            "chub": "output.chub",
            "entrypoint": "main:run"
        }
        proj = ChubProject.from_mapping(mapping)

        assert proj.wheels == []
        assert proj.name is None
        assert proj.version is None


# ============================================================
# Test ChubProject.from_toml_document factory
# ============================================================

def test_from_toml_document_pyproject_with_tool_pychub_package(capsys):
    """pyproject.toml should look for [tool.pychub.package]."""
    with patch("pychub.model.chubproject_model.get_wheel_name_version", return_value=("test-pkg", "1.0.0")):
        doc = {
            "tool": {
                "pychub": {
                    "package": {
                        "wheel": ["/fake/test.whl"],
                        "entrypoint": "main:run"
                    }
                }
            }
        }

        proj = ChubProject.from_toml_document(doc, "pyproject.toml")
        captured = capsys.readouterr()

        assert proj.entrypoint == "main:run"
        assert "enabled" in captured.out


def test_from_toml_document_pyproject_package_disabled(capsys):
    """pyproject.toml with enabled=False should return empty project."""
    doc = {
        "tool": {
            "pychub": {
                "package": {
                    "enabled": False,
                    "wheel": ["test.whl"]
                }
            }
        }
    }

    proj = ChubProject.from_toml_document(doc, "pyproject.toml")
    captured = capsys.readouterr()

    assert "is False" in captured.out
    assert proj.wheels == []


def test_from_toml_document_chubproject_flat_table(capsys):
    """chubproject.toml with flat table should work."""
    with patch("pychub.model.chubproject_model.get_wheel_name_version", return_value=("test-pkg", "1.0.0")):
        doc = {
            "wheel": ["/fake/test.whl"],
            "entrypoint": "main:cli"
        }

        proj = ChubProject.from_toml_document(doc, "my-chubproject.toml")
        captured = capsys.readouterr()

        assert proj.entrypoint == "main:cli"
        assert "flat table" in captured.out


# ============================================================
# Test ChubProject.from_cli_args factory
# ============================================================

def test_from_cli_args_minimal():
    """Minimal CLI args should create valid ChubProject."""
    with patch("pychub.model.chubproject_model.get_wheel_name_version", return_value=("test-pkg", "1.0.0")):
        with patch("pychub.model.chubproject_model.os.getcwd", return_value="/fake/cwd"):
            args = {"wheel": "/fake/test.whl"}
            proj = ChubProject.from_cli_args(args)

            assert proj.wheels == "/fake/test.whl"
            assert proj.name == "test-pkg"
            assert proj.version == "1.0.0"


def test_from_cli_args_complete():
    """Complete CLI args should populate all fields."""
    with patch("pychub.model.chubproject_model.get_wheel_name_version", return_value=("test-pkg", "1.0.0")):
        with patch("pychub.model.chubproject_model.os.getcwd", return_value="/fake/cwd"):
            args = {
                "wheel": "/fake/test.whl",
                "chub": "output.chub",
                "entrypoint": "main:run",
                "verbose": True,
                "include": ["src/data.txt", "config.yaml::app/config.yaml"],
                "pre_script": ["setup.sh"],
                "post_script": ["cleanup.sh"],
                "metadata_entry": ["author=John Doe", "tags=test,demo"]
            }
            proj = ChubProject.from_cli_args(args)

            assert proj.chub == "output.chub"
            assert proj.entrypoint == "main:run"
            assert proj.verbose is True
            assert len(proj.includes) == 2
            assert proj.scripts.pre == ["setup.sh"]
            assert proj.scripts.post == ["cleanup.sh"]
            assert proj.metadata["author"] == "John Doe"
            assert proj.metadata["tags"] == ["test", "demo"]


def test_from_cli_args_invalid_metadata_entry():
    """Invalid metadata entry without = should raise ValueError."""
    with patch("pychub.model.chubproject_model.os.getcwd", return_value="/fake/cwd"):
        with patch("pychub.model.chubproject_model.get_wheel_name_version", return_value=("test", "1.0")):
            args = {
                "wheel": "/fake/test.whl",
                "metadata_entry": ["invalid_entry_without_equals"]
            }

            with pytest.raises(ValueError, match="must be key=value"):
                ChubProject.from_cli_args(args)


def test_from_cli_args_no_wheel():
    """CLI args without wheel should handle None gracefully."""
    with patch("pychub.model.chubproject_model.os.getcwd", return_value="/fake/cwd"):
        args = {
            "chub": "output.chub",
            "verbose": True
        }
        proj = ChubProject.from_cli_args(args)

        assert proj.wheels == []
        assert proj.chub == "output.chub"


# ============================================================
# Test ChubProject merge/override methods
# ============================================================


# Fix test_merge_from_cli_args_preserves_existing - line ~267
def test_merge_from_cli_args_preserves_existing():
    """Merge should keep existing scalars unless explicitly provided."""
    existing = ChubProject(
        wheels=["/fake/base.whl"],
        chub="existing.chub",
        entrypoint="main:old",
        verbose=False,
        includes=[],
        metadata={},
        scripts=Scripts(),
        entrypoint_args=[]
    )

    with patch("pychub.model.chubproject_model.os.getcwd", return_value="/fake/cwd"):
        args = {}
        merged = ChubProject.merge_from_cli_args(existing, args)
        assert merged.wheels == ["/fake/base.whl"]


def test_override_from_cli_args_replaces_values():
    """Override should replace values when provided."""
    existing = ChubProject(
        wheels=["/fake/base.whl", "extra.whl"],
        entrypoint="main:old",
        metadata={"author": "John", "version": "1.0"},
        includes=[],
        scripts=Scripts()
    )

    with patch("pychub.model.chubproject_model.get_wheel_name_version", return_value=("new-pkg", "2.0")):
        with patch("pychub.model.chubproject_model.os.getcwd", return_value="/fake/cwd"):
            args = {
                "wheel": "/fake/new.whl",
                "metadata_entry": ["version=2.0", "tags=test"]
            }

            overridden = ChubProject.override_from_cli_args(existing, args)

            assert overridden.metadata["author"] == "John"  # preserved
            assert overridden.metadata["version"] == "2.0"  # overridden
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
                    "wheel": ["test.whl"]
                }
            }
        }
    }

    result = ChubProject._select_package_table(doc, "pyproject.toml")
    captured = capsys.readouterr()

    assert result is not None
    assert result["wheel"] == ["test.whl"]
    assert "enabled" in captured.out


def test_select_package_table_unrecognized(capsys):
    """Unrecognized filename should return None."""
    doc = {"wheel": ["test.whl"]}

    result = ChubProject._select_package_table(doc, "random.toml")
    captured = capsys.readouterr()

    assert result is None
    assert "unrecognized" in captured.out


# ============================================================
# Test ChubProject.determine_table_path
# ============================================================

def test_determine_table_path_pyproject():
    """pyproject.toml should always return default table."""
    result = ChubProject.determine_table_path(Path("pyproject.toml"), None)
    assert result == "tool.pychub.package"


def test_determine_table_path_chubproject_flat():
    """chubproject.toml with 'flat' arg should return None."""
    result = ChubProject.determine_table_path(Path("chubproject.toml"), "flat")
    assert result is None


def test_determine_table_path_invalid_filename():
    """Invalid filename should raise ValueError."""
    with pytest.raises(ValueError, match="Invalid chubproject_path"):
        ChubProject.determine_table_path(Path("invalid.toml"), None)


# ============================================================
# Test ChubProject.load_file
# ============================================================

def test_load_file_not_found():
    """load_file should raise ChubProjectError when file doesn't exist."""
    with patch("pychub.model.chubproject_model.Path.is_file", return_value=False):
        with pytest.raises(ChubProjectError, match="Project file not found"):
            ChubProject.load_file("/nonexistent/path/file.toml")


def test_load_file_invalid_toml():
    """load_file should raise ChubProjectError when TOML is invalid."""
    mock_path = MagicMock()
    mock_path.is_file.return_value = True
    mock_path.open.return_value.__enter__.return_value.read.side_effect = Exception("Invalid TOML")

    with patch("pychub.model.chubproject_model.Path", return_value=mock_path):
        with pytest.raises(ChubProjectError, match="Failed to parse TOML"):
            ChubProject.load_file("/fake/bad.toml")


def test_load_file_success():
    """load_file should successfully load and parse a valid TOML file."""
    toml_content = b"""
[pychub.package]
wheel = ["/fake/test.whl"]
entrypoint = "main:run"
"""

    mock_file = io.BytesIO(toml_content)

    with patch("pychub.model.chubproject_model.Path") as mock_path_class:
        mock_path_instance = MagicMock()
        mock_path_instance.is_file.return_value = True
        mock_path_instance.open.return_value.__enter__.return_value = mock_file
        mock_path_instance.as_posix.return_value = "/fake/chubproject.toml"
        mock_path_instance.name = "chubproject.toml"
        mock_path_class.return_value.expanduser.return_value.resolve.return_value = mock_path_instance

        # FIX: Pass Path object, not string
        with patch("pychub.model.chubproject_model.get_wheel_name_version", return_value=("test-pkg", "1.0.0")):
            proj = ChubProject.load_file(mock_path_instance)  # Changed from string

            assert proj.entrypoint == "main:run"


# ============================================================
# Test ChubProject.save_file
# ============================================================

def test_save_file_no_writer():
    """save_file should raise error when no TOML writer is available."""
    with patch("pychub.model.chubproject_model._TOML_WRITER", None):
        proj = ChubProject(wheels=["test.whl"], includes=[], metadata={}, scripts=Scripts())

        with pytest.raises(ChubProjectError, match="Saving requires a TOML writer"):
            ChubProject.save_file(proj, "/fake/output.toml")


def test_save_file_refuses_overwrite():
    """save_file should refuse to overwrite without overwrite=True."""
    proj = ChubProject(
        wheels=["test.whl"],
        includes=[],
        metadata={},
        scripts=Scripts(),
        entrypoint_args=[]  # ADD THIS
    )

    mock_writer = MagicMock()

    with patch("pychub.model.chubproject_model._TOML_WRITER", mock_writer):
        with patch("pychub.model.chubproject_model.Path") as mock_path_class:
            mock_path_instance = MagicMock()
            mock_path_instance.exists.return_value = True
            mock_path_class.return_value.expanduser.return_value.resolve.return_value = mock_path_instance

            with pytest.raises(ChubProjectError, match="Refusing to overwrite"):
                ChubProject.save_file(proj, "/fake/existing.toml", overwrite=False)


# ============================================================
# Test ChubProject utility methods
# ============================================================

def test_comma_split_maybe_none():
    """None should return empty list."""
    assert ChubProject._comma_split_maybe(None) == []


def test_comma_split_maybe_string():
    """String with commas should be split."""
    assert ChubProject._comma_split_maybe("a,b,c") == ["a", "b", "c"]


def test_flatten_nested_list():
    """Nested lists should be flattened."""
    assert ChubProject._flatten([["a", "b"], ["c"]]) == ["a", "b", "c"]


def test_dedup_with_duplicates():
    """list with duplicates should have duplicates removed."""
    assert ChubProject._dedup(["a", "b", "a", "c", "b"]) == ["a", "b", "c"]


def test_dedup_includes_with_duplicates():
    """Duplicate IncludeSpecs should be removed."""
    a = [IncludeSpec(src="a.txt", dest=None)]
    b = [IncludeSpec(src="a.txt", dest=None)]

    result = ChubProject._dedup_includes(a, b)
    assert len(result) == 1


# ============================================================
# Test ChubProject.to_mapping
# ============================================================

def test_to_mapping_minimal():
    """Minimal ChubProject should export to mapping."""
    proj = ChubProject(
        wheels=["test.whl"],
        includes=[],
        metadata={},
        scripts=Scripts(),
        entrypoint_args=[]  # ADD THIS
    )

    mapping = proj.to_mapping()
    assert mapping["wheels"] == ["test.whl"]


def test_to_mapping_complete():
    """Complete ChubProject should export all fields."""
    proj = ChubProject(
        wheels=["test.whl", "extra.whl"],
        chub="output.chub",
        entrypoint="main:run",
        includes=[IncludeSpec(src="file.txt", dest="dest/file.txt")],
        verbose=True,
        metadata={"author": "John"},
        scripts=Scripts.from_mapping({"pre": ["setup.sh"], "post": ["cleanup.sh"]}),
        entrypoint_args=[]  # ADD THIS
    )

    mapping = proj.to_mapping()
    assert mapping["wheels"] == ["test.whl", "extra.whl"]


# ============================================================
# Test ChubProject serialization
# ============================================================

def test_to_json():
    """to_json should serialize ChubProject to JSON string."""
    proj = ChubProject(
        wheels=["test.whl"],
        entrypoint="main:run",
        metadata={"author": "John"},
        includes=[],
        scripts=Scripts(),
        entrypoint_args=[]  # ADD THIS
    )

    json_str = proj.to_json()
    assert '"wheels"' in json_str


def test_to_yaml_raises_when_yaml_not_installed(monkeypatch):
    """to_yaml should raise RuntimeError when PyYAML is not installed."""
    import pychub.model.chubproject_model as mod

    original_yaml = mod.yaml
    monkeypatch.setattr(mod, "yaml", None)

    proj = ChubProject(wheels=["test.whl"], includes=[], scripts=Scripts())

    with pytest.raises(RuntimeError, match="PyYAML not installed"):
        proj.to_yaml()

    monkeypatch.setattr(mod, "yaml", original_yaml)


def test_chubproject_has_slots():
    """Validate that ChubProject uses slots when supported."""
    config = ChubProject()
    cls = type(config)

    if sys.version_info >= (3, 10):
        assert hasattr(cls, "__slots__"), "Expected __slots__ on 3.10+"
        assert not hasattr(config, "__dict__"), "Expected __dict__ to be removed on 3.10+"
    else:
        assert not hasattr(cls, "__slots__"), "__slots__ should not exist under shimmed 3.9"
        assert hasattr(config, "__dict__"), "Shimmed 3.9 should still have __dict__"


def test_from_mapping_with_wheel_extraction():
    """Test that from_mapping calls get_wheel_name_version properly."""
    with patch("pychub.model.chubproject_model.get_wheel_name_version", return_value=("pkg", "2.0")) as mock_get:
        mapping = {"wheels": ["/fake/wheel.whl"]}
        proj = ChubProject.from_mapping(mapping)

        mock_get.assert_called_once()
        assert proj.name == "pkg"
        assert proj.version == "2.0"


def test_to_yaml():
    """to_yaml should serialize to YAML."""
    proj = ChubProject(
        wheels=["test.whl"],
        includes=[],
        metadata={},
        scripts=Scripts(),
        entrypoint_args=[]  # ADD THIS
    )
    yaml_str = proj.to_yaml()
    assert "wheels" in yaml_str


def test_save_file_success(tmp_path):
    """Test save_file actually writes."""
    proj = ChubProject(wheels=["test.whl"], includes=[], metadata={}, scripts=Scripts(), entrypoint_args=[])

    mock_writer = MagicMock()
    mock_writer.dumps.return_value = "[tool.pychub.package]\nwheels = [\"test.whl\"]\n"

    with patch("pychub.model.chubproject_model._TOML_WRITER", mock_writer):
        output = tmp_path / "out.toml"
        result = ChubProject.save_file(proj, output, overwrite=True)
        assert result.exists()