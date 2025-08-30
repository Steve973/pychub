import pytest

from tests.integration._asserts import (
    assert_rc_ok,
    assert_in_stdout,
    assert_quiet,
)
from tests.integration._factories import (
    mk_chub_basic,
    mk_chub_with_entrypoint,
)
from tests.integration.conftest import run_runtime_cli


# Compact but representative flag matrices for info actions.
# These flags are compatible with --list/--version/--help and allow us to
# exercise quiet/verbose and exec/no-exec paths.
FLAG_SETS = [
    [],
    ["--quiet"],
    ["--verbose"],
]


@pytest.mark.integration
@pytest.mark.parametrize("flags", FLAG_SETS)
def test_list_shows_bundled_wheels(test_env, tmp_path, flags):
    chub = mk_chub_basic(tmp_path, test_env)

    proc = run_runtime_cli(chub, [*flags, "--list"], test_env["python_bin"])
    assert_rc_ok(proc)
    assert_in_stdout(proc, "test_pkg")


@pytest.mark.integration
@pytest.mark.parametrize("flags", FLAG_SETS)
def test_version_prints_python_and_pychubby(test_env, tmp_path, flags):
    chub = mk_chub_with_entrypoint(tmp_path, test_env)

    proc = run_runtime_cli(chub, [*flags, "--version"], test_env["python_bin"])
    assert_rc_ok(proc)
    # Keep expectations loose; exact version string is environment-specific
    assert_in_stdout(proc, "python", "pychubby")


@pytest.mark.integration
@pytest.mark.parametrize("flags", FLAG_SETS)
def test_help_prints_usage_and_succeeds(test_env, tmp_path, flags):
    chub = mk_chub_basic(tmp_path, test_env)

    proc = run_runtime_cli(chub, [*flags, "--help"], test_env["python_bin"])
    assert_rc_ok(proc)
    assert_in_stdout(proc, "usage")


@pytest.mark.integration
def test_quiet_minimizes_and_quiet_wins_over_verbose(test_env, tmp_path):
    chub = mk_chub_basic(tmp_path, test_env)

    loud = run_runtime_cli(chub, ["--list", "--verbose"], test_env["python_bin"])
    quiet = run_runtime_cli(chub, ["--list", "--verbose", "--quiet"], test_env["python_bin"])
    assert_rc_ok(loud)
    assert_rc_ok(quiet)
    # Heuristic: quiet output length should be <= verbose output length
    assert len((quiet.stdout or "")) <= len((loud.stdout or ""))
    # And should satisfy the shared quietness contract
    assert_quiet(quiet)
