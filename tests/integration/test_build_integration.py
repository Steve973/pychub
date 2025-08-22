import zipfile

import pytest
import yaml

from tests.integration.conftest import run_build_cli


def get_chub_contents(chub_path):
    with zipfile.ZipFile(chub_path, "r") as zf:
        names = zf.namelist()
        chubconfig = None
        for name in names:
            if name.endswith(".chubconfig"):
                with zf.open(name) as f:
                    chubconfig = list(yaml.safe_load_all(f.read()))
        return names, chubconfig


@pytest.mark.integration
def test_basic_build(test_env, tmp_path):
    result, chub_path = run_build_cli(test_env["wheel_path"], tmp_path, test_env)
    assert result.returncode == 0, result.stderr
    assert chub_path.exists()
    names, config = get_chub_contents(chub_path)
    assert any(p.endswith(".whl") for p in names)
    assert "__main__.py" in names
    assert config and config[0]["name"] == "test-pkg"


@pytest.mark.integration
def test_entrypoint_build(test_env, tmp_path):
    result, chub_path = run_build_cli(
        test_env["wheel_path"],
        tmp_path,
        test_env,
        entrypoint="test_pkg.greet:main"
    )
    assert result.returncode == 0, result.stderr
    _, config = get_chub_contents(chub_path)
    assert config[0]["entrypoint"] == "test_pkg.greet:main"


@pytest.mark.integration
def test_invalid_entrypoint_format(test_env, tmp_path):
    result, _ = run_build_cli(
        test_env["wheel_path"],
        tmp_path,
        test_env,
        entrypoint="badentrypoint"
    )
    assert result.returncode != 0
    assert "Invalid entrypoint format" in result.stderr


@pytest.mark.integration
def test_metadata_entry(test_env, tmp_path):
    result, chub_path = run_build_cli(
        test_env["wheel_path"],
        tmp_path,
        test_env,
        metadata={"author": "steve", "tags": "foo,bar"}
    )
    assert result.returncode == 0
    _, config = get_chub_contents(chub_path)
    assert config[0]["metadata"] == {"author": "steve", "tags": ["foo", "bar"]}
