import os
import re

import pytest

from pychubby.runtime.actions import entrypoint


def test_none_entrypoint_returns_zero_and_writes_message(tmp_path, capsys):
    python = tmp_path / "bin" / "python"
    rc = entrypoint._run_entrypoint_with_python(python, False, None, ["--flag"])  # stderr message is user-facing
    captured = capsys.readouterr()
    assert rc == 0
    assert "pychubby: no entrypoint to run; installation complete." in captured.err


def test_module_function_invokes_spawnv_with_python_dash_c(monkeypatch, tmp_path):
    python = tmp_path / "venv" / "bin" / "python"
    calls = {}

    def fake_spawnv(mode, file, args):
        calls["mode"] = mode
        calls["file"] = file
        calls["args"] = list(args)
        return 3

    monkeypatch.setattr(os, "spawnv", fake_spawnv)

    rc = entrypoint._run_entrypoint_with_python(python, False, "pkg.mod:main", ["--a", "1"])
    assert rc == 3
    assert calls["file"] == str(python)
    assert calls["args"][0] == str(python)
    assert calls["args"][1] == "-c"

    code = calls["args"][2]
    assert "importlib.import_module('pkg.mod')" in code
    # whitespace-insensitive match for getattr(mod,'main')
    assert re.search(r"getattr\(mod\s*,\s*'main'\)", code)

    # prove argv passthrough is preserved after the code string
    assert calls["args"][3:] == ["--a", "1"]


def test_console_script_uses_local_bin_when_present(monkeypatch, tmp_path):
    venv_bin = tmp_path / "venv" / "bin"
    venv_bin.mkdir(parents=True)
    python = venv_bin / "python"
    script = venv_bin / "mytool"
    script.write_text("#!/usr/bin/env python")

    called = {}

    def fake_spawnv(mode, file, args):
        called["file"] = file
        called["args"] = list(args)
        return 0

    def fake_spawnvp(mode, file, args):  # should not be used
        raise AssertionError("spawnvp should not be called when local script exists")

    monkeypatch.setattr(os, "spawnv", fake_spawnv)
    monkeypatch.setattr(os, "spawnvp", fake_spawnvp)

    rc = entrypoint._run_entrypoint_with_python(python, False, "mytool", ["-x"])
    assert rc == 0
    assert called["file"] == str(script)
    assert called["args"] == [str(script), "-x"]


def test_console_script_prefers_exe_on_windows(monkeypatch, tmp_path):
    scripts = tmp_path / "venv" / "Scripts"
    scripts.mkdir(parents=True)
    python = scripts / "python.exe"
    (scripts / "mytool").write_text("stub")
    exe = scripts / "mytool.exe"
    exe.write_text("stub")  # presence should trigger .exe preference

    called = {}

    def fake_spawnv(mode, file, args):
        called["file"] = file
        called["args"] = list(args)
        return 7

    monkeypatch.setattr(os, "spawnv", fake_spawnv)
    monkeypatch.setattr(os, "name", "nt", raising=False)

    rc = entrypoint._run_entrypoint_with_python(python, False, "mytool", ["--v"])
    assert rc == 7
    assert called["file"] == str(exe)
    assert called["args"] == [str(exe), "--v"]


@pytest.mark.parametrize("parent_name", ["bin", "Scripts", "other"])  # cover missing local binary and non-venv parent
def test_console_script_falls_back_to_spawnvp_when_missing_local(monkeypatch, tmp_path, parent_name):
    parent = tmp_path / "venv" / parent_name
    parent.mkdir(parents=True)
    python = parent / "python"

    called = {}

    def fake_spawnv(mode, file, args):  # must not be used without local file
        raise AssertionError("spawnv should not be called when candidate does not exist")

    def fake_spawnvp(mode, file, args):
        called["file"] = file
        called["args"] = list(args)
        return 42

    monkeypatch.setattr(os, "spawnv", fake_spawnv)
    monkeypatch.setattr(os, "spawnvp", fake_spawnvp)

    rc = entrypoint._run_entrypoint_with_python(python, False, "cli-tool", ["--flag", "1"])
    assert rc == 42
    assert called["file"] == "cli-tool"
    assert called["args"] == ["cli-tool", "--flag", "1"]
