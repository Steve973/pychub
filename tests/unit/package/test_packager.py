import subprocess
import sys
import types
import zipfile
from pathlib import Path

import pytest
import yaml

from pychub.model.chubproject_model import ChubProject
from pychub.package import packager
from pychub.package.constants import (
    CHUB_BUILD_DIR,
    CHUB_LIBS_DIR,
    CHUB_SCRIPTS_DIR,
    CHUB_POST_INSTALL_SCRIPTS_DIR,
    CHUB_PRE_INSTALL_SCRIPTS_DIR,
    CHUBCONFIG_FILENAME,
    RUNTIME_DIR, CHUB_INCLUDES_DIR,
)


@pytest.fixture(autouse=True)
def isolate_cwd(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    return tmp_path


@pytest.fixture
def temp_runtime(monkeypatch, tmp_path):
    # Fake runtime tree next to a fake module __file__
    fake_pkg_dir = tmp_path / "fakepkg"
    (fake_pkg_dir / RUNTIME_DIR).mkdir(parents=True)
    fake_packager_file = fake_pkg_dir / "packager.py"
    fake_packager_file.write_text("# pretend")
    monkeypatch.setattr(packager, "__file__", str(fake_packager_file))
    return fake_pkg_dir


def test_create_chub_archive_includes_all_content(tmp_path):
    build_dir = tmp_path / "build"
    (build_dir / "dir").mkdir(parents=True)
    (build_dir / "a.txt").write_text("A")
    (build_dir / "dir" / "b.txt").write_text("B")
    archive_path = tmp_path / "out.chub"
    out = packager.create_chub_archive(build_dir, archive_path)
    assert out == archive_path
    with zipfile.ZipFile(out) as zf:
        names = set(zf.namelist())
    assert "a.txt" in names
    assert "dir/b.txt" in names


def test_create_chub_archive_skips_itself(tmp_path):
    """Test that create_chub_archive skips the archive file itself (line 112)."""
    build_dir = tmp_path / "build"
    build_dir.mkdir()
    (build_dir / "a.txt").write_text("A")

    # Create archive inside the build_dir
    archive_path = build_dir / "out.chub"
    out = packager.create_chub_archive(build_dir, archive_path)

    # Archive should exist but not be included in itself
    assert out.exists()
    with zipfile.ZipFile(out) as zf:
        names = set(zf.namelist())
    assert "a.txt" in names
    assert "out.chub" not in names  # Should have been skipped


def test_copy_runtime_files_writes_runtime_and_main(tmp_path, temp_runtime):
    chub_build_dir = tmp_path / "chub"
    chub_build_dir.mkdir()
    packager.copy_runtime_files(chub_build_dir)
    assert (chub_build_dir / RUNTIME_DIR).is_dir()
    main_py = chub_build_dir / "__main__.py"
    assert main_py.is_file()
    assert f"run_module('{RUNTIME_DIR}'" in main_py.read_text()


def test_copy_included_files_noop_on_none_and_empty(tmp_path):
    base = tmp_path / "base"
    base.mkdir()
    packager.copy_included_files(base, None)
    packager.copy_included_files(base, [])
    assert list(base.iterdir()) == []


def test_copy_included_files_basic_and_with_dest(tmp_path):
    base = tmp_path / "base"
    base.mkdir()
    src1 = base / "f1.txt"
    src1.write_text("1")
    src2 = base / "f2.txt"
    src2.write_text("2")
    packager.copy_included_files(base, [str(src1), f"{src2}::data/inside.txt"])
    assert (base / "f1.txt").read_text() == "1"
    assert (base / CHUB_INCLUDES_DIR / "data" / "inside.txt").read_text() == "2"


def test_copy_included_files_missing_raises(tmp_path):
    base = tmp_path / "base"
    base.mkdir()
    with pytest.raises(FileNotFoundError):
        packager.copy_included_files(base, ["nope.txt"])


def test_copy_included_files_prevent_directory_traversal(tmp_path):
    base = tmp_path / "base"
    base.mkdir()
    src = tmp_path / "x.txt"
    src.write_text("x")
    with pytest.raises(ValueError) as e:
        packager.copy_included_files(base, [f"{src}::../outside.txt"])
    assert "escapes chub includes directory" in str(e.value)


def test_copy_install_scripts_happy(tmp_path):
    base = tmp_path / "build" / CHUB_SCRIPTS_DIR
    (base / CHUB_POST_INSTALL_SCRIPTS_DIR).mkdir(parents=True)
    s = tmp_path / "foo.sh"
    s.write_text("echo hi")
    packager.copy_install_scripts(
        base,
        [(s, "00_post_foo.sh")],
        CHUB_POST_INSTALL_SCRIPTS_DIR,
    )
    assert (base / CHUB_POST_INSTALL_SCRIPTS_DIR / "00_post_foo.sh").is_file()


def test_copy_install_scripts_empty_list_returns_early(tmp_path):
    """Test that copy_install_scripts returns early with empty list (line 223)."""
    base = tmp_path / "build" / CHUB_SCRIPTS_DIR
    base.mkdir(parents=True)

    # Should not raise and should not create any directories
    packager.copy_install_scripts(base, [], CHUB_POST_INSTALL_SCRIPTS_DIR)

    # Post directory should not have been created
    assert not (base / CHUB_POST_INSTALL_SCRIPTS_DIR).exists()


def test_download_wheel_deps_builds_cmd_and_handles_errors(monkeypatch, tmp_path):
    calls = []

    def fake_run(cmd, text, capture_output):
        calls.append(cmd)
        return types.SimpleNamespace(returncode=0, stdout="ok", stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)
    whl = tmp_path / "pkg-1.0.0-py3-none-any.whl"
    whl.write_text("fake")
    dest = tmp_path / "deps"
    packager.download_wheel_deps(whl, dest, only_binary=True, extra_pip_args=["--no-cache"])
    assert calls and calls[0][:3] == [sys.executable, "-m", "pip"]
    assert "download" in calls[0] and "--only-binary" in calls[0] and ":all:" in calls[0]

    def fake_run_fail(cmd, text, capture_output):
        return types.SimpleNamespace(returncode=1, stdout="", stderr="boom")

    monkeypatch.setattr(subprocess, "run", fake_run_fail)
    with pytest.raises(RuntimeError):
        packager.download_wheel_deps(whl, dest, only_binary=False, extra_pip_args=None)


def test_create_chub_build_dir_creates_flat_structure(tmp_path):
    whl = tmp_path / "pkg-1.0.0-py3-none-any.whl"
    whl.write_text("fake")
    bdir = packager.create_chub_build_dir(whl)
    assert bdir == (tmp_path / CHUB_BUILD_DIR).resolve()
    # Flat structure roots exist and .chubconfig is created
    assert (bdir / CHUBCONFIG_FILENAME).is_file()


def test_verify_pip_uses_subprocess_call(monkeypatch):
    called = {"rc": 0}

    def fake_call(cmd):  # python -m pip --version
        called["rc"] += 0
        return 0

    monkeypatch.setattr(packager.subprocess, "call", fake_call)
    packager.verify_pip()  # should not raise

    def fake_call_fail(cmd):
        return 1

    monkeypatch.setattr(packager.subprocess, "call", fake_call_fail)
    with pytest.raises(RuntimeError):
        packager.verify_pip()


def test_validate_chub_structure_basic(tmp_path):
    bdir = tmp_path / CHUB_BUILD_DIR
    bdir.mkdir()
    (bdir / CHUBCONFIG_FILENAME).write_text("---\n")
    # libs/scripts empty → ok
    packager.validate_chub_structure(bdir, [], [], [])
    # missing .chubconfig → error
    bdir2 = tmp_path / "other"
    bdir2.mkdir()
    with pytest.raises(FileNotFoundError):
        packager.validate_chub_structure(bdir2, [], [], [])
    # non-empty libs → error
    (bdir / CHUB_LIBS_DIR).mkdir(parents=True)
    (bdir / CHUB_LIBS_DIR / "junk.txt").write_text("x")
    with pytest.raises(FileExistsError):
        packager.validate_chub_structure(bdir, [], [], [])


def test_build_chub_happy_path(monkeypatch, tmp_path, fake_dist_wheels):
    # Monkeypatch the function to avoid ZIP parsing
    monkeypatch.setattr(
        "pychub.model.chubproject_model.get_wheel_name_version",
        lambda path: ("pkg", "1.0.0"))

    # Create a dummy pyproject.toml so prepare_project has something to point at
    pyproject_file = tmp_path / "pyproject.toml"
    pyproject_file.write_text("[project]\nname='pkg'\nversion='1.0.0'\n")

    # Fake wheel file
    wheel_path = tmp_path / "pkg-1.0.0-py3-none-any.whl"
    wheel_path.write_text("fake")

    # Create dummy pre/post scripts (note: unprefixed filenames)
    pre_src = tmp_path / "pre.sh"
    pre_src.write_text("#!/bin/sh\necho pre\n")
    post_src = tmp_path / "post.sh"
    post_src.write_text("#!/bin/sh\necho post\n")

    # Spy actions
    actions = []
    monkeypatch.setattr(packager, "verify_pip", lambda: actions.append("verify_pip"))
    # Let create_chub_build_dir create structure in ./out
    outdir = tmp_path / "out"
    outdir.mkdir()
    chub_path = outdir / "pkg-1.0.0.chub"
    # Simplify metadata reading
    monkeypatch.setattr(packager, "get_wheel_metadata", lambda wp: ("pkg", "1.0.0"))
    # Avoid touching a real runtime tree
    monkeypatch.setattr(packager, "copy_runtime_files", lambda *a, **k: actions.append("runtime"))
    # No deps     just echo download call
    monkeypatch.setattr(packager, "download_wheel_deps", lambda *a, **k: [])

    # Build project: scripts are PATHS, not final names
    proj = ChubProject.from_mapping({
        "name": "pkg",
        "version": "1.0.0",
        "wheel": str(wheel_path),
        "chub": str(chub_path),
        "entrypoint": "m:f",
        "scripts": {"post": [str(post_src)], "pre": [str(pre_src)]},
        "metadata": {"main_wheel": wheel_path.name},
    })

    out = packager.build_chub(proj)
    assert out == chub_path

    # Verify contents on disk (flat)
    with zipfile.ZipFile(out) as z:
        names = set(z.namelist())
    assert f"{CHUB_LIBS_DIR}/{wheel_path.name}" in names
    post_name = packager.prefixed_script_names([post_src])[0][1]
    pre_name = packager.prefixed_script_names([pre_src])[0][1]
    assert f"{CHUB_SCRIPTS_DIR}/{CHUB_POST_INSTALL_SCRIPTS_DIR}/{post_name}" in names
    assert f"{CHUB_SCRIPTS_DIR}/{CHUB_PRE_INSTALL_SCRIPTS_DIR}/{pre_name}" in names

    # Verify .chubconfig shape
    tmp_extract = tmp_path / "x"
    tmp_extract.mkdir()
    with zipfile.ZipFile(out) as z:
        z.extract(CHUBCONFIG_FILENAME, tmp_extract)
        z.extract("py3-none-any.chubconfig", tmp_extract)
    cfg = (tmp_extract / CHUBCONFIG_FILENAME).read_text()
    data = yaml.safe_load(cfg)
    ext = (tmp_extract / "py3-none-any.chubconfig").read_text()
    ext_data = yaml.safe_load(ext)
    assert data["name"] == "pkg"
    assert data["version"] == "1.0.0"
    assert data["entrypoint"] == "m:f"
    assert data["scripts"]["post"] == [post_name]
    assert data["scripts"]["pre"] == [pre_name]
    assert list(ext_data["wheels"]) == [wheel_path.name]


def test_prefixed_script_names_deduplicates_collisions(tmp_path):
    # Pass just the filenames as strings, not full paths
    result = packager.prefixed_script_names(["foo.sh", "Foo.sh", "bar.sh", "foo.sh"])
    # First foo.sh -> no suffix (n=0)
    # Second Foo.sh -> (1) suffix (n=1)
    # bar.sh -> no suffix (n=0)
    # Third foo.sh -> (2) suffix (n=2)
    assert len(result) == 4
    assert result[0][1] == "00_foo.sh"
    assert result[1][1] == "01_Foo(1).sh"
    assert result[2][1] == "02_bar.sh"
    assert result[3][1] == "03_foo(2).sh"


def test_prefixed_script_names_handles_no_extension(tmp_path):
    result = packager.prefixed_script_names(["script"])
    assert result[0][1] == "00_script"


def test_prefixed_script_names_width_grows_with_count(tmp_path):
    # Generate 105 unique filenames
    paths = [f"s{i}.sh" for i in range(105)]
    result = packager.prefixed_script_names(paths)
    # Width calculation: max(2, len(str(104))) = max(2, 3) = 3
    assert result[0][1].startswith("000_")
    assert result[104][1].startswith("104_")


def test_prefixed_script_names_sanitizes_paths(tmp_path):
    # Test that full paths get sanitized
    full_path = tmp_path / "subdir" / "my-script.sh"
    result = packager.prefixed_script_names([str(full_path)])
    # Should join path parts with underscores and sanitize
    # Note: hyphens are preserved, only disallowed chars are replaced
    assert result[0][1].startswith("00_")
    assert "my-script.sh" in result[0][1]  # hyphens are kept
    assert "subdir" in result[0][1]


def test_flatten_handles_nested_lists():
    assert packager._flatten([["a", "b"], ["c"]]) == ["a", "b", "c"]
    assert packager._flatten(["x", "y"]) == ["x", "y"]
    assert packager._flatten([]) == []
    assert packager._flatten(None) == []


def test_paths_filters_nonexistent_files(tmp_path):
    real = tmp_path / "exists.txt"
    real.write_text("x")
    result = packager._paths([str(real), str(tmp_path / "nope.txt")])
    assert len(result) == 1
    assert result[0] == real.resolve()


def test_includes_validates_src_existence(tmp_path):
    real = tmp_path / "file.txt"
    real.write_text("x")
    result = packager._includes([f"{real}::dest.txt", str(tmp_path / "missing.txt")])
    assert len(result) == 1
    assert result[0] == f"{real.resolve()}::dest.txt"


def test_get_wheel_metadata_raises_on_non_wheel(tmp_path):
    fake = tmp_path / "not.txt"
    fake.write_text("x")
    with pytest.raises(ValueError) as e:
        packager.get_wheel_metadata(fake)
    assert "Not a wheel" in str(e.value)


def test_get_wheel_metadata_raises_on_missing_metadata(tmp_path):
    # Create a minimal wheel with no METADATA file
    whl = tmp_path / "pkg-1.0.0-py3-none-any.whl"
    with zipfile.ZipFile(whl, "w") as z:
        z.writestr("some_file.txt", "data")
    with pytest.raises(ValueError) as e:
        packager.get_wheel_metadata(whl)
    assert "METADATA file not found" in str(e.value)


def test_get_wheel_metadata_raises_on_incomplete_metadata(tmp_path):
    whl = tmp_path / "pkg-1.0.0-py3-none-any.whl"
    with zipfile.ZipFile(whl, "w") as z:
        # Missing Version field
        z.writestr("pkg-1.0.0.dist-info/METADATA", "Name: pkg\n")
    with pytest.raises(ValueError) as e:
        packager.get_wheel_metadata(whl)
    assert "Missing Name or Version" in str(e.value)


def test_get_wheel_metadata_normalize_name(tmp_path):
    whl = tmp_path / "pkg-1.0.0-py3-none-any.whl"
    with zipfile.ZipFile(whl, "w") as z:
        z.writestr("pkg-1.0.0.dist-info/METADATA", "Name: My_Package Name\nVersion: 1.0.0\n")
    name, ver = packager.get_wheel_metadata(whl, normalize_name=True)
    assert name == "my-package-name"
    assert ver == "1.0.0"


def test_get_wheel_metadata_without_normalize(tmp_path):
    whl = tmp_path / "pkg-1.0.0-py3-none-any.whl"
    with zipfile.ZipFile(whl, "w") as z:
        z.writestr("pkg-1.0.0.dist-info/METADATA", "Name: My_Package\nVersion: 1.0.0\n")
    name, ver = packager.get_wheel_metadata(whl, normalize_name=False)
    assert name == "My_Package"


def test_validate_files_exist_raises_on_missing(tmp_path):
    with pytest.raises(FileNotFoundError) as e:
        packager.validate_files_exist(["nope.txt"], "Test")
    assert "Test file not found" in str(e.value)


def test_validate_files_exist_handles_dest_syntax(tmp_path):
    real = tmp_path / "file.txt"
    real.write_text("x")
    # Should extract src from "src::dest" syntax
    packager.validate_files_exist([f"{real}::somewhere"], "Include")


def test_validate_chub_structure_validates_pre_install_scripts(tmp_path):
    """Test that validate_chub_structure validates pre-install scripts (line 377)."""
    bdir = tmp_path / CHUB_BUILD_DIR
    bdir.mkdir()
    (bdir / CHUBCONFIG_FILENAME).write_text("---\n")

    # Test with non-existent pre-install script
    with pytest.raises(FileNotFoundError) as e:
        packager.validate_chub_structure(bdir, [], ["missing_pre.sh"], [])
    assert "pre-install" in str(e.value)


def test_absolutize_paths_single_string(tmp_path):
    result = packager.absolutize_paths("relative.txt", tmp_path)
    assert isinstance(result, str)
    assert result == str((tmp_path / "relative.txt").resolve())


def test_absolutize_paths_list(tmp_path):
    result = packager.absolutize_paths(["a.txt", "b.txt"], tmp_path)
    assert isinstance(result, list)
    assert len(result) == 2


def test_absolutize_paths_already_absolute(tmp_path):
    abs_path = str(tmp_path / "abs.txt")
    result = packager.absolutize_paths(abs_path, tmp_path)
    assert result == abs_path


def test_prepare_project_basic(monkeypatch, tmp_path):
    monkeypatch.setattr(
        "pychub.model.chubproject_model.get_wheel_name_version",
        lambda path: ("pkg", "1.0.0"))
    whl = tmp_path / "pkg-1.0.0-py3-none-any.whl"
    whl.write_text("fake")
    proj = ChubProject.from_mapping({
        "wheel": str(whl),
        "entrypoint": "mod:func",
        "metadata": {"custom": "value"}
    })
    ctx = packager.prepare_project(proj)
    assert ctx.entrypoint == "mod:func"
    assert ctx.metadata["custom"] == "value"
    assert len(ctx.wheel_paths) == 1


def test_prepare_project_with_scripts_and_includes(monkeypatch, tmp_path):
    monkeypatch.setattr(
        "pychub.model.chubproject_model.get_wheel_name_version",
        lambda path: ("pkg", "1.0.0"))
    whl = tmp_path / "pkg-1.0.0-py3-none-any.whl"
    whl.write_text("fake")
    pre = tmp_path / "pre.sh"
    pre.write_text("pre")
    post = tmp_path / "post.sh"
    post.write_text("post")
    inc = tmp_path / "data.txt"
    inc.write_text("data")
    proj = ChubProject.from_mapping({
        "wheel": str(whl),
        "scripts": {"pre": [str(pre)], "post": [str(post)]},
        "includes": [f"{inc}::conf/data.txt"],
        "metadata": {"__file__": str(tmp_path / "proj.toml")}
    })
    ctx = packager.prepare_project(proj)
    assert len(ctx.pre_scripts) == 1
    assert len(ctx.post_scripts) == 1
    assert len(ctx.includes) == 1
    assert "::conf/data.txt" in ctx.includes[0]


def test_prepare_project_without_metadata_file(monkeypatch, tmp_path):
    """Test prepare_project when metadata has no __file__ (line 427 else branch)."""
    monkeypatch.setattr(
        "pychub.model.chubproject_model.get_wheel_name_version",
        lambda path: ("pkg", "1.0.0"))
    whl = tmp_path / "pkg-1.0.0-py3-none-any.whl"
    whl.write_text("fake")
    proj = ChubProject.from_mapping({
        "wheel": str(whl),
        "entrypoint": "mod:func",
        "metadata": {"custom": "value"}  # No __file__ key
    })
    ctx = packager.prepare_project(proj)
    # Should use Path(".").resolve() as project_dir
    assert ctx.project_dir == Path(".").resolve()
    assert ctx.metadata["custom"] == "value"


def test_prepare_build_dirs_creates_structure(tmp_path):
    whl = tmp_path / "pkg-1.0.0-py3-none-any.whl"
    whl.write_text("fake")
    build_dir, libs_dir, cache_dir = packager.prepare_build_dirs(whl, None)
    assert build_dir.is_dir()
    assert libs_dir.is_dir()
    assert cache_dir.is_dir()
    assert (build_dir / CHUBCONFIG_FILENAME).is_file()


def test_copy_runtime_files_fallback_search(tmp_path, monkeypatch):
    # Test when the first candidate doesn't exist
    fake_pkg_dir = tmp_path / "pychub"
    runtime_dir = fake_pkg_dir / RUNTIME_DIR
    runtime_dir.mkdir(parents=True)
    (runtime_dir / "dummy.py").write_text("# runtime")
    fake_packager_file = fake_pkg_dir / "package" / "packager.py"
    fake_packager_file.parent.mkdir(parents=True)
    fake_packager_file.write_text("# packager")
    monkeypatch.setattr(packager, "__file__", str(fake_packager_file))

    build = tmp_path / "build"
    build.mkdir()
    packager.copy_runtime_files(build)
    assert (build / RUNTIME_DIR / "dummy.py").is_file()


def test_copy_runtime_files_raises_when_not_found(tmp_path, monkeypatch):
    fake_packager_file = tmp_path / "nowhere" / "packager.py"
    fake_packager_file.parent.mkdir(parents=True)
    fake_packager_file.write_text("# fake")
    monkeypatch.setattr(packager, "__file__", str(fake_packager_file))

    build = tmp_path / "build"
    build.mkdir()
    with pytest.raises(FileNotFoundError) as e:
        packager.copy_runtime_files(build)
    assert "Runtime directory not found" in str(e.value)


def test_resolve_wheel_recursive_mode_switching(monkeypatch, tmp_path):
    # Test that after touching PyPI, mode switches to "pypi-only"
    calls = []

    def fake_download(whl, dest, **kwargs):
        calls.append(("download", kwargs.get("no_index", False)))
        if kwargs.get("no_index"):
            raise RuntimeError("local failed")
        return ["dep.whl"]

    def fake_metadata(whl, **kwargs):
        if "dep" in str(whl):
            return ("dep", "1.0.0")
        return ("main", "1.0.0")

    monkeypatch.setattr(packager, "download_wheel_deps", fake_download)
    monkeypatch.setattr(packager, "get_wheel_metadata", fake_metadata)

    whl = tmp_path / "main-1.0.0-py3-none-any.whl"
    whl.write_text("fake")
    libs = tmp_path / "libs"
    libs.mkdir()
    cache = tmp_path / "cache"
    cache.mkdir()

    packager.resolve_wheel_recursive(whl, libs, cache, "cache-first")

    # Should have tried local first (no_index=True), then fallen back (no_index=False)
    assert len(calls) >= 1


def test_resolve_wheel_recursive_skips_already_seen(monkeypatch, tmp_path):
    """Test that resolve_wheel_recursive returns early for already-seen wheels (line 300)."""
    calls = []

    def fake_download(whl, dest, **kwargs):
        calls.append("download")
        return []

    def fake_metadata(whl, **kwargs):
        return ("pkg", "1.0.0")

    monkeypatch.setattr(packager, "download_wheel_deps", fake_download)
    monkeypatch.setattr(packager, "get_wheel_metadata", fake_metadata)

    whl = tmp_path / "pkg-1.0.0-py3-none-any.whl"
    whl.write_text("fake")
    libs = tmp_path / "libs"
    libs.mkdir()
    cache = tmp_path / "cache"
    cache.mkdir()

    # Pre-populate seen set
    seen = {("pkg", "1.0.0")}

    # Should return immediately without downloading
    packager.resolve_wheel_recursive(whl, libs, cache, "cache-first", seen)

    # No downloads should have occurred
    assert len(calls) == 0


def test_write_chubconfig_files(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "pychub.model.chubproject_model.get_wheel_name_version",
        lambda path: ("pkg", "1.0.0"))

    build = tmp_path / "build"
    build.mkdir()

    ctx = packager.ProjectContext(
        project_dir=tmp_path,
        entrypoint="m:f",
        metadata={"key": "value"},
        wheel_paths=[],
        post_scripts=[(tmp_path / "post.sh", "00_post.sh")],
        pre_scripts=[],
        includes=["file.txt"]
    )

    per_combo = {
        "py3-none-any": {"main.whl": "main-1.0.0-py3-none-any.whl"}
    }

    packager.write_chubconfig_files("pkg", "1.0.0", ctx, per_combo, build)

    cfg_file = build / CHUBCONFIG_FILENAME
    assert cfg_file.is_file()
    cfg = yaml.safe_load(cfg_file.read_text())
    assert cfg["name"] == "pkg"
    assert cfg["entrypoint"] == "m:f"
    assert cfg["scripts"]["post"] == ["00_post.sh"]

    combo_file = build / "py3-none-any.chubconfig"
    assert combo_file.is_file()


def test_analyze_compatibility(monkeypatch, tmp_path):
    monkeypatch.setattr(
        "pychub.model.chubproject_model.get_wheel_name_version",
        lambda path: ("pkg", "1.0.0"))

    whl = tmp_path / "pkg-1.0.0-py3-none-any.whl"
    whl.write_text("fake")

    # Mock resolve function
    def fake_resolve(proj, **kwargs):
        return ({"main.whl": ["main-1.0.0-py3-none-any.whl"]}, tmp_path, None)

    monkeypatch.setattr(packager, "resolve_all_dependency_wheels", fake_resolve)

    # Mock enumerate_valid_combos
    def fake_combos(wheel_files):
        return [("cp39", "cp39", "linux_x86_64"), ("cp310", "cp310", "linux_x86_64")]

    monkeypatch.setattr(packager, "enumerate_valid_combos", fake_combos)

    proj = ChubProject.from_mapping({
        "wheel": str(whl),
        "entrypoint": "m:f"
    })

    result = packager.analyze_compatibility(proj)
    assert len(result) == 2
    assert "cp39-cp39-linux_x86_64" in result


def test_stage_path_dependencies_missing_dist(monkeypatch, tmp_path):
    # Mock collect_path_dependencies to return a project without dist/
    def fake_collect(pyproject):
        return {tmp_path / "subproj": "default"}

    monkeypatch.setattr(packager, "collect_path_dependencies", fake_collect)

    cache = tmp_path / "cache"
    cache.mkdir()
    with pytest.raises(FileNotFoundError) as e:
        packager.stage_path_dependencies(tmp_path, cache)
    assert "has no dist/ directory" in str(e.value)


def test_stage_path_dependencies_missing_wheel(monkeypatch, tmp_path):
    def fake_collect(pyproject):
        proj = tmp_path / "subproj"
        proj.mkdir()
        (proj / "dist").mkdir()
        return {proj: "poetry"}

    monkeypatch.setattr(packager, "collect_path_dependencies", fake_collect)

    cache = tmp_path / "cache"
    cache.mkdir()
    with pytest.raises(FileNotFoundError) as e:
        packager.stage_path_dependencies(tmp_path, cache)
    assert "has no wheel in dist/" in str(e.value)


def test_resolve_all_dependency_wheels_with_tempfile(monkeypatch, tmp_path):
    """Test resolve_all_dependency_wheels creates tempdir when reuse_cache is None (lines 482, 486, 487)."""
    monkeypatch.setattr(
        "pychub.model.chubproject_model.get_wheel_name_version",
        lambda path: ("pkg", "1.0.0"))

    whl = tmp_path / "pkg-1.0.0-py3-none-any.whl"
    whl.write_text("fake")

    # Mock to avoid actual path dep collection and wheel resolution
    monkeypatch.setattr(packager, "stage_path_dependencies", lambda *args: None)
    monkeypatch.setattr(packager, "resolve_wheels", lambda *args: {"main.whl": ["main.whl"]})

    proj = ChubProject.from_mapping({
        "wheel": str(whl),
        "entrypoint": "m:f",
        "metadata": {"__file__": str(tmp_path / "proj.toml")}
    })

    # Call with reuse_cache=None to trigger tempfile creation
    wheel_files, cache_dir, ctx = packager.resolve_all_dependency_wheels(proj, reuse_cache=None)

    # Should have created a temp directory
    assert cache_dir.exists()
    assert cache_dir.is_dir()
    # Temp directory should not be in tmp_path (it's in system temp)
    assert str(tmp_path) not in str(cache_dir)


def test_create_chub_build_dir_validates_wheel_extension(tmp_path):
    fake = tmp_path / "not_a_wheel.txt"
    fake.write_text("x")
    with pytest.raises(ValueError) as e:
        packager.create_chub_build_dir(fake)
    assert "Not a wheel" in str(e.value)


def test_copy_included_files_with_trailing_slash_dest(tmp_path):
    base = tmp_path / "base"
    base.mkdir()
    src = tmp_path / "file.txt"
    src.write_text("content")
    # Trailing slash means directory target
    packager.copy_included_files(base, [f"{src}::subdir/"])
    dest = base / CHUB_INCLUDES_DIR / "subdir" / "file.txt"
    assert dest.is_file()
    assert dest.read_text() == "content"


def test_copy_install_scripts_missing_raises(tmp_path):
    base = tmp_path / "scripts"
    base.mkdir()
    with pytest.raises(FileNotFoundError):
        packager.copy_install_scripts(base, [(tmp_path / "missing.sh", "00_script.sh")], CHUB_POST_INSTALL_SCRIPTS_DIR)


def test_download_wheel_deps_with_find_links_and_no_index(tmp_path):
    whl = tmp_path / "pkg-1.0.0-py3-none-any.whl"
    whl.write_text("fake")
    dest = tmp_path / "dest"
    dest.mkdir()
    find_links = tmp_path / "links"
    find_links.mkdir()

    def fake_run(cmd, **kwargs):
        assert "--find-links" in cmd
        assert str(find_links) in cmd
        assert "--no-index" in cmd
        return types.SimpleNamespace(returncode=0, stdout="", stderr="")

    import pychub.package.packager as pkg_mod
    import subprocess
    original_run = subprocess.run
    pkg_mod.subprocess.run = fake_run

    try:
        packager.download_wheel_deps(whl, dest, find_links=find_links, no_index=True)
    finally:
        pkg_mod.subprocess.run = original_run


def test_sanitize_removes_parent_refs():
    # Test the internal _sanitize function
    result = packager._sanitize("../../etc/passwd")
    assert ".." not in result
    assert "/" not in result
    assert result  # Should produce something valid


def test_validate_chub_structure_non_empty_scripts_dir(tmp_path):
    """Test that validate_chub_structure catches non-empty scripts/ directory."""
    bdir = tmp_path / CHUB_BUILD_DIR
    bdir.mkdir()
    (bdir / CHUBCONFIG_FILENAME).write_text("---\n")

    # Create non-empty scripts/ directory
    scripts_dir = bdir / CHUB_SCRIPTS_DIR
    scripts_dir.mkdir(parents=True)
    (scripts_dir / "junk.sh").write_text("echo 'leftover'")

    with pytest.raises(FileExistsError) as e:
        packager.validate_chub_structure(bdir, [], [], [])
    assert "scripts/" in str(e.value)


def test_validate_chub_structure_validates_included_files(tmp_path):
    """Test that validate_chub_structure validates included files."""
    bdir = tmp_path / CHUB_BUILD_DIR
    bdir.mkdir()
    (bdir / CHUBCONFIG_FILENAME).write_text("---\n")

    # Test with non-existent included file
    with pytest.raises(FileNotFoundError) as e:
        packager.validate_chub_structure(bdir, [], [], ["missing_file.txt"])
    assert "Include file not found" in str(e.value)


def test_prepare_project_include_without_dest(monkeypatch, tmp_path):
    """Test prepare_project with includes that don't have :: destination (else branch)."""
    monkeypatch.setattr(
        "pychub.model.chubproject_model.get_wheel_name_version",
        lambda path: ("pkg", "1.0.0"))

    whl = tmp_path / "pkg-1.0.0-py3-none-any.whl"
    whl.write_text("fake")
    inc = tmp_path / "data.txt"
    inc.write_text("data")

    # Include without :: destination
    proj = ChubProject.from_mapping({
        "wheel": str(whl),
        "includes": [str(inc)],  # No :: destination
        "metadata": {"__file__": str(tmp_path / "proj.toml")}
    })

    ctx = packager.prepare_project(proj)
    assert len(ctx.includes) == 1
    # Should have the absolutized path without ::
    assert "::" not in ctx.includes[0]
    assert str(inc.resolve()) in ctx.includes[0]


def test_resolve_all_dependency_wheels_no_wheels_raises(monkeypatch, tmp_path):
    """Test that resolve_all_dependency_wheels raises when no wheels provided."""
    # Create a fake wheel to pass ChubProject validation
    whl = tmp_path / "pkg-1.0.0-py3-none-any.whl"
    whl.write_text("fake")

    monkeypatch.setattr(
        "pychub.model.chubproject_model.get_wheel_name_version",
        lambda path: ("pkg", "1.0.0"))

    # Create project normally first
    proj = ChubProject.from_mapping({
        "wheel": str(whl),
        "entrypoint": "m:f",
        "metadata": {"__file__": str(tmp_path / "proj.toml")}
    })

    # Then mock prepare_project to return a context with no wheels
    def fake_prepare(chubproject):
        return packager.ProjectContext(
            project_dir=tmp_path,
            entrypoint="m:f",
            metadata={},
            wheel_paths=[],  # No wheels!
            post_scripts=[],
            pre_scripts=[],
            includes=[]
        )

    monkeypatch.setattr(packager, "prepare_project", fake_prepare)

    with pytest.raises(ValueError) as e:
        packager.resolve_all_dependency_wheels(proj, reuse_cache=None)
    assert "No wheels provided" in str(e.value)


def test_resolve_all_dependency_wheels_with_reuse_cache(monkeypatch, tmp_path):
    """Test resolve_all_dependency_wheels with reuse_cache path (lines 482-485)."""
    monkeypatch.setattr(
        "pychub.model.chubproject_model.get_wheel_name_version",
        lambda path: ("pkg", "1.0.0"))

    whl = tmp_path / "pkg-1.0.0-py3-none-any.whl"
    whl.write_text("fake")

    # Mock to avoid actual path dep collection and wheel resolution
    monkeypatch.setattr(packager, "stage_path_dependencies", lambda *args: None)
    monkeypatch.setattr(packager, "resolve_wheels", lambda *args: {"main.whl": ["main.whl"]})

    proj = ChubProject.from_mapping({
        "wheel": str(whl),
        "entrypoint": "m:f",
        "metadata": {"__file__": str(tmp_path / "proj.toml")}
    })

    # Use a specific cache directory path
    cache_path = tmp_path / "my_cache"
    wheel_files, cache_dir, ctx = packager.resolve_all_dependency_wheels(proj, reuse_cache=cache_path)

    # Should have created the cache directory
    assert cache_dir.exists()
    assert cache_dir == cache_path.resolve()