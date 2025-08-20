import json

from pychubby.runtime.actions import chubconfig
from pychubby.runtime.constants import CHUBCONFIG_FILENAME


def test_load_chubconfig_returns_empty_if_missing(tmp_path):
    # CHUBCONFIG_FILENAME does not exist
    result = chubconfig.load_chubconfig(tmp_path)
    assert result == {}


def test_load_chubconfig_valid_json(tmp_path):
    data = {"entrypoint": "myplugin.cli:main"}
    config_path = tmp_path / CHUBCONFIG_FILENAME
    config_path.write_text(json.dumps(data), encoding="utf-8")

    result = chubconfig.load_chubconfig(tmp_path)
    assert result == data


def test_load_chubconfig_malformed_json_returns_empty(tmp_path, capsys):
    config_path = tmp_path / CHUBCONFIG_FILENAME
    config_path.write_text("{ bad: json }", encoding="utf-8")  # Invalid JSON

    result = chubconfig.load_chubconfig(tmp_path)
    assert result == {}

    captured = capsys.readouterr()
    assert "failed to parse" in captured.err


def test_load_chubconfig_empty_file(tmp_path, capsys):
    config_path = tmp_path / CHUBCONFIG_FILENAME
    config_path.write_text("", encoding="utf-8")

    result = chubconfig.load_chubconfig(tmp_path)
    assert result == {}

    captured = capsys.readouterr()
    assert "failed to parse" in captured.err


def test_load_chubconfig_file_is_directory(tmp_path, capsys):
    config_path = tmp_path / CHUBCONFIG_FILENAME
    config_path.mkdir()  # simulate misconfiguration

    result = chubconfig.load_chubconfig(tmp_path)
    assert result == {}

    captured = capsys.readouterr()
    assert "failed to parse" in captured.err
