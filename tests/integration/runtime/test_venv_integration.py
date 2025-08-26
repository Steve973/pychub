import os
import pytest
from tests.integration._asserts import assert_rc_ok, assert_in_stdout
from tests.integration.conftest import run_runtime_cli, run_build_cli


def _venv_python_path(venv_path):
    bin_dir = venv_path / ("Scripts" if os.name == "nt" else "bin")
    return bin_dir / ("python.exe" if os.name == "nt" else "python3")

@pytest.mark.integration
def test_venv_create_and_install_basic(test_env, tmp_path):
    proc, chub = run_build_cli(test_env["wheel_path"], tmp_path, test_env)
    assert_rc_ok(proc)

    venv_path = tmp_path / "v1"
    proc = run_runtime_cli(
        chub, ["--venv", str(venv_path)], test_env["python_bin"])
    assert_rc_ok(proc)
    assert _venv_python_path(venv_path).exists()


@pytest.mark.integration
def test_venv_with_run_executes_entrypoint(test_env, tmp_path):
    proc, chub = run_build_cli(
        test_env["wheel_path"], tmp_path, test_env,
        entrypoint="test_pkg.greet:main")
    assert_rc_ok(proc)

    venv_path = tmp_path / "v2"
    proc = run_runtime_cli(
        chub, ["--exec", "--venv", str(venv_path)],
        test_env["python_bin"])
    assert_rc_ok(proc)
    assert_in_stdout(proc, "hello")


@pytest.mark.integration
def test_venv_dry_run_creates_nothing(test_env, tmp_path):
    proc, chub = run_build_cli(test_env["wheel_path"], tmp_path, test_env)
    assert_rc_ok(proc)

    venv_path = tmp_path / "v_dry"
    proc = run_runtime_cli(
        chub, ["--dry-run", "--venv", str(venv_path)],
        test_env["python_bin"])
    assert_rc_ok(proc)
    assert not venv_path.exists()
