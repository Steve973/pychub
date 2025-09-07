import sys
import argparse
from types import SimpleNamespace
from pathlib import Path
import pytest

from pychub.runtime.actions import runtime_main
from pychub.runtime.constants import CHUB_LIBS_DIR


# --- Helpers / fixtures ---

@pytest.fixture(autouse=True)
def fake_parser(monkeypatch):
    """Patch CLI parser to a minimal, test-friendly one matching flags used."""
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--version", action="store_true")
    parser.add_argument("--list", action="store_true")
    parser.add_argument("--unpack", nargs="?", const=".")
    parser.add_argument("--venv")
    parser.add_argument("--exec", dest="exec", action="store_true")
    parser.add_argument("--run", nargs="?", const="")
    parser.add_argument("--only")
    parser.add_argument("--quiet", action="store_true")
    parser.add_argument("--verbose", action="store_true")
    parser.add_argument("--dry_run", action="store_true")
    parser.add_argument("--no_deps", action="store_true")
    parser.add_argument("--no-scripts", dest="no_scripts", action="store_true")
    parser.add_argument("--no-pre-scripts", dest="no_pre_scripts", action="store_true")
    parser.add_argument("--no-post-scripts", dest="no_post_scripts", action="store_true")

    monkeypatch.setattr(runtime_main, "build_parser", lambda: parser)


@pytest.fixture
def config_obj():
    return SimpleNamespace(entrypoint="test_pkg.greet:main", scripts=SimpleNamespace(pre=[], post=[]))


@pytest.fixture
def fake_bundle(tmp_path, monkeypatch, config_obj):
    root = tmp_path / "bundle"
    root.mkdir()
    libs = (root / CHUB_LIBS_DIR)
    libs.mkdir(parents=True)
    (libs / "test_pkg-1.0.0-py3-none-any.whl").touch()

    # runtime resolves bundle_root as parent of __file__
    monkeypatch.setattr(runtime_main, "__file__", str(root / "main.py"))

    # stabilize config
    monkeypatch.setattr(runtime_main, "load_chubconfig", lambda r: config_obj)

    return root, libs


# --- Simple info actions ---

def test_main_prints_version(monkeypatch, fake_bundle):
    root, libs = fake_bundle
    monkeypatch.setattr(sys, "argv", ["pychub", "--version"])

    called = {}
    monkeypatch.setattr(runtime_main, "show_version", lambda d: called.setdefault("version", d))

    runtime_main.main()
    assert called["version"] == libs


def test_main_lists_wheels(monkeypatch, fake_bundle):
    root, libs = fake_bundle
    monkeypatch.setattr(sys, "argv", ["pychub", "--list"])

    called = {}
    monkeypatch.setattr(runtime_main, "list_wheels", lambda d, **kw: called.setdefault("list", (d, kw)))

    runtime_main.main()

    arg, kw = called["list"]
    assert arg == root
    # optional: prove kwargs are forwarded (adjust if your defaults differ)
    assert kw.get("quiet") is False
    assert kw.get("verbose") is False


def test_main_unpacks(monkeypatch, fake_bundle):
    root, libs = fake_bundle
    monkeypatch.setattr(sys, "argv", ["pychub", "--unpack", "/tmp/foo"])

    unpacked = {}
    monkeypatch.setattr(runtime_main, "unpack_chub", lambda bundle, dest: unpacked.setdefault("args", (bundle, dest)))

    runtime_main.main()
    assert unpacked["args"] == (root, Path("/tmp/foo"))


# --- Discover / error path ---

def test_main_errors_when_no_wheels(monkeypatch, fake_bundle):
    root, libs = fake_bundle
    monkeypatch.setattr(sys, "argv", ["pychub"])
    monkeypatch.setattr(runtime_main, "discover_wheels", lambda d, only=None: [])
    monkeypatch.setattr(runtime_main, "die", lambda msg: (_ for _ in ()).throw(SystemExit(msg)))

    with pytest.raises(SystemExit) as exc:
        runtime_main.main()
    assert "no wheels found in bundle" in str(exc.value)


# --- Exec path (ephemeral venv) ---

def test_main_exec_skips_scripts_and_runs_entrypoint(monkeypatch, fake_bundle, config_obj):
    root, libs = fake_bundle
    monkeypatch.setattr(sys, "argv", ["pychub", "--exec"])
    monkeypatch.setattr(runtime_main, "discover_wheels", lambda d, only=None: [libs / "a.whl"])

    # ensure scripts are NOT called
    monkeypatch.setattr(
        runtime_main,
        "run_post_install_scripts",
        lambda *a, **k: (_ for _ in ()).throw(AssertionError("post should not run")),
    )
    monkeypatch.setattr(
        runtime_main,
        "run_pre_install_scripts",
        lambda *a, **k: (_ for _ in ()).throw(AssertionError("pre should not run")),
    )

    create_calls = {}
    monkeypatch.setattr(
        runtime_main,
        "create_venv",
        lambda path, wheels, **opts: create_calls.setdefault("venv", (path, list(wheels))),
    )

    monkeypatch.setattr(runtime_main, "_venv_python", lambda p: Path("/vpy"))

    install_calls = {}
    def fake_install(**kw):
        install_calls.update(kw)
    monkeypatch.setattr(runtime_main, "install_wheels", fake_install)

    run_calls = {}
    def _fake_run(py, dry_run, target, args):
        run_calls.setdefault("call", (py, dry_run, target, list(args)))
        return 0
    monkeypatch.setattr(runtime_main, "_run_entrypoint_with_python", _fake_run)

    # success path: main() returns, does not sys.exit
    runtime_main.main()

    assert install_calls["python"] == str(Path("/vpy"))
    assert run_calls["call"][0] == Path("/vpy")
    assert run_calls["call"][2] == config_obj.entrypoint


def test_main_exec_forwards_passthru_after_dashdash(monkeypatch, fake_bundle):
    root, libs = fake_bundle
    monkeypatch.setattr(sys, "argv", ["pychub", "--exec", "--", "--alpha", "1"])
    monkeypatch.setattr(runtime_main, "discover_wheels", lambda d, only=None: [libs / "a.whl"])
    monkeypatch.setattr(runtime_main, "create_venv", lambda *a, **k: None)
    monkeypatch.setattr(runtime_main, "_venv_python", lambda p: Path("/vpy"))
    monkeypatch.setattr(runtime_main, "install_wheels", lambda **kw: None)

    captured = {}
    def _fake_run_args(py, dry_run, target, args):
        captured.setdefault("args", list(args))
        return 0
    monkeypatch.setattr(runtime_main, "_run_entrypoint_with_python", _fake_run_args)

    # success path: main() returns
    runtime_main.main()
    assert captured["args"] == ["--alpha", "1"]


# --- Venv persistent install path ---

def test_main_handles_venv_with_pre_and_post(monkeypatch, fake_bundle):
    root, libs = fake_bundle
    monkeypatch.setattr(sys, "argv", ["pychub", "--venv", "/my/venv"])
    monkeypatch.setattr(runtime_main, "discover_wheels", lambda d, only=None: [libs / "a.whl"])
    monkeypatch.setattr(runtime_main, "_run_entrypoint_with_python", lambda *a: 0)

    pre, post, inst = {}, {}, {}
    monkeypatch.setattr(runtime_main, "create_venv", lambda path, wheels, **opts: None)
    monkeypatch.setattr(runtime_main, "_venv_python", lambda p: Path("/vpy"))
    monkeypatch.setattr(runtime_main, "run_pre_install_scripts", lambda root, dry_run, items: pre.setdefault("ok", (root, list(items))))
    monkeypatch.setattr(runtime_main, "run_post_install_scripts", lambda root, dry_run, items: post.setdefault("ok", (root, list(items))))
    monkeypatch.setattr(runtime_main, "install_wheels", lambda **kw: inst.setdefault("kw", kw))

    runtime_main.main()

    assert pre["ok"][0] == root and post["ok"][0] == root
    assert inst["kw"]["python"] == str(Path("/vpy"))


def test_main_venv_no_pre_scripts_skips_install_but_may_run_post(monkeypatch, fake_bundle):
    root, libs = fake_bundle
    monkeypatch.setattr(sys, "argv", ["pychub", "--venv", "/venv", "--no-pre-scripts"])
    monkeypatch.setattr(runtime_main, "discover_wheels", lambda d, only=None: [libs / "a.whl"])
    monkeypatch.setattr(runtime_main, "_run_entrypoint_with_python", lambda *a: 0)

    calls = {"pre": 0, "post": 0, "install": 0}
    monkeypatch.setattr(runtime_main, "create_venv", lambda *a, **k: None)
    monkeypatch.setattr(runtime_main, "_venv_python", lambda p: Path("/vpy"))
    monkeypatch.setattr(runtime_main, "run_pre_install_scripts", lambda *a, **k: (_ for _ in ()).throw(AssertionError("pre should be skipped")))
    monkeypatch.setattr(runtime_main, "run_post_install_scripts", lambda *a, **k: calls.update(post=calls["post"] + 1))
    monkeypatch.setattr(runtime_main, "install_wheels", lambda **kw: calls.update(install=calls["install"] + 1))

    runtime_main.main()

    assert calls["install"] == 0  # per current implementation
    assert calls["post"] == 1


# --- Non-venv install + optional run ---

def test_main_normal_install_runs_pre_and_post(monkeypatch, fake_bundle):
    root, libs = fake_bundle
    monkeypatch.setattr(sys, "argv", ["pychub"])
    monkeypatch.setattr(runtime_main, "discover_wheels", lambda d, only=None: [libs / "a.whl"])

    flow = {"pre": 0, "post": 0, "install": 0}
    monkeypatch.setattr(runtime_main, "run_pre_install_scripts", lambda *a, **k: flow.update(pre=flow["pre"] + 1))
    monkeypatch.setattr(runtime_main, "run_post_install_scripts", lambda *a, **k: flow.update(post=flow["post"] + 1))
    monkeypatch.setattr(runtime_main, "install_wheels", lambda **kw: flow.update(install=flow["install"] + 1))

    runtime_main.main()
    assert flow == {"pre": 1, "install": 1, "post": 1}


def test_main_run_baked_entrypoint_when_run_flag_no_arg(monkeypatch, fake_bundle, config_obj):
    root, libs = fake_bundle
    monkeypatch.setattr(sys, "argv", ["pychub", "--run"])
    monkeypatch.setattr(runtime_main, "discover_wheels", lambda d, only=None: [libs / "a.whl"])

    # bypass pre/post/install quickly
    monkeypatch.setattr(runtime_main, "run_pre_install_scripts", lambda *a, **k: None)
    monkeypatch.setattr(runtime_main, "run_post_install_scripts", lambda *a, **k: None)
    monkeypatch.setattr(runtime_main, "install_wheels", lambda **kw: None)

    captured = {}
    def _fake_run_baked(py, dry_run, target, args):
        captured.setdefault("v", (py, target, args))
        return 0
    monkeypatch.setattr(runtime_main, "_run_entrypoint_with_python", _fake_run_baked)

    # success path: main() returns
    runtime_main.main()

    py, target, args = captured["v"]
    assert py == Path(sys.executable)
    assert target == config_obj.entrypoint  # baked wins when --run has no value


def test_main_run_exit_nonzero_exits(monkeypatch, fake_bundle):
    root, libs = fake_bundle
    monkeypatch.setattr(sys, "argv", ["pychub", "--run", "demo:main"])
    monkeypatch.setattr(runtime_main, "discover_wheels", lambda d, only=None: [libs / "a.whl"])

    # silence install & scripts
    monkeypatch.setattr(runtime_main, "run_pre_install_scripts", lambda *a, **k: None)
    monkeypatch.setattr(runtime_main, "run_post_install_scripts", lambda *a, **k: None)
    monkeypatch.setattr(runtime_main, "install_wheels", lambda **kw: None)

    # entrypoint returns non-zero
    monkeypatch.setattr(runtime_main, "_run_entrypoint_with_python", lambda *a: 5)

    exits = {}

    def _fake_exit(code):
        exits["code"] = code
        raise SystemExit(code)

    monkeypatch.setattr(runtime_main.sys, "exit", _fake_exit)

    with pytest.raises(SystemExit):
        runtime_main.main()
    assert exits["code"] == 5
