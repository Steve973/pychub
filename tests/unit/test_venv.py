import os

import pytest

from pychub.runtime.actions import venv as venv_mod
from tests.utils import CoercingPath


# --- Dry run ---

def test_create_venv_dry_run_prints_files(tmp_path, capsys):
    wheels = [tmp_path / "a.whl", tmp_path / "b.whl"]
    for w in wheels:
        w.write_text("fake")

    venv_mod.create_venv(tmp_path / "venv", wheels, dry_run=True)

    out = capsys.readouterr().out
    assert "[dry-run] would create venv at" in out
    assert "[dry-run] would install wheels:" in out
    assert "a.whl" in out and "b.whl" in out


# --- Happy path installs ---

def test_create_venv_happy_path_builds_and_installs(monkeypatch, tmp_path):
    created = {}

    class DummyBuilder:
        def create(self, path):
            created["path"] = path

    monkeypatch.setattr(venv_mod.venv, "EnvBuilder", lambda with_pip: DummyBuilder())

    wheels = [tmp_path / "only.whl"]
    wheels[0].write_text("fake")

    called = {}

    class DummyResult:
        def __init__(self, returncode=0, stderr=""):
            self.returncode = returncode
            self.stderr = stderr

    def fake_run(cmd, capture_output, text):
        called["cmd"] = cmd
        called["capture_output"] = capture_output
        called["text"] = text
        return DummyResult(0, "")

    monkeypatch.setattr(venv_mod.subprocess, "run", fake_run)

    venv_path = tmp_path / "venv"
    venv_mod.create_venv(venv_path, wheels)

    assert created["path"] == venv_path
    bin_dir = "Scripts" if os.name == "nt" else "bin"
    pip_path = venv_path / bin_dir / "pip"
    cmd = called["cmd"]
    assert str(pip_path) == cmd[0]
    assert cmd[1] == "install"
    assert cmd[-1] == str(wheels[0])
    assert called["capture_output"] is True  # default (not verbose)


# --- Flag behavior ---

def test_create_venv_quiet_and_verbose_flags(monkeypatch, tmp_path):
    monkeypatch.setattr(venv_mod.venv, "EnvBuilder", lambda with_pip: type("B", (), {"create": lambda self, p: None})())
    wheel = tmp_path / "a.whl"
    wheel.write_text("fake")

    results = []

    def fake_run(cmd, capture_output, text):
        results.append((cmd, capture_output))
        return type("R", (), {"returncode": 0, "stderr": ""})()

    monkeypatch.setattr(venv_mod.subprocess, "run", fake_run)

    venv_mod.create_venv(tmp_path / "venv1", [wheel], quiet=True)
    venv_mod.create_venv(tmp_path / "venv2", [wheel], verbose=True)
    venv_mod.create_venv(tmp_path / "venv3", [wheel], quiet=True, verbose=True)  # quiet wins

    (quiet_cmd, quiet_cap), (verb_cmd, verb_cap), (quiet2_cmd, quiet2_cap) = results

    assert "-q" in quiet_cmd and quiet_cap is True
    assert "-v" in verb_cmd and verb_cap is False
    assert "-q" in quiet2_cmd and "-v" not in quiet2_cmd and quiet2_cap is True


# --- Failure path ---

def test_create_venv_install_failure_exits_with_code(monkeypatch, tmp_path, capsys):
    monkeypatch.setattr(venv_mod.venv, "EnvBuilder", lambda with_pip: type("B", (), {"create": lambda self, p: None})())

    wheel = tmp_path / "bad.whl"
    wheel.write_text("fake")

    class DummyResult:
        def __init__(self):
            self.returncode = 42
            self.stderr = "pip failed"

    monkeypatch.setattr(venv_mod.subprocess, "run", lambda *a, **k: DummyResult())

    exit_code = {}

    def fake_exit(code):
        exit_code["code"] = code
        raise SystemExit(code)

    monkeypatch.setattr(venv_mod.sys, "exit", fake_exit)

    with pytest.raises(SystemExit):
        venv_mod.create_venv(tmp_path / "venv", [wheel])

    assert "pip failed" in capsys.readouterr().err
    assert exit_code["code"] == 42


def test_create_venv_failure_with_none_stderr_writes_nothing(monkeypatch, tmp_path, capsys):
    monkeypatch.setattr(venv_mod.venv, "EnvBuilder", lambda with_pip: type("B", (), {"create": lambda self, p: None})())

    wheel = tmp_path / "bad.whl"
    wheel.write_text("fake")

    class DummyResult:
        def __init__(self):
            self.returncode = 3
            self.stderr = None

    monkeypatch.setattr(venv_mod.subprocess, "run", lambda *a, **k: DummyResult())
    monkeypatch.setattr(venv_mod.sys, "exit", lambda code: (_ for _ in ()).throw(SystemExit(code)))

    with pytest.raises(SystemExit):
        venv_mod.create_venv(tmp_path / "venv", [wheel])

    assert capsys.readouterr().err == ""


# --- Success output ---

def test_create_venv_success_messages_posix(monkeypatch, tmp_path, capsys):
    # Ensure posix branch
    monkeypatch.setattr(venv_mod.os, "name", "posix", raising=False)
    monkeypatch.setattr(venv_mod.venv, "EnvBuilder", lambda with_pip: type("B", (), {"create": lambda self, p: None})())
    wheel = tmp_path / "a.whl"
    wheel.write_text("x")

    monkeypatch.setattr(venv_mod.subprocess, "run", lambda *a, **k: type("R", (), {"returncode": 0, "stderr": ""})())

    path = tmp_path / "venv"
    venv_mod.create_venv(path, [wheel])

    out = capsys.readouterr().out
    assert f"Created virtualenv at {path}" in out
    assert f"Use it with: source {path / 'bin' / 'activate'}" in out


def test_create_venv_success_messages_windows(monkeypatch, tmp_path, capsys):
    # Windows branch uses Scripts dir
    monkeypatch.setattr(venv_mod.os, "name", "nt", raising=False)
    monkeypatch.setattr(venv_mod, "Path", CoercingPath)
    monkeypatch.setattr(venv_mod.venv, "EnvBuilder", lambda with_pip: type("B", (), {"create": lambda self, p: None})())

    wheel = tmp_path / "a.whl"
    wheel.write_text("x")

    def fake_run(cmd, **kwargs):
        # Ensure pip path points to Scripts/pip
        assert CoercingPath(cmd[0]).parts[-2] == "Scripts"
        return type("R", (), {"returncode": 0, "stderr": ""})()

    monkeypatch.setattr(venv_mod.subprocess, "run", fake_run)

    path = tmp_path / "venv"
    venv_mod.create_venv(path, [wheel])

    out = capsys.readouterr().out
    assert f"Created virtualenv at {path}" in out
    assert f"Use it with: source {path / 'Scripts' / 'activate'}" in out


# --- Internal helper ---

def test__venv_python_paths_for_platforms(monkeypatch, tmp_path):
    p = tmp_path / "venv"
    # posix
    monkeypatch.setattr(venv_mod.os, "name", "posix", raising=False)
    assert venv_mod._venv_python(p) == p / "bin" / "python"
    # windows
    monkeypatch.setattr(venv_mod.os, "name", "nt", raising=False)
    assert venv_mod._venv_python(p) == p / "Scripts" / "python.exe"


# --- Edge: empty wheel list ---

def test_create_venv_with_no_wheels_still_calls_pip(monkeypatch, tmp_path):
    monkeypatch.setattr(venv_mod.venv, "EnvBuilder", lambda with_pip: type("B", (), {"create": lambda self, p: None})())

    recorded = {}

    def fake_run(cmd, **kwargs):
        recorded["cmd"] = cmd
        return type("R", (), {"returncode": 0, "stderr": ""})()

    monkeypatch.setattr(venv_mod.subprocess, "run", fake_run)

    path = tmp_path / "venv"
    venv_mod.create_venv(path, [])

    cmd = recorded["cmd"]
    # pip install with no extra args (no wheels)
    assert cmd[1] == "install" and cmd[2:] == []
