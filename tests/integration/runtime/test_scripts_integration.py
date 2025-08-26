import os
from pathlib import Path
import pytest
from tests.integration._asserts import assert_rc_ok
from tests.integration.conftest import run_build_cli, run_runtime_cli


def _write_py_script(path: Path, body: str) -> Path:
    path.write_text("#!/usr/bin/env python3\n" + body)
    path.chmod(0o755)
    return path

@pytest.mark.integration
def test_post_install_script_runs(test_env, tmp_path):
    sentinel = tmp_path / "script_ok.txt"
    script = _write_py_script(
        tmp_path / "post_ok.py",
        f'open(r"{sentinel}", "w").write("ok")\n'
    )

    proc, chub = run_build_cli(
        test_env["wheel_path"], tmp_path, test_env,
        scripts=[str(script)])
    assert_rc_ok(proc)

    proc = run_runtime_cli(chub, [], test_env["python_bin"])
    assert_rc_ok(proc)
    assert sentinel.exists()


@pytest.mark.integration
def test_no_scripts_flag_skips_post_install(test_env, tmp_path):
    sentinel = tmp_path / "script_skipped.txt"
    script = _write_py_script(
        tmp_path / "post_skip.py",
        f'open(r"{sentinel}", "w").write("ran")\n'
    )

    proc, chub = run_build_cli(
        test_env["wheel_path"], tmp_path, test_env,
        scripts=[str(script)])
    assert_rc_ok(proc)

    proc = run_runtime_cli(
        chub, ["--no-scripts"], test_env["python_bin"])
    assert_rc_ok(proc)
    assert not sentinel.exists()
