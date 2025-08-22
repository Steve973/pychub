import subprocess
from pathlib import Path

import pytest

from tests.integration.conftest import run_build_cli


def run_runtime_cli(chub_path: Path, args: list[str], python_bin: Path) -> subprocess.CompletedProcess:
    print(f"Running chub {chub_path} runtime with args: {args}")
    return subprocess.run(
        [str(python_bin), str(chub_path), *args],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True)


@pytest.mark.integration
def test_runtime_run_entrypoint(test_env, tmp_path):
    result, chub_path = run_build_cli(
        test_env["wheel_path"],
        tmp_path,
        test_env,
        entrypoint="test_pkg.greet:main")
    assert result.returncode == 0, result.stderr

    result = run_runtime_cli(chub_path, ["--run"], test_env["python_bin"])
    assert result.returncode == 0
    assert "hello" in result.stdout.lower()


@pytest.mark.integration
def test_runtime_exec_entrypoint(test_env, tmp_path):
    result, chub_path = run_build_cli(
        test_env["wheel_path"],
        tmp_path,
        test_env,
        entrypoint="test_pkg.greet:main")
    assert result.returncode == 0

    result = run_runtime_cli(chub_path, ["--exec"], test_env["python_bin"])
    assert result.returncode == 0
    assert "hello" in result.stdout.lower()


@pytest.mark.integration
def test_runtime_list_wheels(test_env, tmp_path):
    result, chub_path = run_build_cli(
        test_env["wheel_path"],
        tmp_path,
        test_env)
    assert result.returncode == 0

    result = run_runtime_cli(chub_path, ["--list"], test_env["python_bin"])
    assert result.returncode == 0
    assert "test_pkg" in result.stdout.lower()


@pytest.mark.integration
def test_runtime_dry_run_install(test_env, tmp_path):
    result, chub_path = run_build_cli(
        test_env["wheel_path"],
        tmp_path,
        test_env)
    assert result.returncode == 0

    result = run_runtime_cli(chub_path, ["--dry-run"], test_env["python_bin"])
    assert result.returncode == 0
    assert "dry" in result.stdout.lower() or "install" in result.stdout.lower()


@pytest.mark.integration
def test_runtime_unpack_to_dir(test_env, tmp_path):
    result, chub_path = run_build_cli(
        test_env["wheel_path"],
        tmp_path,
        test_env)
    assert result.returncode == 0

    unpack_dir = tmp_path / "unpacked"
    result = run_runtime_cli(chub_path, ["--unpack", str(unpack_dir)], test_env["python_bin"])
    assert result.returncode == 0
    assert unpack_dir.exists()
    assert any(p.suffix == ".whl" for p in unpack_dir.iterdir())


@pytest.mark.integration
def test_runtime_install_to_venv(test_env, tmp_path):
    result, chub_path = run_build_cli(
        test_env["wheel_path"],
        tmp_path,
        test_env)
    assert result.returncode == 0

    venv_path = tmp_path / "venv_runtime"
    result = run_runtime_cli(chub_path, ["--venv", str(venv_path)], test_env["python_bin"])
    assert result.returncode == 0
    bin_dir = venv_path / "bin" if (venv_path / "bin").exists() else venv_path / "Scripts"
    assert (bin_dir / "python3").exists() or (bin_dir / "python.exe").exists()
