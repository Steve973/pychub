import os
from pathlib import Path

import pytest

from tests.integration._asserts import (
    assert_rc_ok,
    assert_in_stdout,
)
from tests.integration.conftest import run_runtime_cli, run_build_cli


def _venv_python_path(venv_path: Path) -> Path:
    bin_dir = venv_path / ("Scripts" if os.name == "nt" else "bin")
    return bin_dir / ("python.exe" if os.name == "nt" else "python")


@pytest.mark.integration
def test_venv_create_and_install_basic(test_env, tmp_path):
    proc, chub = run_build_cli(test_env["wheel_path"], tmp_path, test_env)
    assert_rc_ok(proc)

    venv_path = tmp_path / "v1"
    proc = run_runtime_cli(chub, ["--venv", str(venv_path)], test_env["python_bin"])
    assert_rc_ok(proc)
    assert _venv_python_path(venv_path).exists()


@pytest.mark.integration
def test_exec_runs_entrypoint(test_env, tmp_path):
    proc, chub = run_build_cli(
        test_env["wheel_path"], tmp_path, test_env, entrypoint="test_pkg.greet:main"
    )
    assert_rc_ok(proc)

    proc = run_runtime_cli(chub, ["--exec"], test_env["python_bin"])
    assert_rc_ok(proc)
    assert_in_stdout(proc, "hello")


@pytest.mark.integration
def test_venv_dry_run_creates_nothing(test_env, tmp_path):
    proc, chub = run_build_cli(test_env["wheel_path"], tmp_path, test_env)
    assert_rc_ok(proc)

    venv_path = tmp_path / "v_dry"
    proc = run_runtime_cli(chub, ["--dry-run", "--venv", str(venv_path)], test_env["python_bin"])
    assert_rc_ok(proc)
    assert not venv_path.exists()


@pytest.mark.integration
def test_venv_quiet_is_shorter_than_verbose(test_env, tmp_path):
    proc, chub = run_build_cli(test_env["wheel_path"], tmp_path, test_env)
    assert_rc_ok(proc)

    vquiet = tmp_path / "v_q"
    vverb = tmp_path / "v_v"

    p_quiet = run_runtime_cli(chub, ["--venv", str(vquiet), "--quiet"], test_env["python_bin"])
    p_verbose = run_runtime_cli(chub, ["--venv", str(vverb), "--verbose"], test_env["python_bin"])

    assert_rc_ok(p_quiet)
    assert_rc_ok(p_verbose)

    assert _venv_python_path(vquiet).exists()
    assert _venv_python_path(vverb).exists()

    assert len((p_quiet.stdout or "").strip()) <= len((p_verbose.stdout or "").strip())


@pytest.mark.integration
def test_venv_reuse_existing_path_is_ok(test_env, tmp_path):
    proc, chub = run_build_cli(test_env["wheel_path"], tmp_path, test_env)
    assert_rc_ok(proc)

    venv_path = tmp_path / "v_reuse"
    p1 = run_runtime_cli(chub, ["--venv", str(venv_path)], test_env["python_bin"])
    assert_rc_ok(p1)
    assert _venv_python_path(venv_path).exists()

    p2 = run_runtime_cli(chub, ["--venv", str(venv_path)], test_env["python_bin"])
    assert_rc_ok(p2)
    assert _venv_python_path(venv_path).exists()


@pytest.mark.integration
def test_venv_dry_run_then_real_creation(test_env, tmp_path):
    proc, chub = run_build_cli(test_env["wheel_path"], tmp_path, test_env)
    assert_rc_ok(proc)

    venv_path = tmp_path / "v_dry_then_real"
    p_dry = run_runtime_cli(chub, ["--dry-run", "--venv", str(venv_path)], test_env["python_bin"])
    assert_rc_ok(p_dry)
    assert not venv_path.exists()

    p_real = run_runtime_cli(chub, ["--venv", str(venv_path)], test_env["python_bin"])
    assert_rc_ok(p_real)
    assert _venv_python_path(venv_path).exists()


@pytest.mark.integration
def test_venv_path_with_spaces_works(test_env, tmp_path):
    proc, chub = run_build_cli(test_env["wheel_path"], tmp_path, test_env)
    assert_rc_ok(proc)

    venv_path = tmp_path / "venv with spaces"
    proc = run_runtime_cli(chub, ["--venv", str(venv_path)], test_env["python_bin"])
    assert_rc_ok(proc)
    assert _venv_python_path(venv_path).exists()
