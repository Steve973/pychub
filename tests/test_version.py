import sys

import pytest

from pychubby.runtime.actions import version


@pytest.fixture
def fake_wheel():
    class Wheel:
        def __init__(self, name):
            self.name = name
    return Wheel


def test_show_version_with_installed_package(monkeypatch, capsys, fake_wheel, tmp_path):
    monkeypatch.setattr(version.im, "version", lambda pkg: "1.2.3")
    monkeypatch.setattr(version, "discover_wheels", lambda libs_dir, only=None: [fake_wheel("foo.whl"), fake_wheel("bar.whl")])

    version.show_version(tmp_path)

    out = capsys.readouterr().out
    assert f"Python: {sys.version.split()[0]}" in out
    assert "pychubby: 1.2.3" in out
    assert "Bundled wheels:" in out
    assert "  - foo.whl" in out
    assert "  - bar.whl" in out


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
