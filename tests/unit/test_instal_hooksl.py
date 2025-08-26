from pathlib import Path
import pytest

from pychubby.runtime.actions import install_hooks


# Helpers to force predictable directories inside the temp bundle
@pytest.fixture(autouse=True)
def _patch_constants(monkeypatch):
    monkeypatch.setattr(install_hooks, "CHUB_SCRIPTS_DIR", "scripts", raising=False)
    monkeypatch.setattr(install_hooks, "CHUB_POST_INSTALL_SCRIPTS_DIR", "post", raising=False)
    monkeypatch.setattr(install_hooks, "CHUB_PRE_INSTALL_SCRIPTS_DIR", "pre", raising=False)


# ---- Happy paths ----

def test_post_install_runs_success(monkeypatch, tmp_path):
    base = tmp_path / "scripts" / "post"
    base.mkdir(parents=True)
    (base / "ok.sh").write_text("echo ok")

    calls = {}

    def fake_run(cmd, **kwargs):
        # record cmd and kwargs; ensure not using shell and check=False
        calls["cmd"] = cmd
        calls["kwargs"] = kwargs
        return type("R", (), {"returncode": 0})()

    monkeypatch.setattr(install_hooks.subprocess, "run", fake_run)

    scripts = ["ok.sh"]
    install_hooks.run_post_install_scripts(tmp_path, scripts)

    # resolved absolute path and proper flags
    path = Path(calls["cmd"][0])
    assert path.is_absolute() and path.name == "ok.sh"
    assert calls["kwargs"].get("check") is False


def test_pre_install_runs_success(monkeypatch, tmp_path):
    base = tmp_path / "scripts" / "pre"
    base.mkdir(parents=True)
    (base / "prep.sh").write_text("echo prep")

    recorded = []

    def fake_run(cmd, **kwargs):
        recorded.append(Path(cmd[0]).name)
        return type("R", (), {"returncode": 0})()

    monkeypatch.setattr(install_hooks.subprocess, "run", fake_run)

    install_hooks.run_pre_install_scripts(tmp_path, ["prep.sh"])
    assert recorded == ["prep.sh"]


# ---- Warnings and errors ----

def test_warns_if_missing_script(tmp_path, capsys):
    # no file created on purpose
    install_hooks.run_post_install_scripts(tmp_path, ["missing.sh"])
    err = capsys.readouterr().err
    assert "[warn]" in err and "post-install script not found" in err
    assert "missing.sh" in err


def test_exits_with_return_code_on_failure(monkeypatch, tmp_path, capsys):
    base = tmp_path / "scripts" / "post"
    base.mkdir(parents=True)
    (base / "bad.sh").write_text("exit 1")

    monkeypatch.setattr(
        install_hooks.subprocess,
        "run",
        lambda *a, **k: type("R", (), {"returncode": 17})(),
    )

    exits = {}

    def fake_exit(code):
        exits["code"] = code
        raise SystemExit(code)

    monkeypatch.setattr(install_hooks.sys, "exit", fake_exit)

    with pytest.raises(SystemExit):
        install_hooks.run_post_install_scripts(tmp_path, ["bad.sh"])

    err = capsys.readouterr().err
    assert "[error]" in err and "post-install script failed" in err
    assert exits["code"] == 17


# ---- Ordering & stopping semantics ----

def test_runs_multiple_sorted_and_stops_on_first_failure(monkeypatch, tmp_path):
    base = tmp_path / "scripts" / "pre"
    base.mkdir(parents=True)
    (base / "b.sh").write_text("echo b")
    (base / "a.sh").write_text("echo a")
    (base / "c.sh").write_text("exit 1")

    seen = []

    def fake_run(cmd, **kwargs):
        name = Path(cmd[0]).name
        seen.append(name)
        rc = 1 if name == "c.sh" else 0
        return type("R", (), {"returncode": rc})()

    monkeypatch.setattr(install_hooks.subprocess, "run", fake_run)
    monkeypatch.setattr(install_hooks.sys, "exit", lambda code: (_ for _ in ()).throw(SystemExit(code)))

    with pytest.raises(SystemExit):
        # unsorted input on purpose; function sorts first
        install_hooks.run_pre_install_scripts(tmp_path, ["c.sh", "b.sh", "a.sh"])

    # must run in lexicographic order a -> b -> c, and stop at c
    assert seen == ["a.sh", "b.sh", "c.sh"]


def test_sorts_input_list_in_place(monkeypatch, tmp_path):
    base = tmp_path / "scripts" / "post"
    base.mkdir(parents=True)
    for n in ("z.sh", "y.sh"):
        (base / n).write_text("echo")

    monkeypatch.setattr(install_hooks.subprocess, "run", lambda *a, **k: type("R", (), {"returncode": 0})())

    items = ["z.sh", "y.sh"]
    install_hooks.run_post_install_scripts(tmp_path, items)
    assert items == ["y.sh", "z.sh"]


# ---- Delegation wrappers sanity ----

def test_wrappers_delegate_correct_type(monkeypatch, tmp_path):
    passed = []

    def spy(root, kind, scripts):
        passed.append((root, kind, list(scripts)))

    monkeypatch.setattr(install_hooks, "run_install_scripts", spy)

    install_hooks.run_post_install_scripts(tmp_path, ["p.sh"])
    install_hooks.run_pre_install_scripts(tmp_path, ["r.sh"])

    kinds = [k for _, k, _ in passed]
    assert kinds == [install_hooks.CHUB_POST_INSTALL_SCRIPTS_DIR, install_hooks.CHUB_PRE_INSTALL_SCRIPTS_DIR]
    assert passed[0][2] == ["p.sh"] and passed[1][2] == ["r.sh"]
