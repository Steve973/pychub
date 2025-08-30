import zipfile
from pathlib import Path

import pytest

from tests.integration._asserts import assert_rc_ok, assert_rc_fail
from tests.integration.conftest import run_build_cli, run_runtime_cli


def _write_py(python_bin: Path, path, body):
    path.write_text(f"#!{python_bin}\n" + body)
    path.chmod(0o755)
    return path


@pytest.mark.integration
@pytest.mark.parametrize(
    "flags",
    [
        [],
        ["--verbose"],
        ["--quiet"],
        ["--exec"],
        ["--exec", "--verbose"],
        ["--no-scripts"],
        ["--no-post-scripts"],
        ["--no-pre-scripts"]
    ],
)
def test_post_install_scripts_respect_flags(test_env, tmp_path, flags):
    sentinel_post = tmp_path / "post_ok.txt"
    script_post = _write_py(test_env["python_bin"], tmp_path / "post_ok.py", f'open(r"{sentinel_post}", "w").write("ok")\n')
    sentinel_pre = tmp_path / "pre_ok.txt"
    script_pre = _write_py(test_env["python_bin"], tmp_path / "pre_ok.py", f'open(r"{sentinel_pre}", "w").write("ok")\n')

    proc, chub = run_build_cli(test_env["wheel_path"], tmp_path, test_env, scripts_post=[str(script_post)], scripts_pre=[str(script_pre)])
    assert_rc_ok(proc)

    proc = run_runtime_cli(chub, [*flags], test_env["python_bin"])
    assert_rc_ok(proc)

    if "--no-scripts" in flags or "--exec" in flags:
        assert not sentinel_post.exists()
        assert not sentinel_pre.exists()
    elif "--no-pre-scripts" in flags:
        assert sentinel_post.exists()
        assert not sentinel_pre.exists()
    elif "--no-post-scripts" in flags:
        assert sentinel_pre.exists()
        assert not sentinel_post.exists()
    else:
        assert sentinel_post.exists()
        assert sentinel_pre.exists()


@pytest.mark.integration
@pytest.mark.parametrize(
    "flags",
    [
        [],
        ["--run"],
        ["--quiet"],
        ["--verbose"]
    ])
def test_post_install_script_failure_propagates_rc(test_env, tmp_path, flags):
    script = _write_py(test_env["python_bin"], tmp_path / "post_fail.py", "import sys; sys.exit(17)\n")

    proc, chub = run_build_cli(test_env["wheel_path"], tmp_path, test_env, scripts_post=[str(script)])
    assert_rc_ok(proc)

    proc = run_runtime_cli(chub, [*flags], test_env["python_bin"])
    assert_rc_fail(proc, code=17)


@pytest.mark.integration
def test_missing_post_script_warns_and_continues(test_env, tmp_path):
    ok = _write_py(test_env["python_bin"], tmp_path / "post_ok.py", "print('ok')\n")
    missing = _write_py(test_env["python_bin"], tmp_path / "post_del.py", "print('should not run')\n")

    bproc, chub = run_build_cli(test_env["wheel_path"], tmp_path, test_env, scripts_post=[str(ok), str(missing)])
    assert_rc_ok(bproc)

    new_zip = tmp_path / "mutated.chub"
    with zipfile.ZipFile(chub) as src, zipfile.ZipFile(new_zip, "w", zipfile.ZIP_DEFLATED) as dst:
        for info in src.infolist():
            if info.filename.endswith(missing.name):
                continue
            data = src.read(info.filename)
            dst.writestr(info, data)

    proc = run_runtime_cli(new_zip, [], test_env["python_bin"])
    assert_rc_ok(proc)
    blob = (proc.stdout or "") + (proc.stderr or "")
    assert "post-install script not found" in blob


@pytest.mark.integration
@pytest.mark.parametrize(
    "flags",
    [
        [],
        ["--run"],
        ["--quiet"],
        ["--verbose"]
    ])
def test_multiple_post_scripts_both_run(test_env, tmp_path, flags):
    s1 = tmp_path / "s1.txt"
    s2 = tmp_path / "s2.txt"
    a = _write_py(test_env["python_bin"], tmp_path / "01_a.py", f'open(r"{s1}", "w").write("a")\n')
    b = _write_py(test_env["python_bin"], tmp_path / "02_b.py", f'open(r"{s2}", "w").write("b")\n')

    proc, chub = run_build_cli(test_env["wheel_path"], tmp_path, test_env, scripts_post=[str(a), str(b)])
    assert_rc_ok(proc)

    proc = run_runtime_cli(chub, [*flags], test_env["python_bin"])
    assert_rc_ok(proc)
    assert s1.exists()
    assert s2.exists()
