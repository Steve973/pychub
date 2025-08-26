import sys

import pytest

from pychubby.runtime.actions import install


# --- Dry-run behavior ---

def test_install_wheels_dry_run_prints(tmp_path, capsys):
    wheels = [tmp_path / f"pkg{i}.whl" for i in range(2)]
    for w in wheels:
        w.write_text("fake")

    install.install_wheels(wheels, dry_run=True, quiet=False)
    out = capsys.readouterr().out
    assert "would install:" in out
    assert "pkg0.whl" in out and "pkg1.whl" in out


def test_install_wheels_dry_run_quiet(tmp_path, capsys):
    wheel = tmp_path / "pkg.whl"
    wheel.write_text("fake")

    install.install_wheels([wheel], dry_run=True, quiet=True)
    out = capsys.readouterr().out
    assert out.strip() == ""


# --- Command building and flags ---

def test_install_wheels_builds_pip_command(monkeypatch, tmp_path):
    wheel = tmp_path / "example.whl"
    wheel.write_text("pkg")
    called = []

    def fake_run(cmd, **kwargs):
        called.append((cmd, kwargs))
        return type("R", (), {"returncode": 0, "stderr": ""})()

    monkeypatch.setattr(install.subprocess, "run", fake_run)
    monkeypatch.setattr(install, "pep668_blocked", lambda err: False)

    install.install_wheels([wheel], dry_run=False, quiet=True, no_deps=True)

    assert len(called) == 1
    cmd, kwargs = called[0]
    assert cmd[0] == sys.executable
    assert cmd[1:3] == ["-m", "pip"]
    assert "install" in cmd
    assert "--no-deps" in cmd
    assert "-q" in cmd
    assert str(wheel) in cmd


def test_install_wheels_uses_verbose_flag(monkeypatch, tmp_path):
    wheel = tmp_path / "pkg.whl"
    wheel.write_text("x")
    cmds = []

    monkeypatch.setattr(install, "pep668_blocked", lambda err: False)

    def fake_run(cmd, capture_output, text):
        cmds.append(cmd)
        return type("R", (), {"returncode": 0, "stderr": ""})()

    monkeypatch.setattr(install.subprocess, "run", fake_run)

    install.install_wheels([wheel], verbose=True)

    cmd = cmds[0]
    assert "-v" in cmd and "-q" not in cmd


def test_install_wheels_quiet_overrides_verbose(monkeypatch, tmp_path, capsys):
    wheel = tmp_path / "pkg.whl"
    wheel.write_text("x")

    calls = []

    def fake_run(cmd, **kwargs):
        calls.append(cmd)
        return type("R", (), {"returncode": 0, "stderr": ""})()

    monkeypatch.setattr(install.subprocess, "run", fake_run)
    monkeypatch.setattr(install, "pep668_blocked", lambda err: False)

    install.install_wheels([wheel], quiet=True, verbose=True)

    cmd = calls[0]
    assert "-q" in cmd and "-v" not in cmd
    # no print when quiet
    captured = capsys.readouterr()
    assert captured.out.strip() == ""


# --- PEP 668 fallback and error handling ---

def test_install_wheels_fallbacks_on_pep668(monkeypatch, tmp_path):
    wheel = tmp_path / "pkg.whl"
    wheel.write_text("wheel")
    cmds = []

    def fake_run(cmd, **kwargs):
        cmds.append(cmd)
        # First call triggers fallback, second succeeds
        if "--break-system-packages" in cmd:
            return type("R", (), {"returncode": 0, "stderr": ""})()
        return type("R", (), {"returncode": 1, "stderr": "PEP 668 warning"})()

    monkeypatch.setattr(install.subprocess, "run", fake_run)
    monkeypatch.setattr(install, "pep668_blocked", lambda err: "PEP 668" in err)

    install.install_wheels([wheel], quiet=True)
    assert any("--break-system-packages" in cmd for cmd in cmds)
    assert len(cmds) == 2


def test_install_wheels_fallback_preserves_flags(monkeypatch, tmp_path):
    wheel = tmp_path / "pkg.whl"
    wheel.write_text("wheel")
    cmds = []

    def fake_run(cmd, **kwargs):
        cmds.append(cmd)
        # Fail first, succeed second
        rc = 0 if "--break-system-packages" in cmd else 1
        return type("R", (), {"returncode": rc, "stderr": "blocked"})()

    monkeypatch.setattr(install.subprocess, "run", fake_run)
    monkeypatch.setattr(install, "pep668_blocked", lambda err: True)

    install.install_wheels([wheel], verbose=True, no_deps=True)

    first, second = cmds
    assert "install" in first and "install" in second
    assert "--no-deps" in second
    assert "-v" in second and "-q" not in second


def test_install_wheels_fails_if_both_attempts_fail_writes_stderr(monkeypatch, tmp_path, capsys):
    wheel = tmp_path / "fail.whl"
    wheel.write_text("fail")

    monkeypatch.setattr(install, "pep668_blocked", lambda err: True)

    def fake_run(cmd, **kwargs):
        return type("R", (), {"returncode": 1, "stderr": "fail msg"})()

    monkeypatch.setattr(install.subprocess, "run", fake_run)

    exits = {}

    def fake_die(code):
        exits["code"] = code
        raise SystemExit(code)

    monkeypatch.setattr(install, "die", fake_die)

    with pytest.raises(SystemExit):
        install.install_wheels([wheel])

    err = capsys.readouterr().err
    assert "fail msg" in err
    assert exits["code"] == 1


def test_install_wheels_handles_none_stderr(monkeypatch, tmp_path, capsys):
    wheel = tmp_path / "fail.whl"
    wheel.write_text("fail")

    monkeypatch.setattr(install, "pep668_blocked", lambda err: False)

    def fake_run(cmd, **kwargs):
        return type("R", (), {"returncode": 1, "stderr": None})()

    monkeypatch.setattr(install.subprocess, "run", fake_run)

    with pytest.raises(SystemExit):
        monkeypatch.setattr(install, "die", lambda code: (_ for _ in ()).throw(SystemExit(code)))
        install.install_wheels([wheel])

    # Nothing is written when stderr is None
    assert capsys.readouterr().err == ""


# --- Success output and python override ---

def test_install_wheels_success_prints_info(monkeypatch, tmp_path, capsys):
    wheel = tmp_path / "pkg.whl"
    wheel.write_text("x")

    monkeypatch.setattr(install, "pep668_blocked", lambda err: False)
    monkeypatch.setattr(install.subprocess, "run", lambda *a, **k: type("R", (), {"returncode": 0, "stderr": ""})())

    install.install_wheels([wheel], quiet=False)
    out = capsys.readouterr().out
    assert "Installed" in out and "wheel(s)" in out
    assert sys.executable in out


def test_install_wheels_respects_python_override(monkeypatch, tmp_path, capsys):
    wheel1 = tmp_path / "pkg1.whl"
    wheel2 = tmp_path / "pkg2.whl"
    for w in (wheel1, wheel2):
        w.write_text("x")

    custom_python = str(tmp_path / "python-custom")
    calls = []

    def fake_run(cmd, **kwargs):
        calls.append(cmd)
        return type("R", (), {"returncode": 0, "stderr": ""})()

    monkeypatch.setattr(install.subprocess, "run", fake_run)
    monkeypatch.setattr(install, "pep668_blocked", lambda err: False)

    install.install_wheels([wheel1, wheel2], python=custom_python)

    cmd = calls[0]
    assert cmd[0] == custom_python and cmd[1:3] == ["-m", "pip"]
    # Both wheels are appended in order
    assert cmd[-2:] == [str(wheel1), str(wheel2)]

    # Success message references the override
    out = capsys.readouterr().out
    assert custom_python in out


def test_install_wheels_passes_all_wheels_in_order(monkeypatch, tmp_path):
    wheels = [tmp_path / f"p{i}.whl" for i in range(3)]
    for w in wheels:
        w.write_text("x")

    recorded = {}

    def fake_run(cmd, **kwargs):
        recorded["cmd"] = cmd
        return type("R", (), {"returncode": 0, "stderr": ""})()

    monkeypatch.setattr(install.subprocess, "run", fake_run)
    monkeypatch.setattr(install, "pep668_blocked", lambda err: False)

    install.install_wheels(wheels)

    cmd = recorded["cmd"]
    assert cmd[-3:] == [str(w) for w in wheels]
