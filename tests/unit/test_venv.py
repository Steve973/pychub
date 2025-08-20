import os

import pytest

from pychubby.runtime.actions import venv as venv_mod


def test_create_venv_dry_run(capsys, tmp_path):
    wheels = [tmp_path / "a.whl", tmp_path / "b.whl"]
    for w in wheels:
        w.write_text("fake")

    venv_mod.create_venv(tmp_path / "venv", wheels, dry_run=True)

    out = capsys.readouterr().out
    assert "[dry-run] would create venv at" in out
    assert "a.whl" in out
    assert "b.whl" in out


def test_create_venv_happy_path(monkeypatch, tmp_path):
    created = {}
    wheels = [tmp_path / "a.whl"]
    wheels[0].write_text("fake")

    class DummyBuilder:
        def create(self, path):
            created["path"] = path

    monkeypatch.setattr(venv_mod.venv, "EnvBuilder", lambda with_pip: DummyBuilder())

    called = {}

    def fake_run(cmd, capture_output, text):
        called["cmd"] = cmd
        called["capture_output"] = capture_output
        return DummyResult(0)

    class DummyResult:
        def __init__(self, returncode):
            self.returncode = returncode
            self.stderr = ""

    monkeypatch.setattr(venv_mod.subprocess, "run", fake_run)

    venv_mod.create_venv(tmp_path / "venv", wheels)

    assert created["path"] == tmp_path / "venv"
    pip_path = tmp_path / "venv" / ("Scripts" if os.name == "nt" else "bin") / "pip"
    assert pip_path.as_posix() in " ".join(called["cmd"])
    assert "a.whl" in " ".join(called["cmd"])
    assert called["capture_output"] is True


def test_create_venv_quiet_and_verbose(monkeypatch, tmp_path):
    wheels = [tmp_path / "a.whl"]
    wheels[0].write_text("fake")

    monkeypatch.setattr(venv_mod.venv, "EnvBuilder", lambda with_pip: type("B", (), {"create": lambda self, p: None})())

    results = []

    def fake_run(cmd, capture_output, text):
        results.append((cmd, capture_output))
        return type("R", (), {"returncode": 0, "stderr": ""})()

    monkeypatch.setattr(venv_mod.subprocess, "run", fake_run)

    venv_mod.create_venv(tmp_path / "venv1", wheels, quiet=True)
    venv_mod.create_venv(tmp_path / "venv2", wheels, verbose=True)

    quiet_cmd, quiet_cap = results[0]
    verbose_cmd, verbose_cap = results[1]

    assert "-q" in quiet_cmd
    assert quiet_cap is True

    assert "-v" in verbose_cmd
    assert verbose_cap is False


def test_create_venv_install_fails(monkeypatch, tmp_path, capsys):
    wheels = [tmp_path / "bad.whl"]
    wheels[0].write_text("fake")

    monkeypatch.setattr(venv_mod.venv, "EnvBuilder", lambda with_pip: type("B", (), {"create": lambda self, p: None})())

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
        venv_mod.create_venv(tmp_path / "venv", wheels)

    err = capsys.readouterr().err
    assert "pip failed" in err
    assert exit_code["code"] == 42
