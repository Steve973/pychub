import sys
from pathlib import Path
import pytest

from pychubby.runtime.actions import runtime_main
from pychubby.runtime.constants import DEFAULT_LIBS_DIR, CHUBCONFIG_FILENAME

import yaml

@pytest.fixture
def fake_bundle(tmp_path, monkeypatch):
    package_name = "test_pkg"
    version = "1.0.0"
    module_dir = f'{package_name}-{version}'
    root = tmp_path / "bundle"
    libs = root / module_dir / DEFAULT_LIBS_DIR
    libs.mkdir(parents=True)

    # Add a fake __file__ so runtime thinks it's executing from this path
    monkeypatch.setattr(runtime_main, "__file__", str(root / "main.py"))

    # Add dummy .chubconfig
    chubconfig_data = {
        "name": f"{package_name}",
        "version": f"{version}",
        "entrypoint": "test_pkg.greet:main",
        "post_install_scripts": [],
        "includes": [],
        "metadata": {},
        "baked_entrypoint": "entry"
    }
    (root / CHUBCONFIG_FILENAME).write_text(
        yaml.dump(chubconfig_data, sort_keys=False), encoding="utf-8"
    )

    # Add a fake wheel
    (libs / "test_pkg-1.0.0-py3-none-any.whl").touch()

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
    monkeypatch.setattr(runtime_main, "discover_wheels", lambda d, only=None: [])
    monkeypatch.setattr(runtime_main, "die", lambda msg: (_ for _ in ()).throw(SystemExit(msg)))

    with pytest.raises(SystemExit) as exc:
        runtime_main.main()
    assert "no wheels found" in str(exc.value)


def test_main_exec_skips_scripts(monkeypatch, fake_bundle):
    root, libs = fake_bundle
    monkeypatch.setattr(sys, "argv", ["pychubby", "--exec"])
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
    monkeypatch.setattr(runtime_main, "discover_wheels", lambda d, only=None: [libs / "a.whl"])

    called = {}
    monkeypatch.setattr(runtime_main, "create_venv", lambda path, wheels, **opts: called.setdefault("venv", (path, wheels, opts)))

    runtime_main.main()
    assert called["venv"][0] == Path("/my/venv")
    assert called["venv"][1] == [libs / "a.whl"]


def test_main_normal_install(monkeypatch, fake_bundle):
    root, libs = fake_bundle
    monkeypatch.setattr(sys, "argv", ["pychubby"])
    monkeypatch.setattr(runtime_main, "discover_wheels", lambda d, only=None: [libs / "a.whl"])

    flow = {}
    monkeypatch.setattr(runtime_main, "install_wheels", lambda **kw: flow.setdefault("installed", True))
    monkeypatch.setattr(runtime_main, "run_post_install_scripts", lambda *a: flow.setdefault("scripts", True))
    monkeypatch.setattr(runtime_main, "maybe_run_entrypoint", lambda *a: flow.setdefault("ran", a))

    runtime_main.main()
    assert flow == {"installed": True, "scripts": True}
