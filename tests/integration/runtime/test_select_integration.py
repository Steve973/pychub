import pytest
from tests.integration._asserts import assert_rc_ok
from tests.integration.conftest import run_build_cli, run_runtime_cli


@pytest.mark.integration
@pytest.mark.parametrize("args", [
    ["--run", "--no-deps"],
    ["--exec", "--no-deps"],
    ["--run", "--only", "foo"],
    ["--exec", "--only", "foo"],
    ["--run", "--only-deps"],
    ["--exec", "--only-deps"],
])
def test_selection_modes_disable_run_and_exec(test_env, tmp_path, args):
    proc, chub = run_build_cli(
        test_env["wheel_path"], tmp_path, test_env,
        entrypoint="test_pkg.greet:main")
    assert_rc_ok(proc)

    proc = run_runtime_cli(chub, args, test_env["python_bin"])
    assert proc.returncode != 0
    blob = (proc.stdout + proc.stderr).lower()
    assert "disable" in blob or "not allowed" in blob or "conflict" in blob
