import shutil
from pathlib import Path

from tests.integration._asserts import assert_rc_ok
from tests.integration.conftest import run_build_cli, get_chub_contents


def test_build_uses_chubproject_toml(test_env, tmp_path):
    """Verify valid_chubproject.toml alone is enough to build a chub."""
    test_proj = test_env["test_pkg_dir"]
    wheel = test_env["wheel_path"]
    chubproject_location = Path(test_proj / "valid_chubproject.toml").resolve()

    result, chub = run_build_cli(wheel, tmp_path, test_env, chubproject=str(chubproject_location))

    assert_rc_ok(result)
    assert chub.exists()

    names, cfg = get_chub_contents(chub)
    assert cfg.metadata.get("maintainer") == "you@example.com"
    assert "libs/test_pkg-0.1.0-py3-none-any.whl" in names


def test_cli_overrides_toml_metadata(test_env, tmp_path):
    """CLI metadata should override valid_chubproject.toml values."""
    test_proj = test_env["test_pkg_dir"]
    wheel = test_env["wheel_path"]

    shutil.copy(test_proj / "valid_chubproject.toml", tmp_path)

    override_meta = {"author": "Overridden via CLI"}
    result, chub = run_build_cli(wheel, tmp_path, test_env, metadata=override_meta)

    assert_rc_ok(result)
    _, cfg = get_chub_contents(chub)
    assert cfg.metadata.get("author") == "Overridden via CLI"


def test_scripts_are_pulled_from_toml(test_env, tmp_path):
    """Ensure script files listed in valid_chubproject.toml are bundled correctly."""
    test_proj = test_env["test_pkg_dir"]
    wheel = test_env["wheel_path"]
    chubproject_location = Path(test_proj / "valid_chubproject.toml").resolve()

    result, chub = run_build_cli(wheel, tmp_path, test_env, chubproject=str(chubproject_location))

    assert_rc_ok(result)
    names, _ = get_chub_contents(chub)
    for name in names:
        print(f"name: {name}")

    assert any("_test_proj_scripts_pre_check.sh" in name for name in names)
    assert any("_test_proj_scripts_post_install.sh" in name for name in names)
    assert any("includes/conf/test.cfg" in name for name in names)
    assert any("includes/docs/README.md" in name for name in names)
    assert any("includes/etc/other.txt" in name for name in names)
    assert any("includes/test.txt" in name for name in names)
