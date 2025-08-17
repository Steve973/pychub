from pathlib import Path

import pytest

from pychubby.runtime.actions import post_install


def test_post_install_runs_success(monkeypatch, tmp_path):
    script_path = tmp_path / "ok.sh"
    script_path.write_text("echo ok")
    script = str(script_path.relative_to(tmp_path))

    called = {}

    def fake_run(cmd, shell):
        called["cmd"] = cmd
        return type("R", (), {"returncode": 0})()

    monkeypatch.setattr(post_install.subprocess, "run", fake_run)
    post_install.run_post_install_scripts(tmp_path, [script])

    # Check that it resolved the path correctly and called subprocess.run
    assert f'{called["cmd"][0]}'.endswith("ok.sh")


def test_post_install_warns_if_missing(tmp_path, capsys):
    missing = "nope.sh"
    post_install.run_post_install_scripts(tmp_path, [missing])

    err = capsys.readouterr().err
    assert "post-install script not found" in err
    assert "nope.sh" in err


def test_post_install_exits_on_failure(monkeypatch, tmp_path):
    script_path = tmp_path / "bad.sh"
    script_path.write_text("exit 1")
    script = str(script_path.relative_to(tmp_path))

    monkeypatch.setattr(post_install.subprocess, "run", lambda *a, **k: type("R", (), {"returncode": 1})())

    exits = {}

    def fake_exit(msg):
        exits["msg"] = msg
        raise SystemExit(msg)

    monkeypatch.setattr(post_install.sys, "exit", fake_exit)

    with pytest.raises(SystemExit) as exc:
        post_install.run_post_install_scripts(tmp_path, [script])

    assert "Post-install script failed" in exits["msg"]
    assert "bad.sh" in exits["msg"]


def test_post_install_runs_multiple_and_stops_on_fail(monkeypatch, tmp_path):
    script1 = tmp_path / "ok1.sh"
    script1.write_text("echo ok")
    script2 = tmp_path / "fail2.sh"
    script2.write_text("exit 1")
    rel1 = str(script1.relative_to(tmp_path))
    rel2 = str(script2.relative_to(tmp_path))

    calls = []

    def fake_run(cmd, shell):
        path = Path(cmd[0])
        calls.append(path.name)
        return type("R", (), {"returncode": 0 if "ok1" in str(path) else 1})()

    monkeypatch.setattr(post_install.subprocess, "run", fake_run)

    def fake_exit(msg):
        raise SystemExit(msg)

    monkeypatch.setattr(post_install.sys, "exit", fake_exit)

    with pytest.raises(SystemExit):
        post_install.run_post_install_scripts(tmp_path, [rel1, rel2])

    assert calls == ["ok1.sh", "fail2.sh"]
