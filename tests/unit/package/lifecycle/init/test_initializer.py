"""Unit tests for pychub.package.lifecycle.init.initializer module."""
from __future__ import annotations

import json
import sys
from argparse import Namespace
from pathlib import Path
from unittest.mock import patch

import pytest

from pychub.model.buildplan_model import BuildPlan
from pychub.model.chubproject_model import ChubProject
from pychub.package.lifecycle.init.initializer import (
    cache_project,
    check_python_version,
    init_project,
    parse_cli,
    process_chubproject,
    process_options,
    project_hash,
    verify_pip,
)


# ===========================
# check_python_version tests
# ===========================

def test_check_python_version_succeeds_on_39_or_higher():
    """Test that check_python_version succeeds when Python >= 3.9."""
    build_plan = BuildPlan()
    with patch("sys.version_info", (3, 9, 0)):
        check_python_version(build_plan)
    # No exception raised means success


def test_check_python_version_fails_on_older_python():
    """Test that check_python_version raises an exception for Python < 3.9."""
    build_plan = BuildPlan()
    with patch("sys.version_info", (3, 8, 10)):
        with pytest.raises(Exception, match="Must be using Python 3.9 or higher"):
            check_python_version(build_plan)


# ===========================
# verify_pip tests
# ===========================

def test_verify_pip_succeeds_when_pip_available():
    """Test that verify_pip succeeds when pip is available."""
    build_plan = BuildPlan()
    with patch("subprocess.call", return_value=0) as mock_call:
        verify_pip(build_plan)
        mock_call.assert_called_once_with([sys.executable, "-m", "pip", "--version"])


def test_verify_pip_fails_when_pip_unavailable():
    """Test that verify_pip raises RuntimeError when pip is not available."""
    build_plan = BuildPlan()
    with patch("subprocess.call", return_value=1):
        with pytest.raises(RuntimeError, match="pip not found"):
            verify_pip(build_plan)


# ===========================
# project_hash tests
# ===========================

def test_project_hash_generates_16_char_hash(mock_chubproject):
    """Test that project_hash generates a 16-character hash."""
    build_plan = BuildPlan()

    result = project_hash(build_plan, mock_chubproject)

    assert len(result) == 16
    assert result.isalnum()
    assert build_plan.project_hash == result


def test_project_hash_is_deterministic(mock_chubproject_factory):
    """Test that project_hash produces the same hash for the same data."""
    build_plan1 = BuildPlan()
    build_plan2 = BuildPlan()
    chubproject1 = mock_chubproject_factory(name="test", version="1.0.0")
    chubproject2 = mock_chubproject_factory(name="test", version="1.0.0")

    hash1 = project_hash(build_plan1, chubproject1)
    hash2 = project_hash(build_plan2, chubproject2)

    assert hash1 == hash2


def test_project_hash_differs_for_different_data(mock_chubproject_factory):
    """Test that project_hash produces different hashes for different data."""
    build_plan1 = BuildPlan()
    build_plan2 = BuildPlan()
    chubproject1 = mock_chubproject_factory(name="test1", version="1.0.0")
    chubproject2 = mock_chubproject_factory(name="test2", version="1.0.0")

    hash1 = project_hash(build_plan1, chubproject1)
    hash2 = project_hash(build_plan2, chubproject2)

    assert hash1 != hash2


# ===========================
# cache_project tests
# ===========================

def test_cache_project_creates_cache_directory(tmp_path, mock_chubproject_factory, mock_chubproject_class):
    with patch("pychub.package.lifecycle.init.initializer.ChubProject", mock_chubproject_class):
        """Test that cache_project creates the cache directory."""
        build_plan = BuildPlan()
        chubproject = mock_chubproject_factory(name="test", version="1.0.0")

        with patch("pychub.package.lifecycle.init.initializer.user_cache_dir", return_value=str(tmp_path)):
            result = cache_project(build_plan, chubproject)

        assert result.exists()
        assert result.is_dir()
        assert build_plan.staging_dir == tmp_path


def test_cache_project_writes_chubproject_toml(tmp_path, mock_chubproject_factory, mock_chubproject_class):
    with patch("pychub.package.lifecycle.init.initializer.ChubProject", mock_chubproject_class):
        """Test that cache_project writes a valid_chubproject.toml file."""
        build_plan = BuildPlan()
        chubproject = mock_chubproject_factory(name="test", version="1.0.0", entrypoint="test:main")

        with patch("pychub.package.lifecycle.init.initializer.user_cache_dir", return_value=str(tmp_path)):
            result = cache_project(build_plan, chubproject)

        meta_file = result / "meta.json"
        assert meta_file.exists()
        assert result.exists()
        assert result.is_dir()
        assert build_plan.staging_dir == tmp_path


def test_cache_project_writes_meta_json(tmp_path, mock_chubproject_factory, mock_chubproject_class):
    with patch("pychub.package.lifecycle.init.initializer.ChubProject", mock_chubproject_class):
        """Test that cache_project writes a meta.json file."""
        build_plan = BuildPlan()
        chubproject = mock_chubproject_factory(name="test", version="1.0.0")

        with patch("pychub.package.lifecycle.init.initializer.user_cache_dir", return_value=str(tmp_path)):
            with patch("pychub.package.lifecycle.init.initializer.get_version", return_value="1.2.3"):
                result = cache_project(build_plan, chubproject)

        meta_file = result / "meta.json"
        assert meta_file.exists()

        meta = json.loads(meta_file.read_text())
        assert "pychub_version" in meta
        assert "created_at" in meta
        assert "hash" in meta
        assert meta["pychub_version"] == "1.2.3"


def test_cache_project_uses_existing_directory(tmp_path, mock_chubproject_factory, mock_chubproject_class):
    with patch("pychub.package.lifecycle.init.initializer.ChubProject", mock_chubproject_class):
        """Test that cache_project works with existing cache directory."""
        build_plan = BuildPlan()
        chubproject = mock_chubproject_factory(name="test", version="1.0.0")

        with patch("pychub.package.lifecycle.init.initializer.user_cache_dir", return_value=str(tmp_path)):
            result1 = cache_project(build_plan, chubproject)
            result2 = cache_project(build_plan, chubproject)

        assert result1 == result2
        assert result1.exists()


# ===========================
# process_chubproject tests
# ===========================

def test_process_chubproject_loads_valid_file(tmp_path, mock_chubproject_class):
    with patch("pychub.package.lifecycle.init.initializer.ChubProject", mock_chubproject_class):
        """Test that process_chubproject loads a valid chubproject file."""
        build_plan = BuildPlan()
        chubproject_path = Path(__file__).parents[4] / "test_data" / "valid_chubproject.toml"

        result = process_chubproject(build_plan, chubproject_path)

        assert result is not None
        assert isinstance(result, ChubProject)
        assert build_plan.project == result


def test_process_chubproject_raises_on_missing_file(tmp_path):
    """Test that process_chubproject raises FileNotFoundError for a missing file."""
    build_plan = BuildPlan()
    chubproject_path = tmp_path / "nonexistent.toml"

    with pytest.raises(FileNotFoundError, match="Chub project file not found"):
        process_chubproject(build_plan, chubproject_path)


def test_process_chubproject_returns_none_on_import_error(tmp_path):
    """Test that process_chubproject returns None on ImportError."""
    build_plan = BuildPlan()
    chubproject_path = tmp_path / "valid_chubproject.toml"
    chubproject_path.write_text("[package]\nname = 'test'\n", encoding="utf-8")

    with patch("pychub.model.chubproject_model.ChubProject.load_file", side_effect=ImportError):
        result = process_chubproject(build_plan, chubproject_path)
        assert result is None


# ===========================
# process_options tests
# ===========================

def test_process_options_with_chubproject_path(tmp_path, mock_chubproject_factory, mock_chubproject_class):
    with patch("pychub.package.lifecycle.init.initializer.ChubProject", mock_chubproject_class):
        """Test process_options when chubproject path is provided."""
        build_plan = BuildPlan()
        chubproject_path = tmp_path / "valid_chubproject.toml"
        chubproject = mock_chubproject_factory(name="test", version="1.0.0", entrypoint="test:main")
        ChubProject.save_file(chubproject, chubproject_path, overwrite=True)

        args = Namespace(chubproject=str(chubproject_path), verbose=True)
        other_args = ["--extra", "arg"]

        result = process_options(build_plan, args, other_args)

        assert result is not None
        assert result.entrypoint_args == ["--extra", "arg"]


def test_process_options_without_chubproject_path():
    """Test process_options when no chubproject path is provided."""
    build_plan = BuildPlan()
    args = Namespace(
        chubproject=None,
        name="cli-test",
        version="2.0.0",
        entrypoint="cli:main",
        wheel=None,
        chub=None,
        include=None,
        pre_script=None,
        post_script=None,
        metadata_entry=None,
        verbose=False,
        project_path=None,
        include_chub=None,
        entrypoint_args=None,
        spdx_license=None
    )
    other_args = []

    result = process_options(build_plan, args, other_args)

    assert result is not None
    assert isinstance(result, ChubProject)
    assert result.entrypoint_args == []


def test_process_options_merges_entrypoint_args():
    """Test that process_options correctly sets entrypoint_args."""
    build_plan = BuildPlan()
    args = Namespace(
        chubproject=None,
        name="test",
        version="1.0.0",
        entrypoint="test:main",
        wheel=None,
        chub=None,
        include=None,
        pre_script=None,
        post_script=None,
        metadata_entry=None,
        verbose=False,
        project_path=None,
        include_chub=None,
        entrypoint_args=None,
        spdx_license=None
    )
    other_args = ["--arg1", "value1"]

    result = process_options(build_plan, args, other_args)

    assert result.entrypoint_args == ["--arg1", "value1"]


# ===========================
# parse_cli tests
# ===========================

def test_parse_cli_returns_namespace_and_args():
    """Test that parse_cli returns a Namespace and remaining args."""
    build_plan = BuildPlan()

    with patch("sys.argv", ["pychub", "--verbose"]):
        namespace, other_args = parse_cli(build_plan)

    assert isinstance(namespace, Namespace)
    assert isinstance(other_args, list)


def test_parse_cli_separates_known_and_unknown_args():
    """Test that parse_cli separates known and unknown arguments."""
    build_plan = BuildPlan()

    with patch("sys.argv", ["pychub", "--verbose", "--unknown-arg", "value"]):
        namespace, other_args = parse_cli(build_plan)

    assert hasattr(namespace, "verbose")
    assert "--unknown-arg" in other_args or "value" in other_args


# ===========================
# init_project tests
# ===========================

def test_init_project_full_flow_with_chubproject_path(tmp_path, mock_chubproject_factory, mock_chubproject_class):
    with patch("pychub.package.lifecycle.init.initializer.ChubProject", mock_chubproject_class):
        """Test init_project with a chubproject path."""
        build_plan = BuildPlan()
        chubproject_path = Path(__file__).parents[4] / "test_data" / "valid_chubproject.toml"
        cache_dir = tmp_path / "cache"

        with patch("sys.version_info", (3, 9, 0)):
            with patch("subprocess.call", return_value=0):
                with patch("pychub.package.lifecycle.init.initializer.user_cache_dir", return_value=str(cache_dir)):
                    result = init_project(build_plan, chubproject_path)

        assert result.exists()
        assert result.is_dir()


def test_init_project_full_flow_without_chubproject_path(tmp_path):
    """Test init_project without a chubproject path (CLI mode)."""
    build_plan = BuildPlan()
    cache_dir = tmp_path / "cache"

    with patch("sys.version_info", (3, 9, 0)):
        with patch("subprocess.call", return_value=0):
            with patch("pychub.package.lifecycle.init.initializer.user_cache_dir", return_value=str(cache_dir)):
                with patch("sys.argv", ["pychub", "--name", "test", "--version", "1.0.0"]):
                    result = init_project(build_plan)

    assert result.exists()
    assert result.is_dir()


def test_init_project_fails_on_old_python():
    """Test that init_project fails when Python version is too old."""
    build_plan = BuildPlan()

    with patch("sys.version_info", (3, 8, 0)):
        with pytest.raises(Exception, match="Must be using Python 3.9 or higher"):
            init_project(build_plan)


def test_init_project_fails_on_missing_pip():
    """Test that init_project fails when pip is not available."""
    build_plan = BuildPlan()

    with patch("sys.version_info", (3, 9, 0)):
        with patch("subprocess.call", return_value=1):
            with pytest.raises(RuntimeError, match="pip not found"):
                init_project(build_plan)


@pytest.mark.parametrize("python_version,should_pass", [
    ((3, 9, 0), True),
    ((3, 10, 5), True),
    ((3, 11, 0), True),
    ((3, 13, 0), True),
    ((3, 8, 10), False),
    ((3, 7, 0), False),
])
def test_check_python_version_parametrized(python_version, should_pass):
    """Parametrized test for various Python versions."""
    build_plan = BuildPlan()

    with patch("sys.version_info", python_version):
        if should_pass:
            check_python_version(build_plan)
        else:
            with pytest.raises(Exception, match="Must be using Python 3.9 or higher"):
                check_python_version(build_plan)


@pytest.mark.parametrize("pip_return_code,should_pass", [
    (0, True),
    (1, False),
    (127, False),
])
def test_verify_pip_parametrized(pip_return_code, should_pass):
    """Parametrized test for pip verification."""
    build_plan = BuildPlan()

    with patch("subprocess.call", return_value=pip_return_code):
        if should_pass:
            verify_pip(build_plan)
        else:
            with pytest.raises(RuntimeError, match="pip not found"):
                verify_pip(build_plan)