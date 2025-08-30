import pytest

from tests.integration._asserts import (
    assert_rc_ok,
    assert_rc_fail,
    assert_in_stdout,
    assert_quiet,
)
from tests.integration._factories import mk_chub_with_entrypoint
from tests.integration.conftest import run_runtime_cli


# Flag sets that should still execute the entrypoint and print "hello"
EXECUTE_FLAG_SETS = [
    [],
    ["--verbose"],
    ["--quiet"],
    ["--no-scripts"],
    ["--no-pre-scripts"],
    ["--no-post-scripts"],
    ["--exec"],
    ["--exec", "--verbose"],
    ["--exec", "--no-scripts"],
]

# Flag sets that affect the environment but should not break execution
AUX_FLAG_SETS = [
    ["--venv"],  # path provided at callsite
]


@pytest.mark.integration
@pytest.mark.parametrize("flags", EXECUTE_FLAG_SETS)
def test_run_with_baked_entrypoint_works(test_env, tmp_path, flags):
    chub = mk_chub_with_entrypoint(tmp_path, test_env, entry="test_pkg.greet:main")
    proc = run_runtime_cli(chub, [*flags, "--run"], test_env["python_bin"])
    assert_rc_ok(proc)
    assert_in_stdout(proc, "hello")


@pytest.mark.integration
@pytest.mark.parametrize("flags", EXECUTE_FLAG_SETS)
def test_run_with_explicit_entrypoint_works(test_env, tmp_path, flags):
    chub = mk_chub_with_entrypoint(tmp_path, test_env, entry="test_pkg.greet:main")
    proc = run_runtime_cli(chub, [*flags, "--run", "test_pkg.greet:main"], test_env["python_bin"])
    assert_rc_ok(proc)
    assert_in_stdout(proc, "hello")


@pytest.mark.integration
@pytest.mark.parametrize("flags", [["--verbose"], ["--quiet"], []])
def test_run_arg_passthrough_does_not_break(test_env, tmp_path, flags):
    chub = mk_chub_with_entrypoint(tmp_path, test_env, entry="test_pkg.greet:main")
    # Pass extra args after --; entrypoint may ignore them, but should not fail
    proc = run_runtime_cli(chub, [*flags, "--run", "test_pkg.greet:main", "--", "arg1", "arg2"], test_env["python_bin"])
    assert_rc_ok(proc)
    assert_in_stdout(proc, "hello")


@pytest.mark.integration
@pytest.mark.parametrize("flags", [["--quiet"], ["--verbose"]])
def test_quiet_wins_over_verbose_during_run(test_env, tmp_path, flags):
    chub = mk_chub_with_entrypoint(tmp_path, test_env, entry="test_pkg.greet:main")
    loud = run_runtime_cli(chub, ["--run", "test_pkg.greet:main", "--verbose"], test_env["python_bin"])
    quiet = run_runtime_cli(chub, ["--run", "test_pkg.greet:main", "--verbose", "--quiet"], test_env["python_bin"])
    assert_rc_ok(loud)
    assert_rc_ok(quiet)
    assert_in_stdout(quiet, "hello")
    assert_quiet(quiet)


@pytest.mark.integration
@pytest.mark.parametrize("venv_flag", ["--venv"])
def test_run_with_persistent_venv_path_works(test_env, tmp_path, venv_flag):
    chub = mk_chub_with_entrypoint(tmp_path, test_env, entry="test_pkg.greet:main")
    venv_dir = tmp_path / "runtime-venv"
    args = [venv_flag, str(venv_dir), "--run", "test_pkg.greet:main"]
    proc = run_runtime_cli(chub, args, test_env["python_bin"])
    assert_rc_ok(proc)
    assert_in_stdout(proc, "hello")


@pytest.mark.integration
def test_exec_without_run_uses_baked_entrypoint(test_env, tmp_path):
    chub = mk_chub_with_entrypoint(tmp_path, test_env, entry="test_pkg.greet:main")
    proc = run_runtime_cli(chub, ["--exec"], test_env["python_bin"])
    assert_rc_ok(proc)
    assert_in_stdout(proc, "hello")


@pytest.mark.integration
def test_baked_invalid_entrypoint_fails_at_runtime(test_env, tmp_path):
    chub = mk_chub_with_entrypoint(tmp_path, test_env, entry="test_pkg.greet:nope")
    proc = run_runtime_cli(chub, ["--run"], test_env["python_bin"])
    assert_rc_fail(proc)
    blob = (proc.stdout or "") + (proc.stderr or "")
    assert ("nope" in blob) or ("attribute" in blob.lower())
