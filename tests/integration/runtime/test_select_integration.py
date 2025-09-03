import pytest
import pychubby.runtime.rt_options_processor as op

from tests.integration._asserts import assert_rc_ok, assert_rc_fail
from tests.integration.conftest import run_build_cli, run_runtime_cli


# ------------ helpers (derived from options_processor) ---------------------

def _parse_arg_shapes(commands):
    """Return (required_arg, optional_arg) sets based on COMMANDS specs."""
    req, opt = set(), set()
    for spec in commands:
        name, *rest = spec.split()
        if not rest:
            continue
        tail = " ".join(rest)
        if tail.startswith("[") and tail.endswith("]"):
            opt.add(name)
        else:
            req.add(name)
    return req, opt


_REQARG, _OPTARG = _parse_arg_shapes(op.COMMANDS)

# conservative CLI argv builder using map-derived shapes
def _argv_for(opt):
    flag = f"--{opt}"
    if opt in _REQARG:
        return [flag, "vdir" if opt == "venv" else "value"]
    # optional args default to omitted value (e.g., --run uses baked entrypoint)
    return [flag]


def _incompat_pairs():
    """Unique unordered incompatible pairs, excluding 'help' which argparse handles before our validator."""
    seen, pairs = set(), []
    for a, bs in op.INCOMPATIBLE_OPTIONS.items():
        if a == "help":
            continue
        for b in bs:
            if b == "help":
                continue
            key = tuple(sorted((a, b)))
            if key in seen:
                continue
            seen.add(key)
            pairs.append((a, b))
    return pairs


def _compat_pairs(limit_per_anchor=2):
    """Sample a few known-good compatible pairs (skip print-and-exit style anchors)."""
    skip = {"help", "info", "list", "show-scripts", "version"}
    pairs = []
    for a, bs in op.COMPATIBLE_OPTIONS.items():
        if a in skip:
            continue
        take = 0
        for b in bs:
            if b in skip or a == b:
                continue
            pairs.append((a, b))
            take += 1
            if take >= limit_per_anchor:
                break
    return pairs


def _blob(proc):
    return ((proc.stdout or "") + (proc.stderr or "")).lower()


# ------------ shared build (avoid rebuilding per-case) ---------------------

@pytest.fixture(scope="session")
def built_chub(test_env, tmp_path_factory):
    tmp = tmp_path_factory.mktemp("rt")
    proc, chub = run_build_cli(test_env["wheel_path"], tmp, test_env, entrypoint="test_pkg.greet:main")
    assert_rc_ok(proc)
    return chub


# ------------------------------- tests -------------------------------------

@pytest.mark.integration
@pytest.mark.parametrize("a,b", _incompat_pairs())
def test_every_incompatible_pair_fails(built_chub, test_env, a, b):
    args = _argv_for(a) + _argv_for(b)
    proc = run_runtime_cli(built_chub, args, test_env["python_bin"])
    assert_rc_fail(proc)


@pytest.mark.integration
@pytest.mark.parametrize("a,b", _compat_pairs())
def test_sample_compatible_pairs_succeed(built_chub, test_env, a, b):
    args = _argv_for(a) + _argv_for(b)
    proc = run_runtime_cli(built_chub, args, test_env["python_bin"])
    assert_rc_ok(proc)


@pytest.mark.integration
def test_venv_requires_dir_value(built_chub, test_env):
    # --venv is required-arg per COMMANDS → calling without value should fail
    proc = run_runtime_cli(built_chub, ["--venv"], test_env["python_bin"])
    assert_rc_fail(proc)


@pytest.mark.integration
@pytest.mark.parametrize("args", [
    ["--unpack"],              # optional DIR missing → ok
    ["--unpack", "udir"]       # optional DIR provided → ok
])
def test_unpack_optional_dir_succeeds(built_chub, test_env, args):
    proc = run_runtime_cli(built_chub, args, test_env["python_bin"])
    assert_rc_ok(proc)


@pytest.mark.integration
@pytest.mark.parametrize("args", [
    ["--run"],                 # baked entrypoint
    ["--run", "test_pkg.greet:main"]
])
def test_run_paths_succeed(built_chub, test_env, args):
    proc = run_runtime_cli(built_chub, args, test_env["python_bin"])
    assert_rc_ok(proc)


@pytest.mark.integration
def test_exec_without_entrypoint_uses_baked(built_chub, test_env):
    proc = run_runtime_cli(built_chub, ["--exec"], test_env["python_bin"])
    assert_rc_ok(proc)
