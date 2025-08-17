import sys
from pathlib import Path
import pytest

from pychubby.runtime.actions import runtime_main


@pytest.fixture
def fake_bundle(tmp_path, monkeypatch):
    root = tmp_path / "bundle"
    libs = root / "libs"
    libs.mkdir(parents=True)

    # Fake __file__ to point to this directory
    monkeypatch.setattr(runtime_main, "__file__", str(root / "main.py"))
    return root, libs


def test_main_prints_version(monkeypatch, fake_bundle):
    root, libs = fake_bundle

    monkeypatch.setattr(sys, "argv", ["pychubby", "--version"])
    called = {}
    monkeypatch.setattr(runtime_main, "show_version", lambda d: called.setdefault("version", d))

    runtime_main.main()
    assert called["version"] == libs


def test_main_lists_wheels(monkeypatch, fake_bundle):
    root, libs = fake_bundle

    monkeypatch.setattr(sys, "argv", ["pychubby", "--list"])
    called = {}
    monkeypatch.setattr(runtime_main, "list_wheels", lambda d: called.setdefault("list", d))

    runtime_main.main()
    assert called["list"] == libs


def test_main_unpacks(monkeypatch, fake_bundle):
    root, libs = fake_bundle
    monkeypatch.setattr(sys, "argv", ["pychubby", "--unpack", "/tmp/foo"])

    unpacked = {}
    monkeypatch.setattr(runtime_main, "unpack_wheels", lambda lib, dest: unpacked.setdefault("args", (lib, dest)))

    runtime_main.main()
    assert unpacked["args"][0] == libs
    assert Path("/tmp/foo") == unpacked["args"][1]


def test_main_errors_when_no_wheels(monkeypatch, fake_bundle):
    root, libs = fake_bundle
    monkeypatch.setattr(sys, "argv", ["pychubby"])
    monkeypatch.setattr(runtime_main, "load_chubconfig", lambda b: {})
    monkeypatch.setattr(runtime_main, "discover_wheels", lambda d, only=None: [])
    monkeypatch.setattr(runtime_main, "die", lambda msg: (_ for _ in ()).throw(SystemExit(msg)))

    with pytest.raises(SystemExit) as exc:
        runtime_main.main()
    assert "no wheels found" in str(exc.value)


def test_main_exec_skips_scripts(monkeypatch, fake_bundle):
    root, libs = fake_bundle
    monkeypatch.setattr(sys, "argv", ["pychubby", "--exec"])
    monkeypatch.setattr(runtime_main, "load_chubconfig", lambda b: {})
    monkeypatch.setattr(runtime_main, "discover_wheels", lambda d, only=None: [libs / "a.whl"])
    monkeypatch.setattr(runtime_main, "install_wheels", lambda **kw: kw.setdefault("installed", True))
    monkeypatch.setattr(runtime_main, "maybe_run_entrypoint", lambda *a: a)

    ran = {}
    monkeypatch.setattr(runtime_main, "run_post_install_scripts", lambda *a: ran.setdefault("scripts", True))

    runtime_main.main()
    assert "scripts" not in ran  # should skip due to --exec


def test_main_handles_venv(monkeypatch, fake_bundle):
    root, libs = fake_bundle
    monkeypatch.setattr(sys, "argv", ["pychubby", "--venv", "/my/venv"])
    monkeypatch.setattr(runtime_main, "load_chubconfig", lambda b: {})
    monkeypatch.setattr(runtime_main, "discover_wheels", lambda d, only=None: [libs / "a.whl"])

    called = {}
    monkeypatch.setattr(runtime_main, "create_venv", lambda path, wheels, **opts: called.setdefault("venv", (path, wheels, opts)))

    runtime_main.main()
    assert called["venv"][0] == Path("/my/venv")
    assert called["venv"][1] == [libs / "a.whl"]


def test_main_normal_install(monkeypatch, fake_bundle):
    root, libs = fake_bundle
    monkeypatch.setattr(sys, "argv", ["pychubby"])
    monkeypatch.setattr(runtime_main, "load_chubconfig", lambda b: {"post_install_scripts": ["post.sh"], "baked_entrypoint": "entry"})
    monkeypatch.setattr(runtime_main, "discover_wheels", lambda d, only=None: [libs / "a.whl"])

    flow = {}
    monkeypatch.setattr(runtime_main, "install_wheels", lambda **kw: flow.setdefault("installed", True))
    monkeypatch.setattr(runtime_main, "run_post_install_scripts", lambda *a: flow.setdefault("scripts", True))
    monkeypatch.setattr(runtime_main, "maybe_run_entrypoint", lambda *a: flow.setdefault("ran", a))

    runtime_main.main()
    assert flow == {"installed": True, "scripts": True}
