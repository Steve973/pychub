from argparse import Namespace
from importlib.metadata import PackageNotFoundError
from pathlib import Path
from unittest.mock import Mock

import pytest

from pychub.model.chubproject_model import ChubProject
from pychub.package import bt_options_processor


# ============================================================================
# parse_chubproject tests
# ============================================================================

def test_parse_chubproject_file_not_found():
    """Test that parse_chubproject raises FileNotFoundError for missing file."""
    missing_path = Path("/nonexistent/file.toml")

    with pytest.raises(FileNotFoundError) as exc_info:
        bt_options_processor.parse_chubproject(missing_path)

    assert "Chub project file not found" in str(exc_info.value)


def test_parse_chubproject_success(monkeypatch, tmp_path):
    """Test that parse_chubproject loads and returns a ChubProject."""
    config_file = tmp_path / "chubproject.toml"
    config_file.write_text('wheel = "test.whl"', encoding="utf-8")

    mock_project = Mock(spec=ChubProject)
    mock_load = Mock(return_value=mock_project)
    monkeypatch.setattr(bt_options_processor, "load_chubproject", mock_load)

    result = bt_options_processor.parse_chubproject(config_file)

    assert result == mock_project
    mock_load.assert_called_once_with(config_file)


def test_parse_chubproject_import_error(monkeypatch, tmp_path, capsys):
    """Test that parse_chubproject handles ImportError gracefully."""
    config_file = tmp_path / "chubproject.toml"
    config_file.write_text('wheel = "test.whl"', encoding="utf-8")

    def mock_load(path):
        raise ImportError("mock import error")

    monkeypatch.setattr(bt_options_processor, "load_chubproject", mock_load)

    result = bt_options_processor.parse_chubproject(config_file)

    # Should print error message and return None
    captured = capsys.readouterr()
    assert "pychub: (not installed)" in captured.out
    assert result is None


# ============================================================================
# process_chubproject tests
# ============================================================================

def test_process_chubproject_calls_parse_and_build(monkeypatch, tmp_path):
    """Test that process_chubproject calls parse_chubproject and build_chub."""
    config_file = tmp_path / "chubproject.toml"
    config_file.write_text('wheel = "test.whl"', encoding="utf-8")

    mock_project = Mock(spec=ChubProject)
    mock_parse = Mock(return_value=mock_project)
    mock_build = Mock()

    monkeypatch.setattr(bt_options_processor, "parse_chubproject", mock_parse)
    monkeypatch.setattr(bt_options_processor, "build_chub", mock_build)

    bt_options_processor.process_chubproject(config_file)

    mock_parse.assert_called_once_with(config_file)
    mock_build.assert_called_once_with(mock_project)


# ============================================================================
# process_options tests - version flag
# ============================================================================

def test_process_options_version_flag_with_installed_package(monkeypatch, capsys):
    """Test --version flag when pychub is installed."""
    args = Namespace(version=True, chubproject=None)

    mock_get_version = Mock(return_value="1.2.3")
    monkeypatch.setattr(bt_options_processor, "get_version", mock_get_version)

    bt_options_processor.process_options(args)

    captured = capsys.readouterr()
    assert "Python:" in captured.out
    assert "pychub: 1.2.3" in captured.out
    mock_get_version.assert_called_once_with("pychub")


def test_process_options_version_flag_not_installed(monkeypatch, capsys):
    """Test --version flag when pychub is not installed."""
    args = Namespace(version=True, chubproject=None)

    def mock_get_version(name):
        raise PackageNotFoundError(f"{name} not found")

    monkeypatch.setattr(bt_options_processor, "get_version", mock_get_version)

    bt_options_processor.process_options(args)

    captured = capsys.readouterr()
    assert "Python:" in captured.out
    assert "pychub: (source)" in captured.out


# ============================================================================
# process_options tests - chubproject file
# ============================================================================

def test_process_options_with_chubproject_file(monkeypatch, tmp_path):
    """Test process_options with --chubproject file."""
    config_file = tmp_path / "chubproject.toml"
    config_file.write_text('wheel = "test.whl"', encoding="utf-8")

    args = Namespace(
        version=False,
        chubproject=config_file,
        analyze_compatibility=False,
        chubproject_save=None,
        wheel="override.whl"
    )

    mock_project = Mock(spec=ChubProject)
    mock_merged = Mock(spec=ChubProject)

    mock_parse = Mock(return_value=mock_project)
    mock_override = Mock(return_value=mock_merged)
    mock_build = Mock()

    monkeypatch.setattr(bt_options_processor, "parse_chubproject", mock_parse)
    monkeypatch.setattr(ChubProject, "override_from_cli_args", mock_override)
    monkeypatch.setattr(bt_options_processor, "build_chub", mock_build)

    bt_options_processor.process_options(args)

    mock_parse.assert_called_once()
    assert mock_parse.call_args[0][0] == config_file
    mock_override.assert_called_once_with(mock_project, vars(args))
    mock_build.assert_called_once_with(mock_merged)


def test_process_options_without_chubproject_file(monkeypatch):
    """Test process_options without --chubproject file."""
    args = Namespace(
        version=False,
        chubproject=None,
        analyze_compatibility=False,
        chubproject_save=None,
        wheel="test.whl"
    )

    mock_project = Mock(spec=ChubProject)
    mock_from_cli = Mock(return_value=mock_project)
    mock_build = Mock()

    monkeypatch.setattr(ChubProject, "from_cli_args", mock_from_cli)
    monkeypatch.setattr(bt_options_processor, "build_chub", mock_build)

    bt_options_processor.process_options(args)

    mock_from_cli.assert_called_once_with(vars(args))
    mock_build.assert_called_once_with(mock_project)


# ============================================================================
# process_options tests - analyze_compatibility
# ============================================================================

def test_process_options_analyze_compatibility_with_results(monkeypatch, capsys):
    """Test --analyze-compatibility with valid combos."""
    args = Namespace(
        version=False,
        chubproject=None,
        analyze_compatibility=True,
        chubproject_save=None,
        wheel="test.whl"
    )

    mock_project = Mock(spec=ChubProject)
    mock_from_cli = Mock(return_value=mock_project)
    mock_analyze = Mock(return_value=["cp310-cp310-linux_x86_64", "cp311-cp311-linux_x86_64"])

    monkeypatch.setattr(ChubProject, "from_cli_args", mock_from_cli)
    monkeypatch.setattr(bt_options_processor, "analyze_compatibility", mock_analyze)

    with pytest.raises(SystemExit) as exc_info:
        bt_options_processor.process_options(args)

    assert exc_info.value.code == 0

    captured = capsys.readouterr()
    assert "Supported compatibility targets:" in captured.out
    assert "cp310-cp310-linux_x86_64" in captured.out
    assert "cp311-cp311-linux_x86_64" in captured.out

    mock_analyze.assert_called_once_with(mock_project)


def test_process_options_analyze_compatibility_no_results(monkeypatch, capsys):
    """Test --analyze-compatibility with no valid combos."""
    args = Namespace(
        version=False,
        chubproject=None,
        analyze_compatibility=True,
        chubproject_save=None,
        wheel="test.whl"
    )

    mock_project = Mock(spec=ChubProject)
    mock_from_cli = Mock(return_value=mock_project)
    mock_analyze = Mock(return_value=[])

    monkeypatch.setattr(ChubProject, "from_cli_args", mock_from_cli)
    monkeypatch.setattr(bt_options_processor, "analyze_compatibility", mock_analyze)

    with pytest.raises(SystemExit) as exc_info:
        bt_options_processor.process_options(args)

    assert exc_info.value.code == 0

    captured = capsys.readouterr()
    assert "WARNING: No valid compatibility targets found!" in captured.out


# ============================================================================
# process_options tests - chubproject_save
# ============================================================================

def test_process_options_saves_chubproject(monkeypatch, tmp_path):
    """Test --chubproject-save saves the project."""
    output_file = tmp_path / "output.toml"

    args = Namespace(
        version=False,
        chubproject=None,
        analyze_compatibility=False,
        chubproject_save=output_file,
        wheel="test.whl"
    )

    mock_project = Mock(spec=ChubProject)
    mock_from_cli = Mock(return_value=mock_project)
    mock_save = Mock()
    mock_build = Mock()

    monkeypatch.setattr(ChubProject, "from_cli_args", mock_from_cli)
    monkeypatch.setattr(bt_options_processor, "save_chubproject", mock_save)
    monkeypatch.setattr(bt_options_processor, "build_chub", mock_build)

    bt_options_processor.process_options(args)

    mock_save.assert_called_once()
    assert mock_save.call_args[0][0] == mock_project
    assert mock_save.call_args[0][1] == output_file
    assert mock_save.call_args[1]["overwrite"] is True
    assert mock_save.call_args[1]["make_parents"] is True

    mock_build.assert_called_once_with(mock_project)


def test_process_options_with_chubproject_and_save(monkeypatch, tmp_path):
    """Test loading from chubproject and saving to another file."""
    input_file = tmp_path / "input.toml"
    output_file = tmp_path / "output.toml"
    input_file.write_text('wheel = "test.whl"', encoding="utf-8")

    args = Namespace(
        version=False,
        chubproject=input_file,
        analyze_compatibility=False,
        chubproject_save=output_file,
        wheel="test.whl"
    )

    mock_project = Mock(spec=ChubProject)
    mock_merged = Mock(spec=ChubProject)

    mock_parse = Mock(return_value=mock_project)
    mock_override = Mock(return_value=mock_merged)
    mock_save = Mock()
    mock_build = Mock()

    monkeypatch.setattr(bt_options_processor, "parse_chubproject", mock_parse)
    monkeypatch.setattr(ChubProject, "override_from_cli_args", mock_override)
    monkeypatch.setattr(bt_options_processor, "save_chubproject", mock_save)
    monkeypatch.setattr(bt_options_processor, "build_chub", mock_build)

    bt_options_processor.process_options(args)

    mock_parse.assert_called_once()
    mock_override.assert_called_once_with(mock_project, vars(args))
    mock_save.assert_called_once_with(mock_merged, output_file, overwrite=True, make_parents=True)
    mock_build.assert_called_once_with(mock_merged)


# ============================================================================
# process_options tests - full workflow
# ============================================================================

def test_process_options_full_workflow_no_flags(monkeypatch):
    """Test full workflow without any special flags."""
    args = Namespace(
        version=False,
        chubproject=None,
        analyze_compatibility=False,
        chubproject_save=None,
        wheel="test.whl",
        verbose=True
    )

    mock_project = Mock(spec=ChubProject)
    mock_from_cli = Mock(return_value=mock_project)
    mock_build = Mock()

    monkeypatch.setattr(ChubProject, "from_cli_args", mock_from_cli)
    monkeypatch.setattr(bt_options_processor, "build_chub", mock_build)

    bt_options_processor.process_options(args)

    mock_from_cli.assert_called_once_with(vars(args))
    mock_build.assert_called_once_with(mock_project)


def test_process_options_chubproject_path_expansion(monkeypatch, tmp_path):
    """Test that chubproject path is expanded and resolved."""
    # Create a file we can reference
    config_file = tmp_path / "chubproject.toml"
    config_file.write_text('wheel = "test.whl"', encoding="utf-8")

    # Use a path with ~ or relative components
    args = Namespace(
        version=False,
        chubproject=config_file,
        analyze_compatibility=False,
        chubproject_save=None,
        wheel="test.whl"
    )

    mock_project = Mock(spec=ChubProject)
    mock_merged = Mock(spec=ChubProject)

    parse_call_tracker = {"called_with": None}

    def track_parse(path):
        parse_call_tracker["called_with"] = path
        return mock_project

    mock_override = Mock(return_value=mock_merged)
    mock_build = Mock()

    monkeypatch.setattr(bt_options_processor, "parse_chubproject", track_parse)
    monkeypatch.setattr(ChubProject, "override_from_cli_args", mock_override)
    monkeypatch.setattr(bt_options_processor, "build_chub", mock_build)

    bt_options_processor.process_options(args)

    # Verify the path was resolved
    called_path = parse_call_tracker["called_with"]
    assert called_path.is_absolute()
    assert called_path == config_file.resolve()


def test_process_options_chubproject_save_path_expansion(monkeypatch, tmp_path):
    """Test that chubproject_save path is expanded and resolved."""
    output_file = tmp_path / "output.toml"

    args = Namespace(
        version=False,
        chubproject=None,
        analyze_compatibility=False,
        chubproject_save=output_file,
        wheel="test.whl"
    )

    mock_project = Mock(spec=ChubProject)

    save_call_tracker = {"called_with": None}

    def track_save(project, path, **kwargs):
        save_call_tracker["called_with"] = path

    mock_from_cli = Mock(return_value=mock_project)
    mock_build = Mock()

    monkeypatch.setattr(ChubProject, "from_cli_args", mock_from_cli)
    monkeypatch.setattr(bt_options_processor, "save_chubproject", track_save)
    monkeypatch.setattr(bt_options_processor, "build_chub", mock_build)

    bt_options_processor.process_options(args)

    # Verify the path was resolved
    called_path = save_call_tracker["called_with"]
    assert called_path.is_absolute()
    assert called_path == output_file.resolve()