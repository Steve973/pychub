import pytest

from tests.integration._asserts import assert_rc_ok, assert_in_stdout
from tests.integration.conftest import run_build_cli, run_runtime_cli


@pytest.mark.parametrize(
    "args,expect_ok,expect_substrings",
    [
        (["--run"], True, ["hello"]),
        (["--run", "test_pkg.greet:main"], True, ["hello"]),
        (["--exec"], True, ["hello"]),
    ])
def test_run_exec_matrix(test_env, tmp_path, args, expect_ok, expect_substrings):
    proc, chub = run_build_cli(test_env["wheel_path"], tmp_path, test_env, entrypoint="test_pkg.greet:main")
    assert_rc_ok(proc)
    proc = run_runtime_cli(chub, args, test_env["python_bin"])
    assert_rc_ok(proc)
    for s in expect_substrings:
        assert_in_stdout(proc, s)
