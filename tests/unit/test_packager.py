import subprocess
import sys
import types
import zipfile

import pytest
import yaml

from pychubby.package import packager
from pychubby.package.constants import (
    CHUB_BUILD_DIR,
    CHUB_LIBS_DIR,
    CHUB_SCRIPTS_DIR,
    CHUB_POST_INSTALL_SCRIPTS_DIR,
    CHUB_PRE_INSTALL_SCRIPTS_DIR,
    CHUBCONFIG_FILENAME,
    RUNTIME_DIR,
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
    src1 = tmp_path / "f1.txt"; src1.write_text("1")
    src2 = tmp_path / "f2.txt"; src2.write_text("2")
    packager.copy_included_files(base, [str(src1), f"{src2}::data/inside.txt"])
    assert (base / "f1.txt").read_text() == "1"
    assert (base / "data" / "inside.txt").read_text() == "2"

def test_copy_included_files_missing_raises(tmp_path):
    base = tmp_path / "base"
    base.mkdir()
    with pytest.raises(FileNotFoundError):
        packager.copy_included_files(base, ["nope.txt"])

def test_copy_included_files_prevent_directory_traversal(tmp_path):
    base = tmp_path / "base"; base.mkdir()
    src = tmp_path / "x.txt"; src.write_text("x")
    with pytest.raises(ValueError) as e:
        packager.copy_included_files(base, [f"{src}::../outside.txt"])
    assert "escapes chub build directory" in str(e.value)

def test_copy_install_scripts_happy(tmp_path):
    base = tmp_path / "build" / CHUB_SCRIPTS_DIR
    (base / CHUB_POST_INSTALL_SCRIPTS_DIR).mkdir(parents=True)
    s = tmp_path / "foo.sh"; s.write_text("echo hi")
    packager.copy_install_scripts(
        base,
        [(s, "00_post_foo.sh")],
        CHUB_POST_INSTALL_SCRIPTS_DIR,
    )
    assert (base / CHUB_POST_INSTALL_SCRIPTS_DIR / "00_post_foo.sh").is_file()

def test_download_wheel_deps_builds_cmd_and_handles_errors(monkeypatch, tmp_path):
    calls = []
    def fake_run(cmd, text, capture_output):
        calls.append(cmd)
        return types.SimpleNamespace(returncode=0, stdout="ok", stderr="")
    monkeypatch.setattr(subprocess, "run", fake_run)
    whl = tmp_path / "pkg-1.0.0-py3-none-any.whl"; whl.write_text("fake")
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
    whl = tmp_path / "pkg-1.0.0-py3-none-any.whl"; whl.write_text("fake")
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
    bdir = tmp_path / CHUB_BUILD_DIR; bdir.mkdir()
    (bdir / CHUBCONFIG_FILENAME).write_text("---\n")
    # libs/scripts empty → ok
    packager.validate_chub_structure(bdir, [], [], [])
    # missing .chubconfig → error
    bdir2 = tmp_path / "other"; bdir2.mkdir()
    with pytest.raises(FileNotFoundError):
        packager.validate_chub_structure(bdir2, [], [], [])
    # non-empty libs → error
    (bdir / CHUB_LIBS_DIR).mkdir(parents=True)
    (bdir / CHUB_LIBS_DIR / "junk.txt").write_text("x")
    with pytest.raises(FileExistsError):
        packager.validate_chub_structure(bdir, [], [], [])

def test_build_chub_happy_path(monkeypatch, tmp_path):
    # Fake wheel file
    wheel_path = tmp_path / "pkg-1.0.0-py3-none-any.whl"; wheel_path.write_text("fake")
    # Spy actions
    actions = []
    monkeypatch.setattr(packager, "verify_pip", lambda: actions.append("verify_pip"))
    # Let create_chub_build_dir create structure in ./out
    outdir = tmp_path / "out"; outdir.mkdir()
    chub_path = outdir / "pkg-1.0.0.chub"
    # Simplify metadata reading
    monkeypatch.setattr(packager, "get_wheel_metadata", lambda wp: ("pkg", "1.0.0"))
    # Avoid touching a real runtime tree
    monkeypatch.setattr(packager, "copy_runtime_files", lambda *a, **k: actions.append("runtime"))
    # No deps; just echo download call
    monkeypatch.setattr(packager, "download_wheel_deps", lambda *a, **k: [])
    # Build
    out = packager.build_chub(
        wheel_paths=[wheel_path],
        chub_path=chub_path,
        entrypoint="m:f",
        post_install_scripts=[(wheel_path, "00_post.sh")],
        pre_install_scripts=[(wheel_path, "00_pre.sh")],
        included_files=[],
        metadata={"main_wheel": wheel_path.name},
    )
    assert out == chub_path
    # Verify contents on disk (flat)
    with zipfile.ZipFile(out) as z:
        names = set(z.namelist())
    assert f"{CHUB_LIBS_DIR}/{wheel_path.name}" in names
    assert f"{CHUB_SCRIPTS_DIR}/{CHUB_POST_INSTALL_SCRIPTS_DIR}/00_post.sh" in names
    assert f"{CHUB_SCRIPTS_DIR}/{CHUB_PRE_INSTALL_SCRIPTS_DIR}/00_pre.sh" in names
    assert CHUBCONFIG_FILENAME in names
    # Verify .chubconfig shape
    tmp_extract = tmp_path / "x"; tmp_extract.mkdir()
    with zipfile.ZipFile(out) as z:
        z.extract(CHUBCONFIG_FILENAME, tmp_extract)
    cfg = (tmp_extract / CHUBCONFIG_FILENAME).read_text()
    data = yaml.safe_load(cfg)
    assert data["name"] == "pkg"
    assert data["version"] == "1.0.0"
    assert data["entrypoint"] == "m:f"
    assert data["scripts"]["post"] == ["00_post.sh"]
    assert data["scripts"]["pre"] == ["00_pre.sh"]
    assert list(data["wheels"].keys()) == [wheel_path.name]
