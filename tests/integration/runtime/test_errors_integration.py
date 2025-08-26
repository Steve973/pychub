import pytest
from tests.integration._asserts import assert_rc_ok
from tests.integration.conftest import run_build_cli, run_runtime_cli


@pytest.mark.integration
def test_invalid_entrypoint_format_fails(test_env, tmp_path):
    proc, chub = run_build_cli(
        test_env["wheel_path"], tmp_path, test_env,
        entrypoint="test_pkg.greet:main")
    assert_rc_ok(proc)

    proc = run_runtime_cli(
        chub, ["--run", "badformat"], test_env["python_bin"])
    assert proc.returncode != 0
    blob = (proc.stdout + proc.stderr).lower()
    assert "entrypoint" in blob or "format" in blob


@pytest.mark.integration
def test_missing_function_in_entrypoint_fails(test_env, tmp_path):
    proc, chub = run_build_cli(
        test_env["wheel_path"], tmp_path, test_env,
        entrypoint="test_pkg.greet:main")
    assert_rc_ok(proc)

    proc = run_runtime_cli(
        chub, ["--run", "test_pkg.greet:nope"],
        test_env["python_bin"])
    assert proc.returncode != 0
    blob = (proc.stdout + proc.stderr).lower()
    assert "nope" in blob or "attribute" in blob
