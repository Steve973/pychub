import pytest
from tests.integration._asserts import assert_rc_ok, assert_in_stdout
from tests.integration.conftest import run_build_cli, run_runtime_cli


@pytest.mark.integration
def test_list_shows_bundled_wheels(test_env, tmp_path):
    proc, chub = run_build_cli(test_env["wheel_path"], tmp_path, test_env)
    assert_rc_ok(proc)

    proc = run_runtime_cli(chub, ["--list"], test_env["python_bin"])
    assert_rc_ok(proc)
    assert_in_stdout(proc, "test_pkg")


@pytest.mark.integration
def test_version_reports_components(test_env, tmp_path):
    proc, chub = run_build_cli(
        test_env["wheel_path"], tmp_path, test_env)
    assert_rc_ok(proc)

    proc = run_runtime_cli(chub, ["--version"], test_env["python_bin"])
    assert_rc_ok(proc)
    # keep loose: wording may evolve
    assert_in_stdout(proc, "python")
    assert_in_stdout(proc, "pychubby")


@pytest.mark.integration
def test_help_shows_usage(test_env, tmp_path):
    proc, chub = run_build_cli(test_env["wheel_path"], tmp_path, test_env)
    assert_rc_ok(proc)

    proc = run_runtime_cli(chub, ["--help"], test_env["python_bin"])
    assert_rc_ok(proc)
    assert_in_stdout(proc, "usage")


@pytest.mark.integration
def test_quiet_minimizes_and_quiet_wins_over_verbose(test_env, tmp_path):
    proc, chub = run_build_cli(test_env["wheel_path"], tmp_path, test_env)
    assert_rc_ok(proc)

    loud = run_runtime_cli(chub, ["--list", "--verbose"], test_env["python_bin"])
    quiet = run_runtime_cli(chub, ["--list", "--verbose", "--quiet"], test_env["python_bin"])
    assert_rc_ok(loud)
    assert_rc_ok(quiet)
    assert len(quiet.stdout) <= len(loud.stdout)
