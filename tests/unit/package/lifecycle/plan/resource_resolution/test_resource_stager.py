"""Unit tests for resource_stager module."""
from pathlib import Path, PurePath
from unittest.mock import Mock, MagicMock, patch

import pytest

from pychub.model.includes_model import IncludeSpec
from pychub.package.lifecycle.plan.resource_resolution import resource_stager


# Tests for _sanitize()

def test_sanitize_simple_filename():
    """Test _sanitize with a simple filename."""
    result = resource_stager._sanitize("script.sh")
    assert result == "script.sh"


def test_sanitize_path_with_directories():
    """Test _sanitize converts directory separators to underscores."""
    result = resource_stager._sanitize("path/to/script.sh")
    assert result == "path_to_script.sh"


def test_sanitize_removes_special_characters():
    """Test _sanitize removes special characters."""
    result = resource_stager._sanitize("my script!@#$%.sh")
    assert result == "my_script_.sh"


def test_sanitize_empty_string():
    """Test _sanitize with empty string returns 'script'."""
    result = resource_stager._sanitize("")
    assert result == "script"


def test_sanitize_only_dots_and_slashes():
    """Test _sanitize filters out '.', '..', '/', and empty parts."""
    result = resource_stager._sanitize("./../../.")
    assert result == "script"


def test_sanitize_dot_in_filename():
    """Test _sanitize keeps dots that are part of filename (not path parts)."""
    result = resource_stager._sanitize("file.name.txt")
    assert result == "file.name.txt"


def test_sanitize_current_directory():
    """Test _sanitize with current directory reference returns 'script'."""
    result = resource_stager._sanitize(".")
    assert result == "script"


def test_sanitize_parent_directory():
    """Test _sanitize with parent directory reference returns 'script'."""
    result = resource_stager._sanitize("..")
    assert result == "script"


def test_sanitize_multiple_underscores():
    """Test _sanitize collapses multiple underscores."""
    result = resource_stager._sanitize("a___b___c")
    assert result == "a_b_c"


def test_sanitize_purepath_input():
    """Test _sanitize accepts PurePath input."""
    result = resource_stager._sanitize(PurePath("path/to/file.txt"))
    assert result == "path_to_file.txt"


def test_sanitize_removes_leading_trailing_underscores():
    """Test _sanitize strips leading/trailing underscores."""
    result = resource_stager._sanitize("___file___")
    assert result == "file"


def test_sanitize_absolute_path():
    """Test _sanitize handles absolute paths by filtering out '/'."""
    result = resource_stager._sanitize("/usr/bin/script.sh")
    assert result == "usr_bin_script.sh"


def test_sanitize_windows_style_path():
    """Test _sanitize with backslash separators."""
    result = resource_stager._sanitize(PurePath("path\\to\\file.txt"))
    assert result == "path_to_file.txt"


def test_sanitize_mixed_special_chars_and_underscores():
    """Test _sanitize handles mixed special characters."""
    result = resource_stager._sanitize("a__b!!c__d")
    assert result == "a_b_c_d"


def test_sanitize_only_special_characters():
    """Test _sanitize with only special characters returns 'script'."""
    result = resource_stager._sanitize("!@#$%^&*()")
    assert result == "script"


# Tests for prefixed_script_names()

def test_prefixed_script_names_empty_list():
    """Test prefixed_script_names with empty list."""
    result = resource_stager.prefixed_script_names([])
    assert result == []


def test_prefixed_script_names_single_item():
    """Test prefixed_script_names with one item."""
    result = resource_stager.prefixed_script_names(["script.sh"])
    assert len(result) == 1
    assert result[0][0] == Path("script.sh")
    assert result[0][1] == "00_script.sh"


def test_prefixed_script_names_multiple_items():
    """Test prefixed_script_names with multiple items."""
    result = resource_stager.prefixed_script_names(["a.sh", "b.sh", "c.sh"])
    assert len(result) == 3
    assert result[0] == (Path("a.sh"), "00_a.sh")
    assert result[1] == (Path("b.sh"), "01_b.sh")
    assert result[2] == (Path("c.sh"), "02_c.sh")


def test_prefixed_script_names_preserves_order():
    """Test prefixed_script_names preserves input order."""
    inputs = ["z.sh", "a.sh", "m.sh"]
    result = resource_stager.prefixed_script_names(inputs)
    assert result[0][1] == "00_z.sh"
    assert result[1][1] == "01_a.sh"
    assert result[2][1] == "02_m.sh"


def test_prefixed_script_names_handles_duplicates():
    """Test prefixed_script_names deduplicates same names."""
    result = resource_stager.prefixed_script_names(["script.sh", "script.sh"])
    assert len(result) == 2
    assert result[0][1] == "00_script.sh"
    assert result[1][1] == "01_script(1).sh"


def test_prefixed_script_names_handles_case_insensitive_duplicates():
    """Test prefixed_script_names treats names case-insensitively."""
    result = resource_stager.prefixed_script_names(["Script.sh", "script.sh", "SCRIPT.sh"])
    assert len(result) == 3
    assert result[0][1] == "00_Script.sh"
    assert result[1][1] == "01_script(1).sh"
    assert result[2][1] == "02_SCRIPT(2).sh"


def test_prefixed_script_names_width_grows_for_100_items():
    """Test prefixed_script_names uses 3-digit prefix for 100+ items."""
    items = [f"script{i}.sh" for i in range(101)]
    result = resource_stager.prefixed_script_names(items)
    assert result[0][1].startswith("000_")
    assert result[99][1].startswith("099_")


def test_prefixed_script_names_handles_path_objects():
    """Test prefixed_script_names accepts Path objects."""
    result = resource_stager.prefixed_script_names([Path("test.sh")])
    assert result[0][0] == Path("test.sh")
    assert result[0][1] == "00_test.sh"


def test_prefixed_script_names_no_extension():
    """Test prefixed_script_names with files without extensions."""
    result = resource_stager.prefixed_script_names(["script"])
    assert result[0][1] == "00_script"


def test_prefixed_script_names_duplicate_no_extension():
    """Test prefixed_script_names deduplicates files without extensions."""
    result = resource_stager.prefixed_script_names(["script", "script"])
    assert result[0][1] == "00_script"
    assert result[1][1] == "01_script(1)"


# Tests for copy_runtime_files()

@patch('pychub.package.lifecycle.plan.resource_resolution.resource_stager.shutil.copytree')
def test_copy_runtime_files_success(mock_copytree, tmp_path):
    """Test copy_runtime_files copies runtime directory."""
    mock_plan = Mock()
    mock_plan.audit_log = []
    runtime_dir = tmp_path / "runtime"

    resource_stager.copy_runtime_files(mock_plan, runtime_dir)

    # Verify copytree was called once with dirs_exist_ok=True
    mock_copytree.assert_called_once()
    call_args = mock_copytree.call_args

    # First arg should be the source runtime path
    assert isinstance(call_args[0][0], Path)
    assert call_args[0][0].name == "runtime"

    # Second arg should be the destination
    assert call_args[0][1] == runtime_dir

    # Should have dirs_exist_ok=True
    assert call_args[1]['dirs_exist_ok'] is True


# Tests for absolutize_paths()

def test_absolutize_paths_single_absolute_path():
    """Test absolutize_paths with single absolute path."""
    result = resource_stager.absolutize_paths("/absolute/path", Path("/base"))
    assert result == "/absolute/path"


def test_absolutize_paths_single_relative_path(tmp_path):
    """Test absolutize_paths with single relative path."""
    base = tmp_path / "base"
    base.mkdir()
    result = resource_stager.absolutize_paths("relative/path", base)
    expected = str((base / "relative/path").resolve())
    assert result == expected


def test_absolutize_paths_list_of_paths(tmp_path):
    """Test absolutize_paths with list of paths."""
    base = tmp_path / "base"
    base.mkdir()
    result = resource_stager.absolutize_paths(["rel1", "rel2"], base)
    assert len(result) == 2
    assert result[0] == str((base / "rel1").resolve())
    assert result[1] == str((base / "rel2").resolve())


def test_absolutize_paths_mixed_absolute_relative(tmp_path):
    """Test absolutize_paths with mix of absolute and relative paths."""
    base = tmp_path / "base"
    base.mkdir()
    result = resource_stager.absolutize_paths(["/abs/path", "rel/path"], base)
    assert len(result) == 2
    assert result[0] == "/abs/path"
    assert result[1] == str((base / "rel/path").resolve())


def test_absolutize_paths_empty_list():
    """Test absolutize_paths with empty list."""
    result = resource_stager.absolutize_paths([], Path("/base"))
    assert result == []


# Tests for copy_included_files()

@patch('pychub.package.lifecycle.plan.resource_resolution.resource_stager.shutil.copy2')
def test_copy_included_files_empty_list(mock_copy2, tmp_path):
    """Test copy_included_files with empty includes list."""
    mock_plan = Mock()
    mock_plan.audit_log = []
    mock_plan.project_dir = tmp_path

    includes_dir = tmp_path / "includes"

    resource_stager.copy_included_files(mock_plan, includes_dir, [])

    mock_copy2.assert_not_called()


@patch('pychub.package.lifecycle.plan.resource_resolution.resource_stager.shutil.copy2')
def test_copy_included_files_single_file(mock_copy2, tmp_path):
    """Test copy_included_files with single file."""
    mock_plan = Mock()
    mock_plan.audit_log = []
    mock_plan.project_dir = tmp_path

    # Create source file
    src_file = tmp_path / "source.txt"
    src_file.write_text("content")

    includes_dir = tmp_path / "includes"

    include_spec = Mock(spec=IncludeSpec)
    include_spec.as_string.return_value = str(src_file)

    resource_stager.copy_included_files(mock_plan, includes_dir, [include_spec])

    assert mock_copy2.call_count == 1
    call_args = mock_copy2.call_args[0]
    assert call_args[0] == src_file
    assert call_args[1] == includes_dir / "source.txt"


@patch('pychub.package.lifecycle.plan.resource_resolution.resource_stager.shutil.copy2')
def test_copy_included_files_with_destination(mock_copy2, tmp_path):
    """Test copy_included_files with custom destination."""
    mock_plan = Mock()
    mock_plan.audit_log = []
    mock_plan.project_dir = tmp_path

    src_file = tmp_path / "source.txt"
    src_file.write_text("content")

    includes_dir = tmp_path / "includes"

    include_spec = Mock(spec=IncludeSpec)
    include_spec.as_string.return_value = f"{src_file}::custom/dest.txt"

    resource_stager.copy_included_files(mock_plan, includes_dir, [include_spec])

    assert mock_copy2.call_count == 1
    call_args = mock_copy2.call_args[0]
    assert call_args[0] == src_file
    assert call_args[1] == includes_dir / "custom" / "dest.txt"


@patch('pychub.package.lifecycle.plan.resource_resolution.resource_stager.shutil.copy2')
def test_copy_included_files_multiple_files(mock_copy2, tmp_path):
    """Test copy_included_files with multiple files."""
    mock_plan = Mock()
    mock_plan.audit_log = []
    mock_plan.project_dir = tmp_path

    src1 = tmp_path / "file1.txt"
    src1.write_text("content1")
    src2 = tmp_path / "file2.txt"
    src2.write_text("content2")

    includes_dir = tmp_path / "includes"

    spec1 = Mock(spec=IncludeSpec)
    spec1.as_string.return_value = str(src1)
    spec2 = Mock(spec=IncludeSpec)
    spec2.as_string.return_value = str(src2)

    resource_stager.copy_included_files(mock_plan, includes_dir, [spec1, spec2])

    assert mock_copy2.call_count == 2


@patch('pychub.package.lifecycle.plan.resource_resolution.resource_stager.shutil.copy2')
def test_copy_included_files_creates_subdirectories(mock_copy2, tmp_path):
    """Test copy_included_files creates nested destination directories."""
    mock_plan = Mock()
    mock_plan.audit_log = []
    mock_plan.project_dir = tmp_path

    src_file = tmp_path / "source.txt"
    src_file.write_text("content")

    includes_dir = tmp_path / "includes"

    include_spec = Mock(spec=IncludeSpec)
    include_spec.as_string.return_value = f"{src_file}::deep/nested/path/dest.txt"

    resource_stager.copy_included_files(mock_plan, includes_dir, [include_spec])

    # Verify the nested directory was created
    expected_dest = includes_dir / "deep" / "nested" / "path" / "dest.txt"
    assert expected_dest.parent.exists()


def test_copy_included_files_missing_source_raises_error(tmp_path):
    """Test copy_included_files raises FileNotFoundError for missing source."""
    mock_plan = Mock()
    mock_plan.audit_log = []
    mock_plan.project_dir = tmp_path

    includes_dir = tmp_path / "includes"

    include_spec = Mock(spec=IncludeSpec)
    include_spec.as_string.return_value = str(tmp_path / "nonexistent.txt")

    with pytest.raises(FileNotFoundError) as exc_info:
        resource_stager.copy_included_files(mock_plan, includes_dir, [include_spec])

    assert "Included file not found" in str(exc_info.value)


@patch('pychub.package.lifecycle.plan.resource_resolution.resource_stager.shutil.copy2')
def test_copy_included_files_relative_path(mock_copy2, tmp_path):
    """Test copy_included_files with relative path."""
    mock_plan = Mock()
    mock_plan.audit_log = []
    mock_plan.project_dir = tmp_path

    src_file = tmp_path / "source.txt"
    src_file.write_text("content")

    includes_dir = tmp_path / "includes"

    include_spec = Mock(spec=IncludeSpec)
    include_spec.as_string.return_value = "source.txt"

    resource_stager.copy_included_files(mock_plan, includes_dir, [include_spec])

    assert mock_copy2.call_count == 1


# Tests for copy_install_scripts()

@patch('pychub.package.lifecycle.plan.resource_resolution.resource_stager.shutil.copy2')
def test_copy_install_scripts_empty_list(mock_copy2, tmp_path):
    """Test copy_install_scripts with empty script list."""
    scripts_dir = tmp_path / "scripts"

    resource_stager.copy_install_scripts(scripts_dir, [], "pre")

    mock_copy2.assert_not_called()


@patch('pychub.package.lifecycle.plan.resource_resolution.resource_stager.shutil.copy2')
def test_copy_install_scripts_single_script(mock_copy2, tmp_path):
    """Test copy_install_scripts with single script."""
    scripts_dir = tmp_path / "scripts"

    src_script = tmp_path / "script.sh"
    src_script.write_text("#!/bin/bash\necho hello")

    resource_stager.copy_install_scripts(scripts_dir, [str(src_script)], "pre")

    assert mock_copy2.call_count == 1
    call_args = mock_copy2.call_args[0]
    assert call_args[0] == src_script
    # The destination name includes the full sanitized path for traceability
    dest_path = call_args[1]
    assert dest_path.parent == scripts_dir / "pre"
    assert dest_path.name.startswith("00_")
    assert dest_path.name.endswith("_script.sh")


@patch('pychub.package.lifecycle.plan.resource_resolution.resource_stager.shutil.copy2')
def test_copy_install_scripts_multiple_scripts(mock_copy2, tmp_path):
    """Test copy_install_scripts with multiple scripts."""
    scripts_dir = tmp_path / "scripts"

    script1 = tmp_path / "first.sh"
    script1.write_text("#!/bin/bash\necho 1")
    script2 = tmp_path / "second.sh"
    script2.write_text("#!/bin/bash\necho 2")

    resource_stager.copy_install_scripts(scripts_dir, [str(script1), str(script2)], "post")

    assert mock_copy2.call_count == 2


@patch('pychub.package.lifecycle.plan.resource_resolution.resource_stager.shutil.copy2')
def test_copy_install_scripts_creates_target_directory(mock_copy2, tmp_path):
    """Test copy_install_scripts creates target directory."""
    scripts_dir = tmp_path / "scripts"

    src_script = tmp_path / "script.sh"
    src_script.write_text("#!/bin/bash")

    resource_stager.copy_install_scripts(scripts_dir, [str(src_script)], "pre")

    target_dir = scripts_dir / "pre"
    assert target_dir.exists()
    assert target_dir.is_dir()


def test_copy_install_scripts_missing_script_raises_error(tmp_path):
    """Test copy_install_scripts raises FileNotFoundError for missing script."""
    scripts_dir = tmp_path / "scripts"

    with pytest.raises(FileNotFoundError) as exc_info:
        resource_stager.copy_install_scripts(scripts_dir, [str(tmp_path / "missing.sh")], "pre")

    assert "pre-install script not found" in str(exc_info.value)


@patch('pychub.package.lifecycle.plan.resource_resolution.resource_stager.shutil.copy2')
def test_copy_install_scripts_preserves_order(mock_copy2, tmp_path):
    """Test copy_install_scripts preserves script order with prefixes."""
    scripts_dir = tmp_path / "scripts"

    scripts = []
    for i in range(3):
        script = tmp_path / f"script{i}.sh"
        script.write_text(f"echo {i}")
        scripts.append(str(script))

    resource_stager.copy_install_scripts(scripts_dir, scripts, "pre")

    assert mock_copy2.call_count == 3
    # Check that prefixes are in order
    calls = mock_copy2.call_args_list
    assert "00_" in str(calls[0][0][1])
    assert "01_" in str(calls[1][0][1])
    assert "02_" in str(calls[2][0][1])


# Tests for copy_post_install_scripts()

@patch('pychub.package.lifecycle.plan.resource_resolution.resource_stager.copy_install_scripts')
def test_copy_post_install_scripts_delegates(mock_copy_install, tmp_path):
    """Test copy_post_install_scripts delegates to copy_install_scripts."""
    mock_plan = Mock()
    mock_plan.audit_log = []

    scripts_dir = tmp_path / "scripts"
    script_paths = ["script1.sh", "script2.sh"]

    resource_stager.copy_post_install_scripts(mock_plan, scripts_dir, script_paths)

    mock_copy_install.assert_called_once_with(scripts_dir, script_paths, "post")


@patch('pychub.package.lifecycle.plan.resource_resolution.resource_stager.copy_install_scripts')
def test_copy_post_install_scripts_empty_list(mock_copy_install, tmp_path):
    """Test copy_post_install_scripts with empty list."""
    mock_plan = Mock()
    mock_plan.audit_log = []

    scripts_dir = tmp_path / "scripts"

    resource_stager.copy_post_install_scripts(mock_plan, scripts_dir, [])

    mock_copy_install.assert_called_once_with(scripts_dir, [], "post")


# Tests for copy_pre_install_scripts()

@patch('pychub.package.lifecycle.plan.resource_resolution.resource_stager.copy_install_scripts')
def test_copy_pre_install_scripts_delegates(mock_copy_install, tmp_path):
    """Test copy_pre_install_scripts delegates to copy_install_scripts."""
    mock_plan = Mock()
    mock_plan.audit_log = []

    scripts_dir = tmp_path / "scripts"
    script_paths = ["script1.sh", "script2.sh"]

    resource_stager.copy_pre_install_scripts(mock_plan, scripts_dir, script_paths)

    mock_copy_install.assert_called_once_with(scripts_dir, script_paths, "pre")


@patch('pychub.package.lifecycle.plan.resource_resolution.resource_stager.copy_install_scripts')
def test_copy_pre_install_scripts_empty_list(mock_copy_install, tmp_path):
    """Test copy_pre_install_scripts with empty list."""
    mock_plan = Mock()
    mock_plan.audit_log = []

    scripts_dir = tmp_path / "scripts"

    resource_stager.copy_pre_install_scripts(mock_plan, scripts_dir, [])

    mock_copy_install.assert_called_once_with(scripts_dir, [], "pre")


# Integration-style tests (testing functions together within the module)

@patch('pychub.package.lifecycle.plan.resource_resolution.resource_stager.shutil.copy2')
def test_prefixed_script_names_integration_with_copy_install_scripts(mock_copy2, tmp_path):
    """Test that prefixed_script_names output works correctly with copy_install_scripts."""
    scripts_dir = tmp_path / "scripts"

    # Create actual scripts
    script1 = tmp_path / "setup.sh"
    script1.write_text("#!/bin/bash\nsetup")
    script2 = tmp_path / "configure.sh"
    script2.write_text("#!/bin/bash\nconfigure")

    script_paths = [str(script1), str(script2)]

    resource_stager.copy_install_scripts(scripts_dir, script_paths, "pre")

    # Verify prefixed names are used
    assert mock_copy2.call_count == 2
    calls = mock_copy2.call_args_list

    # Both scripts should be in the correct directory
    assert calls[0][0][1].parent == scripts_dir / "pre"
    assert calls[1][0][1].parent == scripts_dir / "pre"

    # First script should have 00_ prefix and end with setup.sh
    assert calls[0][0][1].name.startswith("00_")
    assert calls[0][0][1].name.endswith("_setup.sh")

    # Second script should have 01_ prefix and end with configure.sh
    assert calls[1][0][1].name.startswith("01_")
    assert calls[1][0][1].name.endswith("_configure.sh")


def test_sanitize_integration_with_prefixed_script_names():
    """Test that _sanitize is correctly used within prefixed_script_names."""
    # Paths with special characters that need sanitization
    paths = ["path/to/script!.sh", "another@script.sh"]

    result = resource_stager.prefixed_script_names(paths)

    # Verify sanitization happened
    assert "path_to_script_.sh" in result[0][1]
    assert "another_script.sh" in result[1][1]


@patch('pychub.package.lifecycle.plan.resource_resolution.resource_stager.shutil.copy2')
def test_absolutize_paths_integration_with_copy_included_files(mock_copy2, tmp_path):
    """Test that absolutize_paths works correctly within copy_included_files."""
    mock_plan = Mock()
    mock_plan.audit_log = []
    mock_plan.project_dir = tmp_path

    # Create a relative path file
    src_file = tmp_path / "relative.txt"
    src_file.write_text("content")

    includes_dir = tmp_path / "includes"

    include_spec = Mock(spec=IncludeSpec)
    include_spec.as_string.return_value = "relative.txt"

    resource_stager.copy_included_files(mock_plan, includes_dir, [include_spec])

    # Should successfully resolve and copy
    assert mock_copy2.call_count == 1