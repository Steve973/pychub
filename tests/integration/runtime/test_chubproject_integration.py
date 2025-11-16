
from pathlib import Path

import pytest

from pychub.helper.toml_utils import load_toml_text
from pychub.model.chubproject_model import ChubProject, ChubProjectError
from tests.integration._asserts import assert_rc_ok
from tests.integration.conftest import run_build_cli


@pytest.fixture
def saved_chubproject_file(test_env, tmp_path):
    """Run a real build to generate a saved chubproject TOML file."""
    test_proj = test_env["test_pkg_dir"]
    wheel = test_env["wheel_path"]
    out_path = tmp_path / "test_chubproject_save.toml"

    result, _ = run_build_cli(
        wheel,
        tmp_path,
        test_env,
        chubproject_save=out_path,
        metadata={"author": "steve", "tags": ["foo", "bar"]},
        includes=[f"{test_proj}/includes/README.md::altname"],
        scripts_post=[f"{test_proj}/scripts/post_install.sh"],
        scripts_pre=[f"{test_proj}/scripts/pre_check.sh"],
        verbose=True,
    )

    assert_rc_ok(result)
    assert out_path.exists()
    return {"path": out_path, "wheel": wheel, "proj_dir": test_proj}


@pytest.fixture
def loaded_project(saved_chubproject_file):
    return ChubProject.load_file(saved_chubproject_file["path"])


def test_wheel_path_matches_input(loaded_project, saved_chubproject_file):
    assert loaded_project.wheel == saved_chubproject_file["wheel"].as_posix()


def test_metadata_fields_roundtrip(loaded_project):
    assert loaded_project.metadata["author"] == "steve"
    assert loaded_project.metadata["tags"] == ["foo", "bar"]
    assert "__file__" in loaded_project.metadata


def test_includes_are_parsed_correctly(loaded_project):
    includes = loaded_project.includes
    assert any(i.dest == "altname" for i in includes)


def test_scripts_pre_and_post_are_populated(loaded_project):
    pre = loaded_project.scripts.pre or []
    post = loaded_project.scripts.post or []
    assert any("pre_check.sh" in s for s in pre)
    assert any("post_install.sh" in s for s in post)


def test_verbose_flag_is_preserved(loaded_project):
    assert loaded_project.verbose is True


def test_save_roundtrip_toml_equivalence(saved_chubproject_file, loaded_project, tmp_path):
    original_path = saved_chubproject_file["path"]
    second_path = tmp_path / "roundtrip.toml"

    ChubProject.save_file(loaded_project, second_path, overwrite=True)

    doc1 = load_toml_text(original_path.read_text("utf-8"))["tool"]["pychub"]["package"]
    doc2 = load_toml_text(second_path.read_text("utf-8"))["tool"]["pychub"]["package"]

    doc1["metadata"].pop("__file__", None)
    doc2["metadata"].pop("__file__", None)

    assert doc1 == doc2


def test_save_refuses_to_overwrite_existing_file(tmp_path):
    path = tmp_path / "existing.toml"
    path.write_text("dummy")

    with pytest.raises(Exception) as e:
        ChubProject.save_file(ChubProject.from_mapping({}), path)

    assert "Refusing to overwrite" in str(e.value)


def test_save_fails_if_no_writer(monkeypatch):
    import pychub.model.chubproject_model as chubproject_model
    monkeypatch.setattr(chubproject_model, "_TOML_WRITER", None)

    with pytest.raises(Exception) as e:
        ChubProject.save_file(ChubProject.from_mapping({}), Path("any.toml"))

    assert "Saving requires a TOML writer" in str(e.value)


def test_pyproject_valid_tool_package():
    doc = {
        "tool": {
            "pychub": {
                "package": {"wheel": "test.whl"}
            }
        }
    }
    result = ChubProject._select_package_table(doc, "pyproject.toml")
    assert result == {"wheel": "test.whl"}


def test_pyproject_explicitly_disabled(capfd):
    doc = {
        "tool": {
            "pychub": {
                "package": {"enabled": False}
            }
        }
    }
    result = ChubProject._select_package_table(doc, "pyproject.toml")
    assert result is None
    out = capfd.readouterr().out
    assert "enabled" in out and "skipping" in out


def test_pyproject_missing_package_table(capfd):
    doc = {
        "tool": {
            "pychub": {}
        }
    }
    result = ChubProject._select_package_table(doc, "pyproject.toml")
    assert result is None
    assert "not found" in capfd.readouterr().out


def test_chubproject_tool_table_exists():
    doc = {
        "tool": {
            "pychub": {
                "package": {"wheel": "wheel.whl"}
            }
        }
    }
    result = ChubProject._select_package_table(doc, "valid_chubproject.toml")
    assert result == {"wheel": "wheel.whl"}


def test_chubproject_pychub_package_root_level():
    doc = {
        "pychub": {
            "package": {"wheel": "wheel.whl"}
        }
    }
    result = ChubProject._select_package_table(doc, "valid_chubproject.toml")
    assert result == {"wheel": "wheel.whl"}


def test_chubproject_package_flat():
    doc = {
        "package": {"wheel": "pkg.whl"}
    }
    result = ChubProject._select_package_table(doc, "valid_chubproject.toml")
    assert result == {"wheel": "pkg.whl"}


def test_chubproject_flat_document_used_as_fallback(capfd):
    doc = {
        "wheel": "flat.whl",
        "entrypoint": "main:run"
    }
    result = ChubProject._select_package_table(doc, "valid_chubproject.toml")
    assert result == doc
    assert "flat table" in capfd.readouterr().out


def test_unrecognized_filename_is_skipped(capfd):
    doc = {"tool": {"pychub": {"package": {"wheel": "test.whl"}}}}
    result = ChubProject._select_package_table(doc, "weird_name.toml")
    assert result is None
    assert "unrecognized" in capfd.readouterr().out


@pytest.mark.parametrize("name,arg,expected", [
    ("pyproject.toml", None, "tool.pychub.package"),
    ("valid_chubproject.toml", None, "tool.pychub.package"),
    ("chubproject.build.toml", "flat", None),
    ("my-valid_chubproject.toml", "flat", None),
    ("my_chubproject.toml", "flat", None),
    ("my.valid_chubproject.toml", "flat", None),
    ("valid_chubproject.toml", "package", "package"),
    ("valid_chubproject.toml", "tool.pychub.package", "tool.pychub.package"),
    ("valid_chubproject.toml", "pychub.package", "pychub.package"),
])
def test_determine_table_path_valid(name, arg, expected):
    result = ChubProject.determine_table_path(Path(name), arg)
    assert result == expected


@pytest.mark.parametrize("name,arg", [
    ("build.toml", None),
    ("chub_proj.toml", None),
    ("notachubproject.toml", None),
    ("config.toml", "flat"),
    ("myproject.toml", "tool.pychub.package"),
    ("valid_chubproject.toml", "tool.pychub.packag"),  # typo
    ("valid_chubproject.toml", "pychub.package.extra"),  # too long
    ("valid_chubproject.toml", "packge"),  # misspelled
    ("valid_chubproject.toml", "pysub.package"),
])
def test_determine_table_path_invalid(name, arg):
    with pytest.raises(ValueError):
        ChubProject.determine_table_path(Path(name), arg)


@pytest.mark.parametrize("arg", [
    "packag", "pychub.packages", "tool.foo.package", "package.extra", "foo", "tool.pysub.package"
])
def test_invalid_table_args(arg):
    with pytest.raises(ValueError, match="Invalid table_arg"):
        ChubProject.determine_table_path(Path("valid_chubproject.toml"), arg)