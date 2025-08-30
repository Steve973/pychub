import pytest

from tests.integration._asserts import assert_rc_fail
from tests.integration._factories import (
    mk_chub_with_entrypoint,
)
from tests.integration.conftest import run_runtime_cli

# Matrices of option combinations to exercise compatible flags
# Keep each list small-but-representative; we'll expand with more tests later.
RUN_FLAG_SETS = [
    [],
    ["--dry-run"],
    ["--quiet"],
    ["--verbose"],
    ["--no-scripts"],
    ["--no-pre-scripts"],
    ["--no-post-scripts"],
    ["--exec"],
    ["--exec", "--verbose"],
    ["--exec", "--no-scripts"],
    ["--exec", "--dry-run"],
]


@pytest.mark.integration
@pytest.mark.parametrize("flags", RUN_FLAG_SETS)
def test_missing_console_script_fails(test_env, tmp_path, flags):
    """`--run` with console-script form should fail if the script doesn't exist.

    Spec: runtime accepts two forms — `module:function` and `console-script-name`.
    Here we use a definitely-missing console script to trigger an error.
    """
    chub = mk_chub_with_entrypoint(tmp_path, test_env, entry="test_pkg.greet:main")

    # Impossible console script name; keep it simple (no colon => console script path)
    bad_script = "__definitely_not_a_real_console_script__"
    if not "--dry-run" in flags:
        proc = run_runtime_cli(chub, [*flags, "--run", bad_script], test_env["python_bin"])
        # See runtime code: errors here come from spawnvp/spawnv; just assert non-zero
        assert_rc_fail(proc)


@pytest.mark.integration
@pytest.mark.parametrize("flags", RUN_FLAG_SETS)
def test_missing_function_in_module_form_fails(test_env, tmp_path, flags):
    """`--run module:function` should fail if the function attribute is missing.

    We assert non-zero and tolerate platform-specific wording by checking for
    either the missing attribute name or the word 'attribute' in stderr/stdout.
    """
    chub = mk_chub_with_entrypoint(tmp_path, test_env, entry="test_pkg.greet:main")

    target = "test_pkg.greet:nope"
    proc = run_runtime_cli(chub, [*flags, "--run", target], test_env["python_bin"])

    if not "--dry-run" in flags:
        assert_rc_fail(proc)
        blob = (proc.stdout or "") + (proc.stderr or "")
        assert ("nope" in blob) or ("attribute" in blob.lower())
