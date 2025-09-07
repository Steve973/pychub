from pychub.package.chubproject import load_chubproject
from tests.integration._asserts import assert_rc_ok
from tests.integration.conftest import run_build_cli


def test_chubproject_save_roundtrip(test_env, tmp_path):
    """Verify that --chubproject-save writes a valid file, and it can be reloaded cleanly."""
    test_proj = test_env["test_pkg_dir"]
    wheel = test_env["wheel_path"]
    out_path = tmp_path / "saved_config.toml"

    result, _ = run_build_cli(
        wheel,
        tmp_path,
        test_env,
        chubproject_save=out_path,
        metadata={"author": "steve", "tags": ["foo", "bar"]},
        includes=[f"{test_proj}/includes/README.md::altname"],
        scripts_post=[f"{test_proj}/scripts/post_install.sh"],
    )

    assert_rc_ok(result)
    assert out_path.exists(), "Saved chubproject.toml not found"

    # Reload the saved project
    reloaded = load_chubproject(out_path)
    assert reloaded.metadata.get("author") == "steve"
    assert reloaded.metadata.get("tags") == ["foo", "bar"]
    assert any("altname" in i.as_string() for i in reloaded.includes)
    assert any("post_install.sh" in str(p) for p in (reloaded.scripts.post or None))
