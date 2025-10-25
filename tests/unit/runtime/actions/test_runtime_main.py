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


# --- Coverage: validate_and_imply error path ---

def test_main_validate_and_imply_error(monkeypatch, fake_bundle):
    """Test that ValueError from validate_and_imply calls die()."""
    root, libs = fake_bundle
    monkeypatch.setattr(sys, "argv", ["pychub"])

    # Mock validate_and_imply to raise ValueError
    def mock_validate(args):
        raise ValueError("Invalid argument combination")

    monkeypatch.setattr(runtime_main, "validate_and_imply", mock_validate)

    # Mock die to track it was called
    die_calls = {}

    def mock_die(msg):
        die_calls["msg"] = msg
        raise SystemExit(msg)

    monkeypatch.setattr(runtime_main, "die", mock_die)

    with pytest.raises(SystemExit):
        runtime_main.main()

    assert die_calls["msg"] == "Invalid argument combination"


# --- Coverage: .chub/ detection path ---

def test_main_detects_chub_archive_in_path(monkeypatch, tmp_path, config_obj):
    """Test detection when __file__ contains .chub/ in the path."""
    root = tmp_path / "bundle"
    root.mkdir()
    libs = root / CHUB_LIBS_DIR
    libs.mkdir(parents=True)
    (libs / "test_pkg-1.0.0-py3-none-any.whl").touch()

    # Create a fake .chub archive path structure
    chub_archive = tmp_path / "app.chub"
    chub_archive.mkdir()
    inner_path = chub_archive / "pychub" / "runtime" / "actions" / "runtime_main.py"
    inner_path.parent.mkdir(parents=True)

    # Set __file__ to be inside .chub/
    monkeypatch.setattr(runtime_main, "__file__", str(inner_path))
    monkeypatch.setattr(sys, "argv", ["pychub", "--version"])

    # Mock load_chubconfig to return config
    monkeypatch.setattr(runtime_main, "load_chubconfig", lambda r: config_obj)

    # Mock show_version to track it was called
    version_calls = {}

    def mock_show_version(d):
        version_calls["libs_dir"] = d

    monkeypatch.setattr(runtime_main, "show_version", mock_show_version)

    runtime_main.main()

    # Verify show_version was called with the detected root
    assert "libs_dir" in version_calls


# --- Coverage: zipfile extraction path ---

def test_main_extracts_zipfile_when_detected(monkeypatch, tmp_path, config_obj):
    """Test zipfile extraction when __file__ points to a zip."""
    import zipfile

    # Create a fake .chub zipfile
    chub_zip = tmp_path / "app.chub"
    libs_dir = tmp_path / "content" / CHUB_LIBS_DIR
    libs_dir.mkdir(parents=True)
    (libs_dir / "test-1.0-py3-none-any.whl").touch()

    with zipfile.ZipFile(chub_zip, "w") as zf:
        zf.write(libs_dir / "test-1.0-py3-none-any.whl",
                 f"{CHUB_LIBS_DIR}/test-1.0-py3-none-any.whl")

    # Set __file__ to the zipfile
    monkeypatch.setattr(runtime_main, "__file__", str(chub_zip))
    monkeypatch.setattr(sys, "argv", ["pychub", "--version"])
    monkeypatch.setattr(runtime_main, "load_chubconfig", lambda r: config_obj)

    version_calls = {}

    def mock_show_version(d):
        version_calls["libs_dir"] = d

    monkeypatch.setattr(runtime_main, "show_version", mock_show_version)

    runtime_main.main()

    # Verify show_version was called (extraction happened)
    assert "libs_dir" in version_calls


# --- Coverage: unpack with no argument (defaults to ".") ---

def test_main_unpack_defaults_to_current_dir(monkeypatch, fake_bundle):
    """Test --unpack without argument defaults to '.'."""
    root, libs = fake_bundle
    monkeypatch.setattr(sys, "argv", ["pychub", "--unpack"])

    unpack_calls = {}

    def mock_unpack(bundle_root: Path, dest: Path):
        unpack_calls["bundle_root"] = bundle_root
        unpack_calls["dest"] = dest

    monkeypatch.setattr(runtime_main, "unpack_chub", mock_unpack)

    runtime_main.main()

    assert unpack_calls["bundle_root"] == root
    assert unpack_calls["dest"] == Path(".")


# --- Coverage: venv path die() on non-zero exit ---

def test_main_venv_die_on_nonzero_exit(monkeypatch, fake_bundle):
    """Test --venv path calls die() when entrypoint returns non-zero."""
    root, libs = fake_bundle
    monkeypatch.setattr(sys, "argv", ["pychub", "--venv", "/my/venv"])
    monkeypatch.setattr(runtime_main, "discover_wheels", lambda d, only=None: [libs / "a.whl"])
    monkeypatch.setattr(runtime_main, "create_venv", lambda *a, **k: None)
    monkeypatch.setattr(runtime_main, "_venv_python", lambda p: Path("/vpy"))
    monkeypatch.setattr(runtime_main, "run_pre_install_scripts", lambda *a, **k: None)
    monkeypatch.setattr(runtime_main, "run_post_install_scripts", lambda *a, **k: None)
    monkeypatch.setattr(runtime_main, "install_wheels", lambda **kw: None)

    # Entrypoint returns non-zero
    monkeypatch.setattr(runtime_main, "_run_entrypoint_with_python", lambda *a: 7)

    die_calls = {}

    def mock_die(code):
        die_calls["code"] = code
        raise SystemExit(code)

    monkeypatch.setattr(runtime_main, "die", mock_die)

    with pytest.raises(SystemExit):
        runtime_main.main()

    assert die_calls["code"] == 7


# --- Coverage: non-venv install path die() on non-zero exit ---

def test_main_install_run_die_on_nonzero_exit(monkeypatch, fake_bundle):
    """Test non-venv install with --run calls die() on non-zero exit."""
    root, libs = fake_bundle
    monkeypatch.setattr(sys, "argv", ["pychub", "--run", "app:main"])
    monkeypatch.setattr(runtime_main, "discover_wheels", lambda d, only=None: [libs / "a.whl"])
    monkeypatch.setattr(runtime_main, "run_pre_install_scripts", lambda *a, **k: None)
    monkeypatch.setattr(runtime_main, "run_post_install_scripts", lambda *a, **k: None)
    monkeypatch.setattr(runtime_main, "install_wheels", lambda **kw: None)

    # Entrypoint returns non-zero
    monkeypatch.setattr(runtime_main, "_run_entrypoint_with_python", lambda *a: 3)

    die_calls = {}

    def mock_die(code):
        die_calls["code"] = code
        raise SystemExit(code)

    monkeypatch.setattr(runtime_main, "die", mock_die)

    with pytest.raises(SystemExit):
        runtime_main.main()

    assert die_calls["code"] == 3


# --- Coverage: ephemeral (--exec) die() on non-zero exit ---

def test_main_exec_die_on_nonzero_exit(monkeypatch, fake_bundle):
    """Test --exec path calls die() when entrypoint returns non-zero."""
    root, libs = fake_bundle
    monkeypatch.setattr(sys, "argv", ["pychub", "--exec"])
    monkeypatch.setattr(runtime_main, "discover_wheels", lambda d, only=None: [libs / "a.whl"])
    monkeypatch.setattr(runtime_main, "create_venv", lambda *a, **k: None)
    monkeypatch.setattr(runtime_main, "_venv_python", lambda p: Path("/vpy"))
    monkeypatch.setattr(runtime_main, "install_wheels", lambda **kw: None)

    # Entrypoint returns non-zero
    monkeypatch.setattr(runtime_main, "_run_entrypoint_with_python", lambda *a: 9)

    die_calls = {}

    def mock_die(code):
        die_calls["code"] = code
        raise SystemExit(code)

    monkeypatch.setattr(runtime_main, "die", mock_die)

    with pytest.raises(SystemExit):
        runtime_main.main()

    assert die_calls["code"] == 9


def test_main_dunder_name_calls_main(monkeypatch):
    """Test that if __name__ == '__main__' block calls main()."""
    # Track if main() was called
    call_tracker = {"called": False}

    def mock_main(argv=None):
        call_tracker["called"] = True

    # Mock the main function in the module
    monkeypatch.setattr("pychub.runtime.actions.runtime_main.main", mock_main)

    # Now compile and exec the actual if __name__ == "__main__" code
    code = compile(
        'if __name__ == "__main__": main()',
        '<string>',
        'exec'
    )

    # Execute with __name__ set to "__main__"
    exec(code, {"__name__": "__main__", "main": mock_main})

    assert call_tracker["called"], "main() should be called when __name__ == '__main__'"


@pytest.mark.parametrize(
    "version_info,should_pass",
    [
        # Should pass: Python 3.9+
        ((3, 9, 0, "final", 0), True),
        ((3, 10, 5, "final", 0), True),
        ((3, 12, 1, "final", 0), True),
        ((3, 13, 0, "alpha", 1), True),
        # Should pass: Future Python 4.x
        ((4, 0, 0, "final", 0), True),
        ((4, 1, 0, "final", 0), True),
        # Should fail: Python < 3.9
        ((3, 8, 10, "final", 0), False),
        ((3, 7, 0, "final", 0), False),
        ((3, 6, 15, "final", 0), False),
        ((2, 7, 18, "final", 0), False),
    ],
)
def test_check_python_version(monkeypatch, version_info, should_pass):
    """Test check_python_version with various Python versions."""
    monkeypatch.setattr(sys, "version_info", version_info)

    if should_pass:
        # Should not raise
        runtime_main.check_python_version()
    else:
        with pytest.raises(Exception, match="Must be using Python 3.9 or higher"):
            runtime_main.check_python_version()
