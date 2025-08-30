from __future__ import annotations

from pathlib import Path
import shutil
import zipfile

from tests.integration.conftest import run_build_cli


def mk_chub_with_entrypoint(tmp_path: Path, test_env: dict,
                            entry: str = "test_pkg.greet:main") -> Path:
    """
    Builds a .chub with a baked entrypoint. Returns the path to .chub.
    """
    result, chub_path = run_build_cli(
        test_env["wheel_path"], tmp_path, test_env, entrypoint=entry
    )
    assert result.returncode == 0, result.stderr
    return chub_path


def mk_chub_basic(tmp_path: Path, test_env: dict) -> Path:
    """
    Builds a .chub without an entrypoint. Returns the path to .chub.
    Useful for flags that don't need run/exec.
    """
    result, chub_path = run_build_cli(
        test_env["wheel_path"], tmp_path, test_env
    )
    assert result.returncode == 0, result.stderr
    return chub_path


def mk_chub_with_scripts(tmp_path: Path, test_env: dict,
                         *, sentinel: str = "post_install_ok.txt",
                         failing: bool = False) -> Path:
    """
    Builds a .chub that contains a post-install script. The script writes a
    sentinel file by default; if failing=True it exits non-zero.
    Assumes your test wheel reads scripts from 'scripts/'.
    """
    script_dir = tmp_path / "scripts"
    script_dir.mkdir(parents=True, exist_ok=True)
    script_path = script_dir / "post_install.sh"
    if failing:
        script_path.write_text("#!/usr/bin/env bash\nexit 2\n")
    else:
        script_path.write_text(
            "#!/usr/bin/env bash\n"
            f'echo "ok" > "{sentinel}"\n'
        )
    script_path.chmod(0o755)

    result, chub_path = run_build_cli(
        test_env["wheel_path"], tmp_path, test_env, scripts=[str(script_path)]
    )
    assert result.returncode == 0, result.stderr
    return chub_path


def mk_chub_multi_primary(tmp_path: Path, test_env: dict,
                          second_wheel: Path | None = None) -> Path:
    """
    Builds a .chub with the normal main wheel and a second primary wheel
    appended. If you don't pass a wheel, we just append the same one again
    (fine for list/only tests).
    """
    # First wheel
    result, chub_path = run_build_cli(
        test_env["wheel_path"], tmp_path, test_env
    )
    assert result.returncode == 0, result.stderr

    # Second wheel (append)
    sw = second_wheel or test_env["wheel_path"]
    result, chub_path = run_build_cli(
        sw, tmp_path, test_env,  # same --chub path reused by helper
    )
    assert result.returncode == 0, result.stderr
    return chub_path


def mk_corrupt_chub(tmp_path: Path, test_env: dict) -> Path:
    """
    Produces a corrupt .chub by truncating bytes. Intended to exercise
    error paths that surface pip/zip errors.
    """
    good = mk_chub_basic(tmp_path, test_env)
    bad = tmp_path / "corrupt.chub"
    with open(good, "rb") as src, open(bad, "wb") as dst:
        data = src.read()
        dst.write(data[: max(0, len(data) // 3)])  # truncate hard
    return bad


def unpack_chub_to_dir(chub: Path, dest: Path) -> None:
    """
    For tests that need to inspect the archive without running it.
    """
    dest.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(chub) as zf:
        zf.extractall(dest)


def rm_tree(path: Path) -> None:
    if path.exists():
        shutil.rmtree(path)
