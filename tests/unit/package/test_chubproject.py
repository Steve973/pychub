from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

import pytest

from pychub.package.chubproject import (
    ChubProjectError,
    load_chubproject,
    save_chubproject
)


# -------------------------------
# helpers
# -------------------------------

def _writer_available() -> bool:
    """
    Detect whether at least one TOML writer is installed.
    This mirrors the module's behavior (tomli_w | tomlkit | toml).
    """
    for name in ("tomli_w", "tomlkit", "toml"):
        try:
            __import__(name)
            return True
        except ModuleNotFoundError:
            continue
    return False


# -------------------------------
# load_chubproject
# -------------------------------

def test_load_happy_path(tmp_path: Path, monkeypatch):
    cfg_file = tmp_path / "chubproject.toml"
    cfg_file.write_text(
        """
        wheel = "dist/pkg-1.0.0.whl"
        verbose = true

        [metadata]
        tags = ["cli", "fast"]

        [scripts]
        pre = ["scripts/check.sh"]
        post = ["scripts/finish.sh"]
        """,
        encoding="utf-8")

    # Monkeypatch the function to avoid ZIP parsing
    monkeypatch.setattr(
        "pychub.model.chubproject_model.get_wheel_name_version",
        lambda path: ("fakepkg", "1.0.0"))

    data = load_chubproject(cfg_file)
    assert data.wheel == "dist/pkg-1.0.0.whl"
    assert data.verbose is True
    assert data.metadata["tags"] == ["cli", "fast"]
    # loader adds the absolute source path for convenience
    assert data.metadata["__file__"] == str(cfg_file.resolve())


def test_load_missing_file_raises(tmp_path: Path):
    missing = tmp_path / "nope.toml"
    with pytest.raises(ChubProjectError) as ei:
        load_chubproject(missing)
    assert "Project file not found" in str(ei.value)


# -------------------------------
# save_chubproject (writer required)
# -------------------------------

writer = pytest.mark.skipif(not _writer_available(), reason="No TOML writer (install tomli-w or tomlkit or toml)")

@writer
def test_save_roundtrip_basic_dict(tmp_path: Path, monkeypatch):
    target = tmp_path / "chubproject.toml"
    cfg: Dict[str, Any] = {
        "wheel": Path("dist/pkg-1.0.0.whl"),   # Path should be serialized to posix str
        "add_wheels": {"dist/extra.whl", "dist/another.whl"},  # set → sorted list
        "includes": ["README.md::docs", "conf.yaml"],
        "verbose": True,
        "metadata": {
            "maintainer": "me@example.com",
            "tags": ("cli", "fast"),  # tuple → list
            "custom": {"x": 1, "y": Path("Z.txt")},
        },
        "scripts": {
            "pre": [Path("scripts/check.sh")],
            "post": [],
        },
        "__file__": tmp_path / "something",  # must be stripped on save
    }

    # Monkeypatch the function to avoid ZIP parsing
    monkeypatch.setattr(
        "pychub.model.chubproject_model.get_wheel_name_version",
        lambda path: ("fakepkg", "1.0.0"))

    # save
    out = save_chubproject(cfg, path=target)
    assert out == target.resolve()
    assert target.is_file()

    # load and compare (structure, not textual formatting)
    data = load_chubproject(target)
    assert "__file__" in data.metadata
    assert data.metadata["__file__"] == str(target)  # loader injects it

    assert data.wheel == "dist/pkg-1.0.0.whl"
    # sets become sorted lists
    assert set(data.add_wheels) == {"dist/extra.whl", "dist/another.whl"}
    assert [inc.as_string() for inc in data.includes] == ["README.md::docs", "conf.yaml"]
    assert data.verbose is True

    meta = data.metadata
    assert meta["maintainer"] == "me@example.com"
    assert meta["tags"] == ["cli", "fast"]   # tuple coerced to list

    scripts = data.scripts
    assert scripts.pre == ["scripts/check.sh"]  # Path → posix str
    assert scripts.post == []

    # extra keys survive and Path is coerced to string
    custom = meta["custom"]
    assert custom == {"x": 1, "y": "Z.txt"}


@writer
def test_save_refuses_overwrite_without_flag(tmp_path: Path, monkeypatch, fake_dist_wheels):
    target = tmp_path / "chubproject.toml"
    target.write_text('title = "exists"', encoding="utf-8")

    # Monkeypatch the function to avoid ZIP parsing
    monkeypatch.setattr(
        "pychub.model.chubproject_model.get_wheel_name_version",
        lambda path: ("fakepkg", "1.0.0"))

    with pytest.raises(ChubProjectError):
        save_chubproject({"package": {}}, path=target, overwrite=False)


@writer
def test_save_allows_overwrite_with_flag(tmp_path: Path, monkeypatch):
    target = tmp_path / "chubproject.toml"
    target.write_text('title = "exists"', encoding="utf-8")

    # Monkeypatch the function to avoid ZIP parsing
    monkeypatch.setattr(
        "pychub.model.chubproject_model.get_wheel_name_version",
        lambda path: ("fakepkg", "1.0.0"))

    out = save_chubproject({"wheel": "dist/x.whl"}, path=target, overwrite=True)
    assert out == target.resolve()
    loaded = load_chubproject(target)
    assert loaded.wheel == "dist/x.whl"


@writer
def test_save_makes_parents(tmp_path: Path, monkeypatch, fake_dist_wheels):
    nested = tmp_path / "a" / "b" / "chubproject.toml"

    # Monkeypatch the function to avoid ZIP parsing
    monkeypatch.setattr(
        "pychub.model.chubproject_model.get_wheel_name_version",
        lambda path: ("fakepkg", "1.0.0"))

    out = save_chubproject({"build": {}}, path=nested, make_parents=True)
    assert out == nested.resolve()
    assert nested.is_file()


def test_save_raises_when_no_writer(monkeypatch, tmp_path: Path):
    # Force the module to believe no writer is available
    import pychub.package.chubproject as chp
    monkeypatch.setattr(chp, "_TOML_WRITER", None, raising=True)
    with pytest.raises(ChubProjectError) as ei:
        save_chubproject({"build": {}}, path=tmp_path / "x.toml", overwrite=True)
    msg = str(ei.value)
    assert "Saving requires a TOML writer" in msg
    assert "tomli-w" in msg or "tomlkit" in msg or "toml" in msg


def test_load_malformed_toml_raises(tmp_path: Path):
    """Test that malformed TOML raises ChubProjectError with original exception."""
    cfg_file = tmp_path / "chubproject.toml"
    # Write invalid TOML
    cfg_file.write_text(
        """
        [section
        missing = "closing bracket"
        """,
        encoding="utf-8")

    with pytest.raises(ChubProjectError) as ei:
        load_chubproject(cfg_file)
    assert "Failed to parse TOML" in str(ei.value)
    # Should chain the original exception
    assert ei.value.__cause__ is not None


@writer
def test_save_coerces_set_to_sorted_list(tmp_path: Path, monkeypatch):
    """Test that sets are coerced to sorted lists during save."""
    target = tmp_path / "chubproject.toml"

    monkeypatch.setattr(
        "pychub.model.chubproject_model.get_wheel_name_version",
        lambda path: ("fakepkg", "1.0.0"))

    cfg: dict[str, Any] = {
        "wheel": "dist/pkg-1.0.0.whl",
        "metadata": {"test_set": {"dist/zebra.whl", "dist/alpha.whl", "dist/middle.whl"}},
    }

    save_chubproject(cfg, path=target)

    # Read the raw TOML to verify sets were sorted during save
    content = target.read_text()
    assert '"dist/alpha.whl"' in content
    assert '"dist/middle.whl"' in content
    assert '"dist/zebra.whl"' in content
    # Just verify the set was converted to a list in TOML (array notation)
    assert "test_set = [" in content


@writer
def test_save_coerces_primitives_unchanged(tmp_path: Path, monkeypatch):
    """Test that primitive types pass through _coerce unchanged (covers final return x)."""
    target = tmp_path / "chubproject.toml"

    monkeypatch.setattr(
        "pychub.model.chubproject_model.get_wheel_name_version",
        lambda path: ("fakepkg", "1.0.0"))

    cfg: dict[str, Any] = {
        "wheel": "dist/pkg-1.0.0.whl",
        "metadata": {
            "count": 42,
            "enabled": True,
            "name": "test"
        },
    }

    save_chubproject(cfg, path=target)
    data = load_chubproject(target)

    assert data.metadata["count"] == 42
    assert data.metadata["enabled"] is True
    assert data.metadata["name"] == "test"