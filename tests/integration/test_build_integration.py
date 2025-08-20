import os
import shutil
import subprocess
import tempfile
import venv
import zipfile
from pathlib import Path

import pytest
import yaml

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

    # Install pychubby (editable)
    subprocess.run(
        [str(python_bin), "-m", "pip", "install", "-e", str(root_dir)],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    # Build wheel once
    subprocess.run(
        ["poetry", "build"],
        cwd=test_pkg_dir,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
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
    chub_build_dir = tmp_path / CHUB_BUILD_DIR / "test-pkg-0.1.0"
    print ("##### Chub build dir: ", chub_build_dir)
    chub_out = tmp_path / "test_pkg.chub"
    print("##### Chub output file: ", chub_out)

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

    return subprocess.run(
        args,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=env,
    )


def get_chub_contents(chub_path):
    with zipfile.ZipFile(chub_path, "r") as zf:
        names = zf.namelist()
        chubconfig = None
        for name in names:
            if name.endswith(".chubconfig"):
                with zf.open(name) as f:
                    chubconfig = list(yaml.safe_load_all(f.read()))
        return names, chubconfig


@pytest.mark.integration
def test_basic_build(test_env, tmp_path):
    result = run_build_cli(test_env["wheel_path"], tmp_path, test_env)
    assert result.returncode == 0, result.stderr
    chub_path = tmp_path / "test_pkg.chub"
    assert chub_path.exists()
    names, config = get_chub_contents(chub_path)
    assert any(p.endswith(".whl") for p in names)
    assert "__main__.py" in names
    assert config and config[0]["name"] == "test-pkg"


@pytest.mark.integration
def test_entrypoint_build(test_env, tmp_path):
    result = run_build_cli(
        test_env["wheel_path"],
        tmp_path,
        test_env,
        entrypoint="test_pkg.greet:main"
    )
    assert result.returncode == 0, result.stderr
    _, config = get_chub_contents(tmp_path / "test_pkg.chub")
    assert config[0]["entrypoint"] == "test_pkg.greet:main"


@pytest.mark.integration
def test_invalid_entrypoint_format(test_env, tmp_path):
    result = run_build_cli(
        test_env["wheel_path"],
        tmp_path,
        test_env,
        entrypoint="badentrypoint"
    )
    assert result.returncode != 0
    assert "Invalid entrypoint format" in result.stderr


@pytest.mark.integration
def test_metadata_entry(test_env, tmp_path):
    result = run_build_cli(
        test_env["wheel_path"],
        tmp_path,
        test_env,
        metadata={"author": "steve", "tags": "foo,bar"}
    )
    assert result.returncode == 0
    _, config = get_chub_contents(tmp_path / "test_pkg.chub")
    assert config[0]["metadata"] == {"author": "steve", "tags": ["foo", "bar"]}
