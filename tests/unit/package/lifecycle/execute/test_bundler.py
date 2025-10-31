"""Unit tests for pychub.package.lifecycle.execute.bundler module."""
from __future__ import annotations

import zipfile
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from pychub.package.lifecycle.execute.bundler import (
    write_chubconfig_file,
    create_chub_build_dir,
    validate_files_exist,
    validate_chub_structure,
    prepare_build_dirs,
    copy_runtime_files,
    copy_included_files,
    copy_install_scripts,
    create_chub_archive,
    bundle_chub,
)


# ============================================================================
# Tests for write_chubconfig_file
# ============================================================================


def test_write_chubconfig_file_basic(tmp_path, mock_buildplan, mock_chubproject_factory):
    """Test write_chubconfig_file creates .chubconfig with correct content."""
    chub_build_dir = tmp_path / "build"
    chub_build_dir.mkdir()

    project = mock_chubproject_factory(
        name="test-pkg",
        version="1.0.0",
        entrypoint="test:main",
        includes=["config.yaml"],
        scripts={"pre": [("/src/setup.sh", "setup.sh")], "post": [("/src/cleanup.sh", "cleanup.sh")]},
        metadata={"author": "Test Author"}
    )
    mock_buildplan.project = project

    with patch("pychub.package.lifecycle.execute.bundler.ChubConfig") as mock_chubconfig_class:
        mock_chubconfig = MagicMock()
        mock_chubconfig_class.from_mapping.return_value = mock_chubconfig
        mock_chubconfig.to_yaml.return_value = "yaml_content"

        write_chubconfig_file(
            mock_buildplan,
            "test-pkg",
            "1.0.0",
            ["pkg1==1.0.0", "pkg2==2.0.0"],
            ["platform1", "platform2"],
            chub_build_dir
        )

        # Verify ChubConfig.from_mapping called with correct args
        mock_chubconfig_class.from_mapping.assert_called_once()
        call_args = mock_chubconfig_class.from_mapping.call_args[0][0]
        assert call_args["name"] == "test-pkg"
        assert call_args["version"] == "1.0.0"
        assert call_args["entrypoint"] == "test:main"
        assert call_args["includes"] == ["config.yaml"]
        assert call_args["scripts"]["pre"] == ["setup.sh"]
        assert call_args["scripts"]["post"] == ["cleanup.sh"]
        assert call_args["pinned_wheels"] == ["pkg1==1.0.0", "pkg2==2.0.0"]
        assert call_args["compatibility"]["targets"] == ["platform1", "platform2"]
        assert call_args["metadata"] == {"author": "Test Author"}

        # Verify validate called
        mock_chubconfig.validate.assert_called_once()

        # Verify file written
        chubconfig_file = chub_build_dir / ".chubconfig"
        assert chubconfig_file.exists()
        assert chubconfig_file.read_text() == "yaml_content"


def test_write_chubconfig_file_empty_scripts(tmp_path, mock_buildplan, mock_chubproject_factory):
    """Test write_chubconfig_file with empty scripts."""
    chub_build_dir = tmp_path / "build"
    chub_build_dir.mkdir()

    project = mock_chubproject_factory(
        name="test-pkg",
        version="1.0.0",
        scripts={"pre": [], "post": []}
    )
    mock_buildplan.project = project

    with patch("pychub.package.lifecycle.execute.bundler.ChubConfig") as mock_chubconfig_class:
        mock_chubconfig = MagicMock()
        mock_chubconfig_class.from_mapping.return_value = mock_chubconfig
        mock_chubconfig.to_yaml.return_value = "yaml_content"

        write_chubconfig_file(
            mock_buildplan,
            "test-pkg",
            "1.0.0",
            [],
            [],
            chub_build_dir
        )

        call_args = mock_chubconfig_class.from_mapping.call_args[0][0]
        assert call_args["scripts"]["pre"] == []
        assert call_args["scripts"]["post"] == []


# ============================================================================
# Tests for create_chub_build_dir
# ============================================================================


def test_create_chub_build_dir_basic(tmp_path):
    """Test create_chub_build_dir creates directory structure."""
    wheel_path = tmp_path / "test-1.0.0-py3-none-any.whl"
    wheel_path.touch()

    with patch("pychub.package.lifecycle.execute.bundler.CHUB_BUILD_DIR_STRUCTURE", [".chub", ".chub/libs", ".chub/scripts"]):
        with patch("pychub.package.lifecycle.execute.bundler.CHUB_BUILD_DIR", ".chub"):
            with patch("pychub.package.lifecycle.execute.bundler.CHUBCONFIG_FILENAME", ".chubconfig"):
                result = create_chub_build_dir(wheel_path)

    assert result == tmp_path / ".chub"
    assert (tmp_path / ".chub").exists()
    assert (tmp_path / ".chub" / "libs").exists()
    assert (tmp_path / ".chub" / "scripts").exists()
    assert (tmp_path / ".chub" / ".chubconfig").exists()


def test_create_chub_build_dir_with_custom_chub_path(tmp_path):
    """Test create_chub_build_dir with a custom chub output path."""
    wheel_path = tmp_path / "wheels" / "test-1.0.0-py3-none-any.whl"
    wheel_path.parent.mkdir()
    wheel_path.touch()

    chub_path = tmp_path / "output" / "test.chub"
    chub_path.parent.mkdir()

    with patch("pychub.package.lifecycle.execute.bundler.CHUB_BUILD_DIR_STRUCTURE", [".chub"]):
        with patch("pychub.package.lifecycle.execute.bundler.CHUB_BUILD_DIR", ".chub"):
            with patch("pychub.package.lifecycle.execute.bundler.CHUBCONFIG_FILENAME", ".chubconfig"):
                result = create_chub_build_dir(wheel_path, chub_path)

    # Should create in the parent of chub_path (output dir), not wheel dir
    assert result == tmp_path / "output" / ".chub"
    assert (tmp_path / "output" / ".chub").exists()


def test_create_chub_build_dir_not_a_wheel(tmp_path):
    """Test create_chub_build_dir raises an error for a non-wheel file."""
    not_wheel = tmp_path / "test.tar.gz"
    not_wheel.touch()

    with pytest.raises(ValueError, match="Not a wheel"):
        create_chub_build_dir(not_wheel)


def test_create_chub_build_dir_idempotent(tmp_path):
    """Test create_chub_build_dir is idempotent (can be called multiple times)."""
    wheel_path = tmp_path / "test-1.0.0-py3-none-any.whl"
    wheel_path.touch()

    with patch("pychub.package.lifecycle.execute.bundler.CHUB_BUILD_DIR_STRUCTURE", [".chub"]):
        with patch("pychub.package.lifecycle.execute.bundler.CHUB_BUILD_DIR", ".chub"):
            with patch("pychub.package.lifecycle.execute.bundler.CHUBCONFIG_FILENAME", ".chubconfig"):
                result1 = create_chub_build_dir(wheel_path)
                result2 = create_chub_build_dir(wheel_path)

    assert result1 == result2
    assert (tmp_path / ".chub").exists()


# ============================================================================
# Tests for validate_files_exist
# ============================================================================


def test_validate_files_exist_all_valid(tmp_path):
    """Test validate_files_exist with all valid files."""
    file1 = tmp_path / "file1.txt"
    file2 = tmp_path / "file2.yaml"
    file1.touch()
    file2.touch()

    # Should not raise
    validate_files_exist([str(file1), str(file2)], "Test")


def test_validate_files_exist_with_aliases(tmp_path):
    """Test validate_files_exist with aliased files (file::alias syntax)."""
    file1 = tmp_path / "file1.txt"
    file1.touch()

    # Should not raise - validates a source file before the double colon '::'
    validate_files_exist([f"{file1}::alias.txt"], "Test")


def test_validate_files_exist_missing_file(tmp_path):
    """Test validate_files_exist raises an error for a missing file."""
    file1 = tmp_path / "file1.txt"
    file1.touch()
    file2 = tmp_path / "missing.txt"

    with pytest.raises(FileNotFoundError, match="Test file not found: .*missing.txt"):
        validate_files_exist([str(file1), str(file2)], "Test")


def test_validate_files_exist_empty_list():
    """Test validate_files_exist with an empty list."""
    # Should not raise
    validate_files_exist([], "Test")


def test_validate_files_exist_directory_instead_of_file(tmp_path):
    """Test validate_files_exist raises an error when given a directory."""
    dir_path = tmp_path / "somedir"
    dir_path.mkdir()

    with pytest.raises(FileNotFoundError, match="Test file not found"):
        validate_files_exist([str(dir_path)], "Test")


def test_validate_files_exist_expands_user_path(tmp_path, monkeypatch):
    """Test validate_files_exist expands ~ in paths."""
    home_dir = tmp_path / "home"
    home_dir.mkdir()
    test_file = home_dir / "test.txt"
    test_file.touch()

    monkeypatch.setenv("HOME", str(home_dir))

    # Mock expanduser to return our test path
    original_expanduser = Path.expanduser

    def mock_expanduser(self):
        if str(self).startswith("~/"):
            return Path(str(self).replace("~", str(home_dir)))
        return original_expanduser(self)

    monkeypatch.setattr(Path, "expanduser", mock_expanduser)

    # Should not raise
    validate_files_exist(["~/test.txt"], "Test")


# ============================================================================
# Tests for validate_chub_structure
# ============================================================================


def test_validate_chub_structure_valid(tmp_path):
    """Test validate_chub_structure with valid structure."""
    chub_build_dir = tmp_path / "build"
    chub_build_dir.mkdir()
    (chub_build_dir / ".chubconfig").touch()
    (chub_build_dir / "libs").mkdir()
    (chub_build_dir / "scripts").mkdir()

    file1 = tmp_path / "script.sh"
    file2 = tmp_path / "include.yaml"
    file1.touch()
    file2.touch()

    # Should not raise
    validate_chub_structure(
        chub_build_dir,
        [str(file1)],
        [str(file1)],
        [str(file2)]
    )


def test_validate_chub_structure_missing_chubconfig(tmp_path):
    """Test validate_chub_structure raises error when .chubconfig missing."""
    chub_build_dir = tmp_path / "build"
    chub_build_dir.mkdir()

    with pytest.raises(FileNotFoundError, match="Missing .chubconfig"):
        validate_chub_structure(chub_build_dir, [], [], [])


def test_validate_chub_structure_libs_not_empty(tmp_path):
    """Test validate_chub_structure raises error when libs dir has files."""
    chub_build_dir = tmp_path / "build"
    chub_build_dir.mkdir()
    (chub_build_dir / ".chubconfig").touch()
    libs_dir = chub_build_dir / "libs"
    libs_dir.mkdir()
    (libs_dir / "some.whl").touch()

    with pytest.raises(FileExistsError, match="libs/ .* is not empty"):
        validate_chub_structure(chub_build_dir, [], [], [])


def test_validate_chub_structure_scripts_not_empty(tmp_path):
    """Test validate_chub_structure raises error when scripts dir has files."""
    chub_build_dir = tmp_path / "build"
    chub_build_dir.mkdir()
    (chub_build_dir / ".chubconfig").touch()
    (chub_build_dir / "libs").mkdir()
    scripts_dir = chub_build_dir / "scripts"
    scripts_dir.mkdir()
    (scripts_dir / "setup.sh").touch()

    with pytest.raises(FileExistsError, match="scripts/ .* is not empty"):
        validate_chub_structure(chub_build_dir, [], [], [])


def test_validate_chub_structure_missing_include_file(tmp_path):
    """Test validate_chub_structure raises error for missing include file."""
    chub_build_dir = tmp_path / "build"
    chub_build_dir.mkdir()
    (chub_build_dir / ".chubconfig").touch()
    (chub_build_dir / "libs").mkdir()
    (chub_build_dir / "scripts").mkdir()

    with pytest.raises(FileNotFoundError, match="Include file not found"):
        validate_chub_structure(chub_build_dir, [], [], ["missing.yaml"])


def test_validate_chub_structure_missing_post_install_script(tmp_path):
    """Test validate_chub_structure raises error for missing post-install script."""
    chub_build_dir = tmp_path / "build"
    chub_build_dir.mkdir()
    (chub_build_dir / ".chubconfig").touch()
    (chub_build_dir / "libs").mkdir()
    (chub_build_dir / "scripts").mkdir()

    with pytest.raises(FileNotFoundError, match="post-install file not found"):
        validate_chub_structure(chub_build_dir, ["missing.sh"], [], [])


def test_validate_chub_structure_missing_pre_install_script(tmp_path):
    """Test validate_chub_structure raises error for missing pre-install script."""
    chub_build_dir = tmp_path / "build"
    chub_build_dir.mkdir()
    (chub_build_dir / ".chubconfig").touch()
    (chub_build_dir / "libs").mkdir()
    (chub_build_dir / "scripts").mkdir()

    with pytest.raises(FileNotFoundError, match="pre-install file not found"):
        validate_chub_structure(chub_build_dir, [], ["missing.sh"], [])


# ============================================================================
# Tests for prepare_build_dirs
# ============================================================================


def test_prepare_build_dirs_basic(tmp_path):
    """Test prepare_build_dirs creates all necessary directories."""
    wheel_path = tmp_path / "test-1.0.0-py3-none-any.whl"
    wheel_path.touch()

    with patch("pychub.package.lifecycle.execute.bundler.create_chub_build_dir") as mock_create:
        mock_create.return_value = tmp_path / ".chub"
        with patch("pychub.package.lifecycle.execute.bundler.CHUB_LIBS_DIR", "libs"):
            chub_build_dir, wheel_libs_dir, path_cache_dir = prepare_build_dirs(wheel_path, None)

    mock_create.assert_called_once_with(wheel_path, None)
    assert chub_build_dir == tmp_path / ".chub"
    assert wheel_libs_dir == tmp_path / ".chub" / "libs"
    assert path_cache_dir == tmp_path / ".chub" / ".wheel_cache"


def test_prepare_build_dirs_with_chub_path(tmp_path):
    """Test prepare_build_dirs with a custom chub output path."""
    wheel_path = tmp_path / "test-1.0.0-py3-none-any.whl"
    wheel_path.touch()
    chub_path = tmp_path / "output.chub"

    with patch("pychub.package.lifecycle.execute.bundler.create_chub_build_dir") as mock_create:
        mock_create.return_value = tmp_path / ".chub"
        with patch("pychub.package.lifecycle.execute.bundler.CHUB_LIBS_DIR", "libs"):
            chub_build_dir, wheel_libs_dir, path_cache_dir = prepare_build_dirs(wheel_path, chub_path)

    mock_create.assert_called_once_with(wheel_path, chub_path)


def test_prepare_build_dirs_creates_subdirs(tmp_path):
    """Test prepare_build_dirs actually creates the subdirectories."""
    wheel_path = tmp_path / "test-1.0.0-py3-none-any.whl"
    wheel_path.touch()

    build_dir = tmp_path / ".chub"
    build_dir.mkdir()

    with patch("pychub.package.lifecycle.execute.bundler.create_chub_build_dir") as mock_create:
        mock_create.return_value = build_dir
        with patch("pychub.package.lifecycle.execute.bundler.CHUB_LIBS_DIR", "libs"):
            chub_build_dir, wheel_libs_dir, path_cache_dir = prepare_build_dirs(wheel_path, None)

    assert (build_dir / "libs").exists()
    assert (build_dir / ".wheel_cache").exists()


# ============================================================================
# Tests for copy_runtime_files
# ============================================================================


def test_copy_runtime_files(tmp_path, mock_buildplan):
    """Test copy_runtime_files copies runtime directory."""
    staging_dir = tmp_path / "staging"
    staging_dir.mkdir()
    runtime_src = staging_dir / "runtime"
    runtime_src.mkdir()
    (runtime_src / "main.py").write_text("main content")
    (runtime_src / "__main__.py").write_text("main content")

    mock_buildplan.staging_dir = staging_dir

    dest_dir = tmp_path / "dest" / "runtime"

    with patch("pychub.package.lifecycle.execute.bundler.RUNTIME_DIR", "runtime"):
        with patch("pychub.package.lifecycle.execute.bundler.shutil.copytree") as mock_copytree:
            copy_runtime_files(mock_buildplan, dest_dir)

            mock_copytree.assert_called_once_with(runtime_src, dest_dir, dirs_exist_ok=True)


def test_copy_runtime_files_dirs_exist_ok(tmp_path, mock_buildplan):
    """Test copy_runtime_files allows existing directories."""
    staging_dir = tmp_path / "staging"
    staging_dir.mkdir()
    runtime_src = staging_dir / "runtime"
    runtime_src.mkdir()

    mock_buildplan.staging_dir = staging_dir
    dest_dir = tmp_path / "dest" / "runtime"

    with patch("pychub.package.lifecycle.execute.bundler.RUNTIME_DIR", "runtime"):
        with patch("pychub.package.lifecycle.execute.bundler.shutil.copytree") as mock_copytree:
            copy_runtime_files(mock_buildplan, dest_dir)

            # Verify dirs_exist_ok=True passed
            assert mock_copytree.call_args[1]["dirs_exist_ok"] is True


# ============================================================================
# Tests for copy_included_files
# ============================================================================


def test_copy_included_files(tmp_path, mock_buildplan):
    """Test copy_included_files copies the includes directory."""
    staging_dir = tmp_path / "staging"
    staging_dir.mkdir()
    includes_src = staging_dir / "includes"
    includes_src.mkdir()
    (includes_src / "config.yaml").write_text("config")

    mock_buildplan.staging_dir = staging_dir
    dest_dir = tmp_path / "dest" / "includes"

    with patch("pychub.package.lifecycle.execute.bundler.CHUB_INCLUDES_DIR", "includes"):
        with patch("pychub.package.lifecycle.execute.bundler.shutil.copytree") as mock_copytree:
            copy_included_files(mock_buildplan, dest_dir)

            mock_copytree.assert_called_once_with(includes_src, dest_dir, dirs_exist_ok=True)


# ============================================================================
# Tests for copy_install_scripts
# ============================================================================


def test_copy_install_scripts(tmp_path, mock_buildplan):
    """Test copy_install_scripts copies scripts directory."""
    staging_dir = tmp_path / "staging"
    staging_dir.mkdir()
    scripts_src = staging_dir / "scripts"
    scripts_src.mkdir()
    (scripts_src / "setup.sh").write_text("setup")

    mock_buildplan.staging_dir = staging_dir
    dest_dir = tmp_path / "dest" / "scripts"

    with patch("pychub.package.lifecycle.execute.bundler.CHUB_SCRIPTS_DIR", "scripts"):
        with patch("pychub.package.lifecycle.execute.bundler.shutil.copytree") as mock_copytree:
            copy_install_scripts(mock_buildplan, dest_dir)

            mock_copytree.assert_called_once_with(scripts_src, dest_dir, dirs_exist_ok=True)


# ============================================================================
# Tests for create_chub_archive
# ============================================================================


def test_create_chub_archive_basic(tmp_path, mock_buildplan):
    """Test create_chub_archive creates a valid ZIP archive."""
    build_dir = tmp_path / "build"
    build_dir.mkdir()
    (build_dir / ".chubconfig").write_text("config")
    libs_dir = build_dir / "libs"
    libs_dir.mkdir()
    (libs_dir / "test.whl").write_text("wheel")

    archive_path = tmp_path / "output.chub"
    mock_buildplan.staging_dir = tmp_path

    result = create_chub_archive(mock_buildplan, build_dir, archive_path)

    assert result == archive_path
    assert archive_path.exists()

    # Verify archive contents
    with zipfile.ZipFile(archive_path, "r") as zf:
        names = zf.namelist()
        assert ".chubconfig" in names
        assert "libs/test.whl" in names or "libs\\test.whl" in names


def test_create_chub_archive_excludes_self(tmp_path, mock_buildplan):
    """Test create_chub_archive doesn't include the archive file itself."""
    build_dir = tmp_path / "build"
    build_dir.mkdir()
    (build_dir / ".chubconfig").write_text("config")

    # Archive path inside the build dir
    archive_path = build_dir / "output.chub"
    mock_buildplan.staging_dir = tmp_path

    result = create_chub_archive(mock_buildplan, build_dir, archive_path)

    with zipfile.ZipFile(archive_path, "r") as zf:
        names = zf.namelist()
        assert "output.chub" not in names


def test_create_chub_archive_compression(tmp_path, mock_buildplan):
    """Test create_chub_archive uses ZIP_DEFLATED compression."""
    build_dir = tmp_path / "build"
    build_dir.mkdir()
    (build_dir / "test.txt").write_text("x" * 1000)

    archive_path = tmp_path / "output.chub"
    mock_buildplan.staging_dir = tmp_path

    create_chub_archive(mock_buildplan, build_dir, archive_path)

    with zipfile.ZipFile(archive_path, "r") as zf:
        for info in zf.infolist():
            # Verify compression type
            assert info.compress_type == zipfile.ZIP_DEFLATED


def test_create_chub_archive_nested_directories(tmp_path, mock_buildplan):
    """Test create_chub_archive handles nested directory structures."""
    build_dir = tmp_path / "build"
    build_dir.mkdir()
    nested = build_dir / "level1" / "level2"
    nested.mkdir(parents=True)
    (nested / "file.txt").write_text("nested")

    archive_path = tmp_path / "output.chub"
    mock_buildplan.staging_dir = tmp_path

    create_chub_archive(mock_buildplan, build_dir, archive_path)

    with zipfile.ZipFile(archive_path, "r") as zf:
        names = [n.replace("\\", "/") for n in zf.namelist()]
        assert "level1/level2/file.txt" in names


def test_create_chub_archive_preserves_relative_paths(tmp_path, mock_buildplan):
    """Test create_chub_archive uses relative paths in the archive."""
    build_dir = tmp_path / "build"
    build_dir.mkdir()
    (build_dir / "root_file.txt").write_text("root")
    subdir = build_dir / "subdir"
    subdir.mkdir()
    (subdir / "sub_file.txt").write_text("sub")

    archive_path = tmp_path / "output.chub"
    mock_buildplan.staging_dir = tmp_path

    create_chub_archive(mock_buildplan, build_dir, archive_path)

    with zipfile.ZipFile(archive_path, "r") as zf:
        names = zf.namelist()
        # Paths should be relative to build_dir
        assert any("root_file.txt" in n for n in names)
        assert any("subdir" in n and "sub_file.txt" in n for n in names)
        # Should NOT contain absolute paths
        assert not any(str(tmp_path) in n for n in names)


# ============================================================================
# Tests for bundle_chub
# ============================================================================


def test_bundle_chub_full_flow(tmp_path, mock_buildplan, mock_chubproject_factory):
    """Test bundle_chub complete bundling flow."""
    # Setup staging directory
    staging_dir = tmp_path / "staging"
    staging_dir.mkdir()

    wheels_dir = staging_dir / "wheels"
    wheels_dir.mkdir()
    platform_dir = wheels_dir / "linux_x86_64"
    platform_dir.mkdir()
    (platform_dir / "test-1.0.0-py3-none-any.whl").touch()

    runtime_dir = staging_dir / "runtime"
    runtime_dir.mkdir()
    (runtime_dir / "main.py").touch()

    includes_dir = staging_dir / "includes"
    includes_dir.mkdir()

    scripts_dir = staging_dir / "scripts"
    scripts_dir.mkdir()

    project = mock_chubproject_factory(
        name="test-pkg",
        version="1.0.0",
        wheels=["test-1.0.0-py3-none-any.whl"],
        entrypoint="test:main"
    )
    mock_buildplan.project = project
    mock_buildplan.staging_dir = staging_dir
    mock_buildplan.wheels_dir = Path("wheels")

    with patch("pychub.package.lifecycle.execute.bundler.shutil.copy2"):
        with patch("pychub.package.lifecycle.execute.bundler.write_chubconfig_file"):
            with patch("pychub.package.lifecycle.execute.bundler.shutil.copytree"):
                with patch("pychub.package.lifecycle.execute.bundler.create_chub_archive") as mock_archive:
                    expected_path = staging_dir / ".chub" / "test-pkg-1.0.0.chub"
                    mock_archive.return_value = expected_path

                    result = bundle_chub(mock_buildplan)

                    assert result == expected_path


def test_bundle_chub_uses_project_name_version(tmp_path, mock_buildplan, mock_chubproject_factory):
    """Test bundle_chub uses project name and version when available."""
    staging_dir = tmp_path / "staging"
    staging_dir.mkdir()

    wheels_dir = staging_dir / "wheels"
    wheels_dir.mkdir()
    platform_dir = wheels_dir / "linux"
    platform_dir.mkdir()

    runtime_dir = staging_dir / "runtime"
    runtime_dir.mkdir()
    includes_dir = staging_dir / "includes"
    includes_dir.mkdir()
    scripts_dir = staging_dir / "scripts"
    scripts_dir.mkdir()

    project = mock_chubproject_factory(
        name="my-project",
        version="2.5.0",
        wheels=["other-1.0.0-py3-none-any.whl"]
    )
    mock_buildplan.project = project
    mock_buildplan.staging_dir = staging_dir
    mock_buildplan.wheels_dir = Path("wheels")

    with patch("pychub.package.lifecycle.execute.bundler.shutil.copy2"):
        with patch("pychub.package.lifecycle.execute.bundler.write_chubconfig_file") as mock_write:
            with patch("pychub.package.lifecycle.execute.bundler.shutil.copytree"):
                with patch("pychub.package.lifecycle.execute.bundler.create_chub_archive") as mock_archive:
                    expected_path = staging_dir / ".chub" / "my-project-2.5.0.chub"
                    mock_archive.return_value = expected_path

                    bundle_chub(mock_buildplan)

                    # Verify write_chubconfig_file called with project name/version
                    call_args = mock_write.call_args[0]
                    assert call_args[1] == "my-project"
                    assert call_args[2] == "2.5.0"


def test_bundle_chub_falls_back_to_wheel_name(tmp_path, mock_buildplan, mock_chubproject_factory):
    """Test bundle_chub falls back to the wheel filename for name/version."""
    staging_dir = tmp_path / "staging"
    staging_dir.mkdir()

    wheels_dir = staging_dir / "wheels"
    wheels_dir.mkdir()
    platform_dir = wheels_dir / "linux"
    platform_dir.mkdir()

    runtime_dir = staging_dir / "runtime"
    runtime_dir.mkdir()
    includes_dir = staging_dir / "includes"
    includes_dir.mkdir()
    scripts_dir = staging_dir / "scripts"
    scripts_dir.mkdir()

    project = mock_chubproject_factory(
        name=None,
        version=None,
        wheels=["extracted-3.0.0-py3-none-any.whl"]
    )
    mock_buildplan.project = project
    mock_buildplan.staging_dir = staging_dir
    mock_buildplan.wheels_dir = Path("wheels")

    with patch("pychub.package.lifecycle.execute.bundler.shutil.copy2"):
        with patch("pychub.package.lifecycle.execute.bundler.parse_wheel_filename") as mock_parse:
            mock_parse.return_value = ("extracted", "3.0.0", None, None)
            with patch("pychub.package.lifecycle.execute.bundler.write_chubconfig_file") as mock_write:
                with patch("pychub.package.lifecycle.execute.bundler.shutil.copytree"):
                    with patch("pychub.package.lifecycle.execute.bundler.create_chub_archive") as mock_archive:
                        expected_path = staging_dir / ".chub" / "extracted-3.0.0.chub"
                        mock_archive.return_value = expected_path

                        bundle_chub(mock_buildplan)

                        call_args = mock_write.call_args[0]
                        assert call_args[1] == "extracted"
                        assert call_args[2] == "3.0.0"


def test_bundle_chub_raises_when_no_name_version(tmp_path, mock_buildplan, mock_chubproject_factory):
    """Test bundle_chub raises error when no name/version available."""
    staging_dir = tmp_path / "staging"
    staging_dir.mkdir()

    wheels_dir = staging_dir / "wheels"
    wheels_dir.mkdir()
    platform_dir = wheels_dir / "linux"
    platform_dir.mkdir()

    project = mock_chubproject_factory(
        name=None,
        version=None,
        wheels=[]
    )
    mock_buildplan.project = project
    mock_buildplan.staging_dir = staging_dir
    mock_buildplan.wheels_dir = Path("wheels")

    runtime_dir = staging_dir / "runtime"
    runtime_dir.mkdir()
    includes_dir = staging_dir / "includes"
    includes_dir.mkdir()
    scripts_dir = staging_dir / "scripts"
    scripts_dir.mkdir()

    with patch("pychub.package.lifecycle.execute.bundler.shutil.copytree"):
        with pytest.raises(ValueError, match="Missing distribution name and version"):
            bundle_chub(mock_buildplan)


def test_bundle_chub_missing_staged_wheels_dir(tmp_path, mock_buildplan, mock_chubproject_factory):
    """Test bundle_chub raises error when staged wheels directory is missing."""
    staging_dir = tmp_path / "staging"
    staging_dir.mkdir()

    project = mock_chubproject_factory(
        name="test",
        version="1.0.0"
    )
    mock_buildplan.project = project
    mock_buildplan.staging_dir = staging_dir
    mock_buildplan.wheels_dir = Path("wheels")

    with pytest.raises(FileNotFoundError, match="Missing staged wheels"):
        bundle_chub(mock_buildplan)


def test_bundle_chub_copies_all_wheels(tmp_path, mock_buildplan, mock_chubproject_factory):
    """Test bundle_chub copies all wheels from the staged directory."""
    staging_dir = tmp_path / "staging"
    staging_dir.mkdir()

    wheels_dir = staging_dir / "wheels"
    wheels_dir.mkdir()
    platform_dir = wheels_dir / "linux"
    platform_dir.mkdir()
    (platform_dir / "pkg1-1.0.0-py3-none-any.whl").touch()
    (platform_dir / "pkg2-2.0.0-py3-none-any.whl").touch()

    runtime_dir = staging_dir / "runtime"
    runtime_dir.mkdir()
    includes_dir = staging_dir / "includes"
    includes_dir.mkdir()
    scripts_dir = staging_dir / "scripts"
    scripts_dir.mkdir()

    project = mock_chubproject_factory(
        name="test",
        version="1.0.0",
        wheels=["pkg1-1.0.0-py3-none-any.whl", "pkg2-2.0.0-py3-none-any.whl"]
    )
    mock_buildplan.project = project
    mock_buildplan.staging_dir = staging_dir
    mock_buildplan.wheels_dir = Path("wheels")

    with patch("pychub.package.lifecycle.execute.bundler.shutil.copy2") as mock_copy:
        with patch("pychub.package.lifecycle.execute.bundler.write_chubconfig_file"):
            with patch("pychub.package.lifecycle.execute.bundler.shutil.copytree"):
                with patch("pychub.package.lifecycle.execute.bundler.create_chub_archive") as mock_archive:
                    expected_path = staging_dir / ".chub" / "test-1.0.0.chub"
                    mock_archive.return_value = expected_path

                    bundle_chub(mock_buildplan)

                    # Verify both wheels were copied
                    assert mock_copy.call_count == 2


def test_bundle_chub_detects_platform_targets(tmp_path, mock_buildplan, mock_chubproject_factory):
    """Test bundle_chub detects platform directories as targets."""
    staging_dir = tmp_path / "staging"
    staging_dir.mkdir()

    wheels_dir = staging_dir / "wheels"
    wheels_dir.mkdir()
    (wheels_dir / "linux_x86_64").mkdir()
    (wheels_dir / "win_amd64").mkdir()
    (wheels_dir / "macosx_arm64").mkdir()

    runtime_dir = staging_dir / "runtime"
    runtime_dir.mkdir()
    includes_dir = staging_dir / "includes"
    includes_dir.mkdir()
    scripts_dir = staging_dir / "scripts"
    scripts_dir.mkdir()

    project = mock_chubproject_factory(
        name="test",
        version="1.0.0",
        wheels=["test-1.0.0-py3-none-any.whl"]
    )
    mock_buildplan.project = project
    mock_buildplan.staging_dir = staging_dir
    mock_buildplan.wheels_dir = Path("wheels")

    with patch("pychub.package.lifecycle.execute.bundler.shutil.copy2"):
        with patch("pychub.package.lifecycle.execute.bundler.write_chubconfig_file") as mock_write:
            with patch("pychub.package.lifecycle.execute.bundler.shutil.copytree"):
                with patch("pychub.package.lifecycle.execute.bundler.create_chub_archive") as mock_archive:
                    expected_path = staging_dir / ".chub" / "test-1.0.0.chub"
                    mock_archive.return_value = expected_path

                    bundle_chub(mock_buildplan)

                    # Verify targets passed to write_chubconfig_file
                    call_args = mock_write.call_args[0]
                    targets = call_args[4]
                    assert set(targets) == {"linux_x86_64", "win_amd64", "macosx_arm64"}


def test_bundle_chub_calls_copy_functions(tmp_path, mock_buildplan, mock_chubproject_factory):
    """Test bundle_chub calls all copy functions for assets."""
    staging_dir = tmp_path / "staging"
    staging_dir.mkdir()

    wheels_dir = staging_dir / "wheels"
    wheels_dir.mkdir()
    platform_dir = wheels_dir / "linux"
    platform_dir.mkdir()

    runtime_dir = staging_dir / "runtime"
    runtime_dir.mkdir()
    includes_dir = staging_dir / "includes"
    includes_dir.mkdir()
    scripts_dir = staging_dir / "scripts"
    scripts_dir.mkdir()

    project = mock_chubproject_factory(
        name="test",
        version="1.0.0",
        wheels=["test-1.0.0-py3-none-any.whl"]
    )
    mock_buildplan.project = project
    mock_buildplan.staging_dir = staging_dir
    mock_buildplan.wheels_dir = Path("wheels")

    with patch("pychub.package.lifecycle.execute.bundler.shutil.copy2"):
        with patch("pychub.package.lifecycle.execute.bundler.copy_runtime_files") as mock_runtime:
            with patch("pychub.package.lifecycle.execute.bundler.copy_included_files") as mock_includes:
                with patch("pychub.package.lifecycle.execute.bundler.copy_install_scripts") as mock_scripts:
                    with patch("pychub.package.lifecycle.execute.bundler.write_chubconfig_file"):
                        with patch("pychub.package.lifecycle.execute.bundler.create_chub_archive") as mock_archive:
                            expected_path = staging_dir / ".chub" / "test-1.0.0.chub"
                            mock_archive.return_value = expected_path

                            bundle_chub(mock_buildplan)

                            mock_runtime.assert_called_once()
                            mock_includes.assert_called_once()
                            mock_scripts.assert_called_once()


def test_bundle_chub_uses_custom_chub_path(tmp_path, mock_buildplan, mock_chubproject_factory):
    """Test bundle_chub uses a custom chub output path when specified."""
    staging_dir = tmp_path / "staging"
    staging_dir.mkdir()

    wheels_dir = staging_dir / "wheels"
    wheels_dir.mkdir()
    platform_dir = wheels_dir / "linux"
    platform_dir.mkdir()

    runtime_dir = staging_dir / "runtime"
    runtime_dir.mkdir()
    includes_dir = staging_dir / "includes"
    includes_dir.mkdir()
    scripts_dir = staging_dir / "scripts"
    scripts_dir.mkdir()

    custom_path = tmp_path / "custom" / "output.chub"

    project = mock_chubproject_factory(
        name="test",
        version="1.0.0",
        wheels=["test-1.0.0-py3-none-any.whl"],
        chub=str(custom_path)
    )
    mock_buildplan.project = project
    mock_buildplan.staging_dir = staging_dir
    mock_buildplan.wheels_dir = Path("wheels")

    with patch("pychub.package.lifecycle.execute.bundler.shutil.copy2"):
        with patch("pychub.package.lifecycle.execute.bundler.write_chubconfig_file"):
            with patch("pychub.package.lifecycle.execute.bundler.shutil.copytree"):
                with patch("pychub.package.lifecycle.execute.bundler.create_chub_archive") as mock_archive:
                    mock_archive.return_value = custom_path

                    result = bundle_chub(mock_buildplan)

                    # Verify custom path used
                    call_args = mock_archive.call_args[0]
                    assert call_args[2] == Path(custom_path)
                    assert result == custom_path


def test_bundle_chub_prints_output_message(tmp_path, mock_buildplan, mock_chubproject_factory, capsys):
    """Test bundle_chub prints a success message with an output path."""
    staging_dir = tmp_path / "staging"
    staging_dir.mkdir()

    wheels_dir = staging_dir / "wheels"
    wheels_dir.mkdir()
    platform_dir = wheels_dir / "linux"
    platform_dir.mkdir()

    runtime_dir = staging_dir / "runtime"
    runtime_dir.mkdir()
    includes_dir = staging_dir / "includes"
    includes_dir.mkdir()
    scripts_dir = staging_dir / "scripts"
    scripts_dir.mkdir()

    project = mock_chubproject_factory(
        name="test",
        version="1.0.0",
        wheels=["test-1.0.0-py3-none-any.whl"]
    )
    mock_buildplan.project = project
    mock_buildplan.staging_dir = staging_dir
    mock_buildplan.wheels_dir = Path("wheels")

    with patch("pychub.package.lifecycle.execute.bundler.shutil.copy2"):
        with patch("pychub.package.lifecycle.execute.bundler.write_chubconfig_file"):
            with patch("pychub.package.lifecycle.execute.bundler.shutil.copytree"):
                with patch("pychub.package.lifecycle.execute.bundler.create_chub_archive") as mock_archive:
                    expected_path = staging_dir / ".chub" / "test-1.0.0.chub"
                    mock_archive.return_value = expected_path

                    bundle_chub(mock_buildplan)

                    captured = capsys.readouterr()
                    assert "Built" in captured.out
                    assert str(expected_path) in captured.out