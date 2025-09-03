import os
import shutil
import subprocess
import tempfile
import venv
import zipfile
from pathlib import Path

import pytest

from pychubby.package.constants import CHUB_BUILD_DIR


@pytest.fixture(scope="session")
def test_env():
    """Shared test environment: temp dir, venv, built wheel, pychubby install."""
    root_dir = Path(__file__).resolve().parent.parent.parent
    src_dir = root_dir / "src"
    test_pkg_dir = root_dir / "tests" / "test_proj"
    dist_dir = test_pkg_dir / "dist"

    temp_dir = Path(tempfile.mkdtemp(prefix="integration-tests-"))
    venv_dir = temp_dir / "venv"

    venv.create(venv_dir, with_pip=True)
    python_bin = venv_dir / "bin" / "python"
    if not python_bin.exists():
        python_bin = venv_dir / "Scripts" / "python.exe"
    if not python_bin.exists():
        raise RuntimeError("Could not find venv Python binary")

    # install poetry inside the nested venv
    subprocess.run(
        [str(python_bin), "-m", "pip", "install", "--upgrade", "poetry"],
        check=True,
    )

    # install the project under test
    subprocess.run(
        [str(python_bin), "-m", "pip", "install", "-e", str(root_dir)],
        check=True,
    )

    # build the test package using poetry from this venv
    subprocess.run(
        [str(python_bin), "-m", "poetry", "build"],
        cwd=test_pkg_dir,
        check=True,
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


def run_runtime_cli(chub_path: Path, args: list[str], python_bin: Path):
    return subprocess.run([str(python_bin), str(chub_path), *args], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)


def run_build_cli(wheel_path: Path, tmp_path: Path, test_env: dict, **kwargs):
    chub_build_dir = tmp_path / CHUB_BUILD_DIR
    chub_out = tmp_path / "test_pkg.chub"

    if chub_build_dir.exists():
        shutil.rmtree(chub_build_dir)

    args = [
        str(test_env["python_bin"]),
        "-m",
        "pychubby.package.cli",
        str(wheel_path),
        "--chub",
        str(chub_out),
    ]

    chubproject = kwargs.get("chubproject")
    if chubproject:
        args += ["--chubproject", chubproject]

    chubproject_save = kwargs.get("chubproject_save")
    if chubproject_save:
        args += ["--chubproject-save", chubproject_save]

    entrypoint = kwargs.get("entrypoint")
    if entrypoint:
        args += ["--entrypoint", entrypoint]

    # Includes: --include FILE[::dest]
    includes = kwargs.get("includes")
    if includes:
        for inc in includes:
            args += ["--include", inc]

    # Post-install scripts: --post-script PATH
    post_scripts = kwargs.get("scripts_post")
    if post_scripts:
        for script in post_scripts:
            args += ["--post-script", script]

    # Pre-install scripts: --pre-script PATH
    pre_scripts = kwargs.get("scripts_pre")
    if pre_scripts:
        for script in pre_scripts:
            args += ["--pre-script", script]

    # Metadata: --metadata-entry KEY=VALUE
    metadata = kwargs.get("metadata")
    if metadata:
        for k, v in metadata.items():
            val = v if isinstance(v, str) else ",".join(v)
            args += ["--metadata-entry", f"{k}={val}"]

    env = os.environ.copy()
    env["PYTHONPATH"] = str(test_env["src_dir"])

    result = subprocess.run(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=env)
    return result, chub_out


def get_chub_contents(chub_path: Path):
    """Return (names, ChubConfig instance) from the built .chub archive."""
    from pychubby.model.chubconfig_model import ChubConfig

    with zipfile.ZipFile(chub_path, "r") as zf:
        names = zf.namelist()
        text = None
        for name in names:
            if name.endswith(".chubconfig"):
                with zf.open(name) as f:
                    text = f.read().decode("utf-8")
                break
        if text is None:
            return names, None
        cfg = ChubConfig.from_yaml(text)
        return names, cfg
