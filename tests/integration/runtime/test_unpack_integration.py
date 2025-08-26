from pathlib import Path
import pytest
from tests.integration._asserts import assert_rc_ok
from tests.integration.conftest import run_build_cli, run_runtime_cli


def _wheel_prefix(wheel_path: Path) -> str:
    # "dist-1.2.3-..." → "dist-"
    name = wheel_path.name
    return name.split("-")[0] + "-"

@pytest.mark.integration
def test_unpack_dir_basic(test_env, tmp_path):
    proc, chub = run_build_cli(test_env["wheel_path"], tmp_path, test_env)
    assert_rc_ok(proc)

    out_dir = tmp_path / "unpack"
    proc = run_runtime_cli(chub, ["--unpack", str(out_dir)], test_env["python_bin"])
    assert_rc_ok(proc)

    assert out_dir.exists()
    assert any(p.suffix == ".whl" for p in out_dir.iterdir())


@pytest.mark.integration
def test_unpack_dry_run_no_files_created(test_env, tmp_path):
    proc, chub = run_build_cli(test_env["wheel_path"], tmp_path, test_env)
    assert_rc_ok(proc)

    out_dir = tmp_path / "unpack_dry"
    proc = run_runtime_cli(
        chub, ["--dry-run", "--unpack", str(out_dir)],
        test_env["python_bin"])
    assert_rc_ok(proc)
    assert not out_dir.exists() or not any(out_dir.iterdir())


@pytest.mark.integration
def test_unpack_only_variants_respect_selection(test_env, tmp_path):
    proc, chub = run_build_cli(test_env["wheel_path"], tmp_path, test_env)
    assert_rc_ok(proc)

    out_dir = tmp_path / "sel_only"
    main_prefix = _wheel_prefix(test_env["wheel_path"])

    # only main
    proc = run_runtime_cli(
        chub, ["--unpack", str(out_dir), "--only", main_prefix[:-1]],
        test_env["python_bin"])
    assert_rc_ok(proc)
    names = [p.name for p in out_dir.iterdir()]
    assert any(n.startswith(main_prefix) for n in names)

    # only-deps should NOT include main wheel
    out_dir2 = tmp_path / "sel_only_deps"
    proc = run_runtime_cli(
        chub, ["--unpack", str(out_dir2), "--only-deps"],
        test_env["python_bin"])
    assert_rc_ok(proc)
    if out_dir2.exists() and any(out_dir2.iterdir()):
        assert all(not p.name.startswith(main_prefix)
                   for p in out_dir2.iterdir())


@pytest.mark.integration
def test_unpack_no_deps_skips_dependencies(test_env, tmp_path):
    proc, chub = run_build_cli(test_env["wheel_path"], tmp_path, test_env)
    assert_rc_ok(proc)

    out_dir = tmp_path / "no_deps"
    main_prefix = _wheel_prefix(test_env["wheel_path"])

    proc = run_runtime_cli(
        chub, ["--unpack", str(out_dir), "--no-deps"],
        test_env["python_bin"])
    assert_rc_ok(proc)

    names = [p.name for p in out_dir.iterdir()]
    assert any(n.startswith(main_prefix) for n in names)
    # if deps exist, ensure none slipped in
    assert all(n.startswith(main_prefix) for n in names)
