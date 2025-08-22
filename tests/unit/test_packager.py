import subprocess
import sys
import types
import zipfile
from pathlib import Path
from textwrap import dedent

import pytest
import yaml

from pychubby import packager
from pychubby.constants import (
    CHUB_BUILD_DIR,
    CHUB_LIBS_DIR,
    CHUB_SCRIPTS_DIR,
    CHUBCONFIG_FILENAME,
    RUNTIME_DIR,
)


@pytest.fixture
def build_env(tmp_path):
    wheel = tmp_path / "pkg-1.0.0-py3-none-any.whl"
    wheel.write_text("fake")

    build_dir = packager.create_chub_build_dir_structure(wheel)
    pkg_dir = packager.get_wheel_package_dir("pkg", "1.0.0", build_dir)

    return wheel, build_dir, pkg_dir


@pytest.fixture(autouse=True)
def isolate_cwd(tmp_path, monkeypatch):
    # Run tests in an isolated working directory
    monkeypatch.chdir(tmp_path)
    return tmp_path


@pytest.fixture
def temp_runtime(monkeypatch, tmp_path):
    # Create a fake runtime dir adjacent to a fake module file path and point packager.__file__ to it
    fake_pkg_dir = tmp_path / "fakepkg"
    fake_pkg_dir.mkdir()
    (fake_pkg_dir / RUNTIME_DIR).mkdir()
    fake_packager_file = fake_pkg_dir / "packager.py"
    fake_packager_file.write_text("# pretend")

    # Point the module's __file__ to the fake location so copy_runtime_files finds runtime
    monkeypatch.setattr(packager, "__file__", str(fake_packager_file))
    return fake_pkg_dir


def test_create_chub_archive_includes_all_content(tmp_path):
    build_dir = tmp_path / "build"
    build_dir.mkdir()
    (build_dir / "a.txt").write_text("A")
    (build_dir / "dir").mkdir()
    (build_dir / "dir" / "b.txt").write_text("B")

    archive_path = tmp_path / "out.chub"
    out = packager.create_chub_archive(build_dir, archive_path)

    assert out == archive_path
    with zipfile.ZipFile(archive_path) as zf:
        names = set(zf.namelist())
    # Note: directories may or may not be present explicitly; files must be
    assert "a.txt" in names
    assert "dir/b.txt" in names


def test_copy_runtime_files_writes_runtime_and_main(tmp_path, temp_runtime):
    chub_build_dir = tmp_path / "chub"
    chub_build_dir.mkdir()

    packager.copy_runtime_files(chub_build_dir)

    assert (chub_build_dir / RUNTIME_DIR).is_dir()
    main_py = chub_build_dir / "__main__.py"
    assert main_py.is_file()
    content = main_py.read_text()
    assert f"run_module('{RUNTIME_DIR}'" in content


def test_copy_included_files_noop_on_none_and_empty(tmp_path):
    pkg_dir = tmp_path / "pkg"
    pkg_dir.mkdir()
    # None and [] should not raise and should not create anything
    packager.copy_included_files(pkg_dir, None)
    packager.copy_included_files(pkg_dir, [])
    assert list(pkg_dir.iterdir()) == []


def test_copy_included_files_basic_and_with_dest(tmp_path):
    pkg_dir = tmp_path / "pkg"
    pkg_dir.mkdir()

    src1 = tmp_path / "file1.txt"
    src1.write_text("1")
    src2 = tmp_path / "file2.txt"
    src2.write_text("2")

    packager.copy_included_files(pkg_dir, [str(src1), f"{src2}::data/inside.txt"])

    assert (pkg_dir / "file1.txt").read_text() == "1"
    assert (pkg_dir / "data" / "inside.txt").read_text() == "2"


def test_copy_included_files_missing_raises(tmp_path):
    pkg_dir = tmp_path / "pkg"
    pkg_dir.mkdir()

    with pytest.raises(FileNotFoundError) as e:
        packager.copy_included_files(pkg_dir, ["nope.txt"])
    assert "Included file not found" in str(e.value)


def test_copy_included_files_prevent_directory_traversal(tmp_path):
    pkg_dir = tmp_path / "pkg"
    pkg_dir.mkdir()
    src = tmp_path / "x.txt"
    src.write_text("x")

    # Attempt to escape with ../
    with pytest.raises(ValueError) as e:
        packager.copy_included_files(pkg_dir, [f"{src}::../outside.txt"])
    assert "escapes wheel package directory" in str(e.value)


def test_copy_post_install_scripts_noop_and_success(build_env, tmp_path):
    wheel_path, build_dir, pkg_dir = build_env

    script = tmp_path / "foo.sh"
    script.write_text("echo hi")

    packager.copy_post_install_scripts(pkg_dir, [str(script)])

    expected = pkg_dir / CHUB_SCRIPTS_DIR / script.name
    assert expected.is_file()


def test_copy_post_install_scripts_missing_raises(tmp_path):
    pkg_dir = tmp_path / "pkg"
    pkg_dir.mkdir()
    with pytest.raises(FileNotFoundError) as e:
        packager.copy_post_install_scripts(pkg_dir, ["nope.sh"])
    assert "Post-install script not found" in str(e.value)


def test_create_chubconfig_yaml_shape_and_markers():
    text = packager.create_chubconfig(
        package_name="Requests_Lib",
        version="2.31.0",
        entrypoint="module:func",
        post_install_scripts=["a.sh"],
        included_files=["x.txt", "y.txt::z.txt"],
        metadata={"k": "v"},
    )
    assert text.startswith("---")
    assert text.endswith("\n\n")

    data = list(yaml.safe_load_all(text))[0]
    assert data["name"] == "Requests_Lib"
    assert data["version"] == "2.31.0"
    assert data["entrypoint"] == "module:func"
    assert data["post_install_scripts"] == ["a.sh"]
    assert data["includes"] == ["x.txt", "y.txt::z.txt"]
    assert data["metadata"] == {"k": "v"}


def test_create_chubconfig_defaults_for_none():
    text = packager.create_chubconfig(
        package_name="n", version="1", entrypoint="m:f", post_install_scripts=None, included_files=None, metadata=None
    )
    data = list(yaml.safe_load_all(text))[0]
    assert data["post_install_scripts"] == []
    assert data["includes"] == []
    assert data["metadata"] == {}


def test_download_wheel_deps_builds_cmd_and_handles_errors(monkeypatch, tmp_path):
    calls = []

    def fake_run(cmd, text, capture_output):
        calls.append(cmd)
        # simulate success
        return types.SimpleNamespace(returncode=0, stdout="ok", stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)
    wheel = tmp_path / "pkg-1.0.0-py3-none-any.whl"
    wheel.write_text("fake")
    dest = tmp_path / "deps"

    packager.download_wheel_deps(wheel, dest, only_binary=True, extra_pip_args=["--no-cache"])

    assert calls, "subprocess.run should be called"
    cmd = calls[0]
    assert cmd[:3] == [sys.executable, "-m", "pip"]
    assert "download" in cmd
    assert "--only-binary" in cmd and ":all:" in cmd
    assert "--no-cache" in cmd

    # Failure case
    def fake_run_fail(cmd, text, capture_output):
        return types.SimpleNamespace(returncode=1, stdout="", stderr="boom")

    monkeypatch.setattr(subprocess, "run", fake_run_fail)
    with pytest.raises(RuntimeError) as e:
        packager.download_wheel_deps(wheel, dest, only_binary=False, extra_pip_args=None)
    assert "pip download failed" in str(e.value)


def test_get_wheel_metadata_happy_and_options(tmp_path):
    # Create a wheel with METADATA
    whl = tmp_path / "pkg-1.2.3-py3-none-any.whl"
    dist_info = "pkg-1.2.3.dist-info/METADATA"
    meta = dedent(
        """\
        Metadata-Version: 2.1
        Name: Requests_Lib
        Version: 1.2.3
        """
    )
    with zipfile.ZipFile(whl, "w") as z:
        z.writestr(dist_info, meta)

    name, ver = packager.get_wheel_metadata(whl, normalize_name=True)
    assert name == "requests-lib"  # normalized
    assert ver == "1.2.3"

    name2, ver2 = packager.get_wheel_metadata(whl, normalize_name=False)
    assert name2 == "Requests_Lib"
    assert ver2 == "1.2.3"


def test_get_wheel_metadata_errors(tmp_path):
    not_whl = tmp_path / "file.txt"
    not_whl.write_text("x")
    with pytest.raises(ValueError) as e:
        packager.get_wheel_metadata(not_whl)
    assert "Not a wheel" in str(e.value)

    # Missing METADATA
    bad_whl = tmp_path / "bad-0.0.1.whl"
    with zipfile.ZipFile(bad_whl, "w") as z:
        z.writestr("some/file.txt", "x")
    with pytest.raises(ValueError) as e:
        packager.get_wheel_metadata(bad_whl)
    assert "METADATA file not found" in str(e.value)

    # METADATA missing fields
    bad_whl2 = tmp_path / "bad2-0.0.1.whl"
    with zipfile.ZipFile(bad_whl2, "w") as z:
        z.writestr("bad2-0.0.1.dist-info/METADATA", "Name:\n")
    with pytest.raises(ValueError) as e:
        packager.get_wheel_metadata(bad_whl2)
    assert "Missing Name or Version" in str(e.value)


def test_get_wheel_package_dir_creates_structure(tmp_path):
    chub_build_dir = tmp_path / CHUB_BUILD_DIR
    chub_build_dir.mkdir()
    pkg_dir = packager.get_wheel_package_dir("pkg", "1.0.0", chub_build_dir)
    assert pkg_dir.is_dir()
    assert (pkg_dir / CHUB_LIBS_DIR).is_dir()
    assert (pkg_dir / CHUB_SCRIPTS_DIR).is_dir()


def test_get_chub_build_dir_selection_and_validation(tmp_path):
    whl = tmp_path / "x-0.1.0.whl"
    whl.write_text("fake")

    # Default uses wheel parent
    d1 = packager.get_chub_build_dir(whl)
    assert d1 == (tmp_path / CHUB_BUILD_DIR).resolve()

    # When chub_path is given, use its parent
    chub_path = tmp_path / "output" / "out.chub"
    d2 = packager.get_chub_build_dir(whl, chub_path)
    assert d2 == (chub_path.parent / CHUB_BUILD_DIR).resolve()

    # Guard for wrong suffix
    with pytest.raises(ValueError):
        packager.get_chub_build_dir(tmp_path / "not_a_wheel.txt")


def test_create_chub_build_dir_structure_creates_dir_and_config(tmp_path):
    whl = tmp_path / "p-0.0.1.whl"
    whl.write_text("fake")
    build_dir = packager.create_chub_build_dir_structure(whl)
    assert build_dir.is_dir()
    cfg = build_dir / CHUBCONFIG_FILENAME
    assert cfg.is_file()


def test_verify_pip(monkeypatch):
    # When pip exists
    monkeypatch.setattr(packager.shutil, "which", lambda name: "/usr/bin/pip")
    packager.verify_pip()  # should not raise

    # When pip missing
    monkeypatch.setattr(packager.shutil, "which", lambda name: None)
    with pytest.raises(RuntimeError) as e:
        packager.verify_pip()
    assert "pip not found" in str(e.value)


def test_validate_files_exist_with_and_without_dest(tmp_path):
    f1 = tmp_path / "a.txt"
    f1.write_text("a")
    f2 = tmp_path / "b.txt"
    f2.write_text("b")

    # Should pass
    packager.validate_files_exist([str(f1), f"{f2}::dest/b.txt"], context="Include")

    with pytest.raises(FileNotFoundError):
        packager.validate_files_exist(["missing.txt", "also::nope.txt"], context="Include")


def test_validate_chub_structure_happy(tmp_path):
    build_dir = tmp_path / CHUB_BUILD_DIR
    build_dir.mkdir()
    # .chubconfig exists with different name/version or empty
    (build_dir / CHUBCONFIG_FILENAME).write_text("---\nname: other\nversion: 0.0.1\n")

    wheel_package_dir = build_dir / "pkg-1.2.3"
    # Must not exist yet
    assert not wheel_package_dir.exists()

    # Validates fine when entrypoint ok and files lists empty
    packager.validate_chub_structure(
        wheel_package_dir,
        entrypoint="mod:func",
        post_install_scripts=[],
        included_files=[],
    )


def test_validate_chub_structure_prevent_overwrite(tmp_path):
    build_dir = tmp_path / CHUB_BUILD_DIR
    build_dir.mkdir()
    (build_dir / CHUBCONFIG_FILENAME).write_text("---\n")

    wheel_package_dir = build_dir / "pkg-1.2.3"
    wheel_package_dir.mkdir(parents=True)
    with pytest.raises(FileExistsError) as e:
        packager.validate_chub_structure(wheel_package_dir)
    assert "already exists" in str(e.value)


def test_validate_chub_structure_missing_chubconfig(tmp_path):
    build_dir = tmp_path / CHUB_BUILD_DIR
    build_dir.mkdir()
    wheel_package_dir = build_dir / "pkg-1.2.3"
    with pytest.raises(FileNotFoundError) as e:
        packager.validate_chub_structure(wheel_package_dir)
    assert "Missing" in str(e.value)


def test_validate_chub_structure_bad_yaml(tmp_path):
    build_dir = tmp_path / CHUB_BUILD_DIR
    build_dir.mkdir()
    # Invalid YAML
    (build_dir / CHUBCONFIG_FILENAME).write_text(":\nbad\n- [")
    wheel_package_dir = build_dir / "pkg-1.2.3"
    with pytest.raises(ValueError) as e:
        packager.validate_chub_structure(wheel_package_dir)
    assert "Failed to parse" in str(e.value)


def test_validate_chub_structure_collision(tmp_path):
    build_dir = tmp_path / CHUB_BUILD_DIR
    build_dir.mkdir()
    (build_dir / CHUBCONFIG_FILENAME).write_text(
        "---\nname: pkg\nversion: 1.2.3\n---\nname: other\nversion: 0.0.1\n"
    )
    wheel_package_dir = build_dir / "pkg-1.2.3"
    with pytest.raises(ValueError) as e:
        packager.validate_chub_structure(wheel_package_dir)
    assert "already defined" in str(e.value)


def test_validate_chub_structure_reserved_names(tmp_path):
    build_dir = tmp_path / CHUB_BUILD_DIR
    build_dir.mkdir()
    (build_dir / CHUBCONFIG_FILENAME).write_text("---\n")

    for reserved in {"runtime", "__main__.py", CHUBCONFIG_FILENAME}:
        wheel_package_dir = build_dir / f"{reserved}-1.0.0"
        with pytest.raises(ValueError) as e:
            packager.validate_chub_structure(wheel_package_dir)
        assert "reserved name" in str(e.value)


def test_validate_chub_structure_entrypoint_format(tmp_path):
    build_dir = tmp_path / CHUB_BUILD_DIR
    build_dir.mkdir()
    (build_dir / CHUBCONFIG_FILENAME).write_text("---\n")
    wheel_package_dir = build_dir / "pkg-1.2.3"
    with pytest.raises(ValueError) as e:
        packager.validate_chub_structure(wheel_package_dir, entrypoint="no_colon")
    assert "Invalid entrypoint format" in str(e.value)


def test_validate_chub_structure_validates_files_exist(tmp_path):
    build_dir = tmp_path / CHUB_BUILD_DIR
    build_dir.mkdir()
    (build_dir / CHUBCONFIG_FILENAME).write_text("---\n")
    wheel_package_dir = build_dir / "pkg-1.2.3"

    existing = tmp_path / "ok.txt"
    existing.write_text("ok")

    # includes ok, scripts missing
    with pytest.raises(FileNotFoundError):
        packager.validate_chub_structure(
            wheel_package_dir,
            included_files=[str(existing)],
            post_install_scripts=["missing.sh"],
        )


def test_validate_chub_structure_libs_scripts_nonempty_branch(monkeypatch, tmp_path):
    # This branch is logically unreachable in normal flow due to the early exists() guard.
    # We simulate it by monkeypatching Path.exists selectively.
    build_dir = tmp_path / CHUB_BUILD_DIR
    build_dir.mkdir()
    (build_dir / CHUBCONFIG_FILENAME).write_text("---\n")

    wheel_package_dir = build_dir / "pkg-1.2.3"
    libs = wheel_package_dir / CHUB_LIBS_DIR
    scripts = wheel_package_dir / CHUB_SCRIPTS_DIR

    libs.mkdir(parents=True)
    (libs / "junk.txt").write_text("x")

    original_exists = Path.exists

    def fake_exists(self: Path):
        # Pretend the package dir itself does not exist to bypass the first guard,
        # but its libs directory does exist.
        if self == wheel_package_dir:
            return False
        return original_exists(self)

    monkeypatch.setattr(Path, "exists", fake_exists)

    with pytest.raises(FileExistsError) as e:
        packager.validate_chub_structure(wheel_package_dir)
    assert "libs/ directory" in str(e.value)


def test_build_chub_happy_path(monkeypatch, tmp_path, capsys):
    wheel_path = tmp_path / "pkg-1.0.0-py3-none-any.whl"
    wheel_path.write_text("fake")

    actions = []

    monkeypatch.setattr(packager, "verify_pip", lambda: actions.append("verify_pip"))

    build_dir = tmp_path / "out" / CHUB_BUILD_DIR

    def fake_create_build_dir_structure(wp, cp=None):
        actions.append("create_build_dir")
        build_dir.mkdir(parents=True, exist_ok=True)
        (build_dir / CHUBCONFIG_FILENAME).write_text("")
        return build_dir

    monkeypatch.setattr(packager, "create_chub_build_dir_structure", fake_create_build_dir_structure)
    monkeypatch.setattr(packager, "get_wheel_metadata", lambda wp: ("pkg", "1.0.0"))

    pkg_dir = build_dir / "pkg-1.0.0"
    libs_dir = pkg_dir / CHUB_LIBS_DIR
    libs_dir.mkdir(parents=True)

    monkeypatch.setattr(packager, "get_wheel_package_dir", lambda *a, **k: pkg_dir)
    monkeypatch.setattr(packager, "validate_chub_structure", lambda *a, **k: actions.append("validate"))

    monkeypatch.setattr(packager.shutil, "copy2", lambda *a, **k: actions.append(("copy", a[0], a[1])))
    monkeypatch.setattr(packager, "download_wheel_deps", lambda *a, **k: actions.append("download"))
    monkeypatch.setattr(packager, "copy_post_install_scripts", lambda *a, **k: actions.append("post_install"))
    monkeypatch.setattr(packager, "copy_included_files", lambda *a, **k: actions.append("included"))
    monkeypatch.setattr(packager, "copy_runtime_files", lambda *a, **k: actions.append("runtime"))

    monkeypatch.setattr(
        packager,
        "create_chubconfig",
        lambda **kwargs: "---\nname: pkg\nversion: 1.0.0\nentrypoint: m:f\n\n"
    )

    def fake_create_chub_archive(build_dir, chub_path):
        return chub_path or build_dir / "pkg-1.0.0"

    monkeypatch.setattr(packager, "create_chub_archive", fake_create_chub_archive)

    out = packager.build_chub(wheel_path, chub_path=None, entrypoint="m:f")

    expected = build_dir / "pkg-1.0.0.chub"
    assert out == expected


def test_build_chub_propagates_validate_errors(monkeypatch, tmp_path):
    wheel_path = tmp_path / "pkg-1.0.0-py3-none-any.whl"
    wheel_path.write_text("fake")

    br = tmp_path / CHUB_BUILD_DIR
    br.mkdir()

    monkeypatch.setattr(packager, "verify_pip", lambda: None)
    monkeypatch.setattr(packager, "create_chub_build_dir_structure", lambda *a, **k: br)
    monkeypatch.setattr(packager, "get_wheel_metadata", lambda *a, **k: ("pkg", "1.0.0"))

    wpd = br / "pkg-1.0.0"
    wpd.mkdir(parents=True)
    (wpd / CHUB_LIBS_DIR).mkdir()

    monkeypatch.setattr(packager, "get_wheel_package_dir", lambda *a, **k: wpd)

    def boom(*a, **k):
        raise ValueError("bad validate")

    monkeypatch.setattr(packager, "validate_chub_structure", boom)

    with pytest.raises(ValueError):
        packager.build_chub(wheel_path)