import sys
from pathlib import Path
import pytest

from pychubby.runtime.actions import version


@pytest.fixture
def fake_wheel():
    class Wheel:
        def __init__(self, name):
            self.name = name
    return Wheel


def test_show_version_with_installed_package(monkeypatch, capsys, fake_wheel, tmp_path):
    called = {}

    def fake_im_version(pkg):
        called["pkg"] = pkg
        return "1.2.3"

    monkeypatch.setattr(version.im, "version", fake_im_version)
    monkeypatch.setattr(
        version, "discover_wheels", lambda libs_dir, only=None: [fake_wheel("foo.whl"), fake_wheel("bar.whl")]
    )

    version.show_version(tmp_path)

    out = capsys.readouterr().out
    assert f"Python: {sys.version.split()[0]}" in out
    assert "pychubby: 1.2.3" in out
    assert "Bundled wheels:" in out
    assert "  - foo.whl" in out and "  - bar.whl" in out
    assert called["pkg"] == "pychubby"  # ensure correct dist is queried


def test_show_version_when_pychubby_not_installed(monkeypatch, capsys, tmp_path):
    def raise_not_found(pkg):
        raise version.im.PackageNotFoundError

    monkeypatch.setattr(version.im, "version", raise_not_found)
    monkeypatch.setattr(version, "discover_wheels", lambda libs_dir, only=None: [])

    version.show_version(tmp_path)

    out = capsys.readouterr().out
    assert "pychubby: (not installed)" in out
    assert "Bundled wheels:" in out
    assert "  (none)" in out


def test_show_version_with_none_from_discover(monkeypatch, capsys, tmp_path):
    monkeypatch.setattr(version.im, "version", lambda pkg: "9.9.9")
    monkeypatch.setattr(version, "discover_wheels", lambda libs_dir, only=None: None)

    version.show_version(tmp_path)

    out = capsys.readouterr().out
    assert "pychubby: 9.9.9" in out
    assert "Bundled wheels:" in out
    assert "  (none)" in out


def test_show_version_preserves_print_order(monkeypatch, capsys, tmp_path):
    monkeypatch.setattr(version.im, "version", lambda pkg: "0.0.1")
    # Provide Path-like items with names in unsorted order; function should not reorder
    items = [Path("z.whl"), Path("a.whl"), Path("m.whl")]
    monkeypatch.setattr(version, "discover_wheels", lambda libs_dir, only=None: items)

    version.show_version(tmp_path)

    lines = [l for l in capsys.readouterr().out.splitlines() if l.startswith("  - ")]
    assert lines == ["  - z.whl", "  - a.whl", "  - m.whl"]


def test_show_version_handles_unicode_names(monkeypatch, capsys, fake_wheel, tmp_path):
    monkeypatch.setattr(version.im, "version", lambda pkg: "2.0.0")
    wheels = [fake_wheel("naïve-β.whl"), fake_wheel("数据.whl")]  # unicode
    monkeypatch.setattr(version, "discover_wheels", lambda libs_dir, only=None: wheels)

    version.show_version(tmp_path)

    out = capsys.readouterr().out
    assert "  - naïve-β.whl" in out
    assert "  - 数据.whl" in out


def test_show_version_propagates_unexpected_errors(monkeypatch, tmp_path):
    # Any error other than PackageNotFoundError should bubble up
    monkeypatch.setattr(version.im, "version", lambda pkg: (_ for _ in ()).throw(RuntimeError("boom")))
    monkeypatch.setattr(version, "discover_wheels", lambda *a, **k: [])

    with pytest.raises(RuntimeError):
        version.show_version(tmp_path)
