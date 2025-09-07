import pytest

from tests.integration.conftest import run_build_cli, get_chub_contents


@pytest.mark.integration
def test_basic_build(test_env, tmp_path):
    result, chub_path = run_build_cli(test_env["wheel_path"], tmp_path, test_env)
    assert result.returncode == 0, result.stderr
    assert chub_path.exists()

    names, cfg = get_chub_contents(chub_path)
    assert any(p.endswith(".whl") for p in names)
    assert any(p.endswith("__main__.py") for p in names)
    assert cfg.name == "test-pkg"


@pytest.mark.integration
def test_entrypoint_build(test_env, tmp_path):
    result, chub_path = run_build_cli(test_env["wheel_path"], tmp_path, test_env, entrypoint="test_pkg.greet:main")
    assert result.returncode == 0, result.stderr

    _, cfg = get_chub_contents(chub_path)
    assert cfg.entrypoint == "test_pkg.greet:main"


@pytest.mark.integration
def test_invalid_entrypoint_format(test_env, tmp_path):
    # Invalid: contains a space; validator requires a single token
    result, chub_path = run_build_cli(test_env["wheel_path"], tmp_path, test_env, entrypoint="bad entrypoint")
    assert result.returncode != 0
    assert "entrypoint" in (result.stderr or "").lower()
    assert not chub_path.exists()


@pytest.mark.integration
def test_metadata_entry(test_env, tmp_path):
    result, chub_path = run_build_cli(test_env["wheel_path"], tmp_path, test_env, metadata={"author": "steve", "tags": ["foo", "bar"]})
    assert result.returncode == 0, result.stderr

    _, cfg = get_chub_contents(chub_path)
    meta = cfg.metadata

    assert meta.get("author") == "steve"
