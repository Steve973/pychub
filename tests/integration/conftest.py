import os
import shutil
import subprocess
import tempfile
import venv
from pathlib import Path

import pytest

from pychubby.constants import CHUB_BUILD_DIR


@pytest.fixture(scope="session")
def test_env():
    """Shared test environment: temp dir, venv, built wheel, pychubby install."""
    root_dir = Path(__file__).resolve().parent.parent.parent
    src_dir = root_dir / "src"
    test_pkg_dir = root_dir / "tests" / "test_proj"
    dist_dir = test_pkg_dir / "dist"

    temp_dir = Path(tempfile.mkdtemp(prefix="integration-tests-"))
    venv_dir = temp_dir / "venv"

    # Create venv
    venv.create(venv_dir, with_pip=True)
    python_bin = venv_dir / "bin" / "python"
    if not python_bin.exists():
        python_bin = venv_dir / "Scripts" / "python.exe"
    if not python_bin.exists():
        raise RuntimeError("Could not find venv Python binary")

    subprocess.run(
        [str(python_bin), "-m", "pip", "install", "--upgrade", "poetry"],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE)

    # Install pychubby (editable)
    subprocess.run(
        [str(python_bin), "-m", "pip", "install", "-e", str(root_dir)],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE)

    # Build wheel once
    subprocess.run(
        ["poetry", "build"],
        cwd=test_pkg_dir,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE)

    wheels = list(dist_dir.glob("*.whl"))
    assert wheels, "No wheel was built"

    yield {
        "temp_dir": temp_dir,
        "venv_dir": venv_dir,
        "python_bin": python_bin,
        "root_dir": root_dir,
        "src_dir": src_dir,
        "test_pkg_dir": test_pkg_dir,
        "wheel_path": wheels[0]
    }

    shutil.rmtree(temp_dir)


def run_build_cli(wheel_path: Path, tmp_path: Path, test_env: dict, **kwargs):
    chub_build_dir = tmp_path / CHUB_BUILD_DIR
    chub_out = tmp_path / "test_pkg.chub"

    # 🚽 Clean up chub-build to avoid .chubconfig conflicts
    if chub_build_dir.exists():
        shutil.rmtree(chub_build_dir)

    args = [
        str(test_env["python_bin"]),
        "-m", "pychubby.cli",
        str(wheel_path),
        "--chub", str(chub_out),
    ]

    if "entrypoint" in kwargs:
        args += ["--entrypoint", kwargs["entrypoint"]]
    if "scripts" in kwargs:
        for script in kwargs["scripts"]:
            args += ["--scripts", script]
    if "includes" in kwargs:
        for inc in kwargs["includes"]:
            args += ["--includes", inc]
    if "metadata" in kwargs:
        for k, v in kwargs["metadata"].items():
            args += ["--metadata-entry", k, v]

    env = os.environ.copy()
    env["PYTHONPATH"] = str(test_env["src_dir"])

    result = subprocess.run(
        args,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=env)

    return result, chub_out
