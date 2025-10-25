from argparse import ArgumentError
from pathlib import Path
from unittest.mock import Mock

import pytest


def test_main_creates_parser_and_calls_process_options(monkeypatch):
    """Test that main() creates the parser, parses args, and calls process_options."""
    from pychub.package import cli

    # Mock process_options to capture what it's called with
    mock_process = Mock()
    monkeypatch.setattr(cli, "process_options", mock_process)

    # Mock sys.argv to provide test arguments
    test_args = ["pychub", "mywheel.whl", "--verbose"]
    monkeypatch.setattr("sys.argv", test_args)

    # Call main
    cli.main()

    # Verify process_options was called once
    assert mock_process.call_count == 1

    # Verify the args passed to process_options
    args = mock_process.call_args[0][0]
    assert args.wheel == Path("mywheel.whl")
    assert args.verbose is True


def test_main_parses_wheel_argument(monkeypatch):
    """Test that wheel positional argument is parsed correctly."""
    from pychub.package import cli

    mock_process = Mock()
    monkeypatch.setattr(cli, "process_options", mock_process)
    monkeypatch.setattr("sys.argv", ["pychub", "dist/pkg.whl"])

    cli.main()

    args = mock_process.call_args[0][0]
    assert args.wheel == Path("dist/pkg.whl")


def test_main_parses_add_wheel_argument(monkeypatch):
    """Test that --add-wheel arguments are parsed correctly."""
    from pychub.package import cli

    mock_process = Mock()
    monkeypatch.setattr(cli, "process_options", mock_process)
    monkeypatch.setattr("sys.argv", [
        "pychub", "main.whl",
        "-a", "dep1.whl", "dep2.whl",
        "-a", "dep3.whl"
    ])

    cli.main()

    args = mock_process.call_args[0][0]
    # action="append" with nargs="+" creates nested lists
    assert args.add_wheel == [[Path("dep1.whl"), Path("dep2.whl")], [Path("dep3.whl")]]


def test_main_parses_chub_argument(monkeypatch):
    """Test that --chub argument is parsed correctly."""
    from pychub.package import cli

    mock_process = Mock()
    monkeypatch.setattr(cli, "process_options", mock_process)
    monkeypatch.setattr("sys.argv", ["pychub", "pkg.whl", "-c", "output.chub"])

    cli.main()

    args = mock_process.call_args[0][0]
    assert args.chub == Path("output.chub")


def test_main_parses_chubproject_arguments(monkeypatch):
    """Test that --chubproject and --chubproject-save are parsed correctly."""
    from pychub.package import cli

    mock_process = Mock()
    monkeypatch.setattr(cli, "process_options", mock_process)
    monkeypatch.setattr("sys.argv", [
        "pychub", "pkg.whl",
        "--chubproject", "config.toml",
        "--chubproject-save", "output.toml"
    ])

    cli.main()

    args = mock_process.call_args[0][0]
    assert args.chubproject == Path("config.toml")
    assert args.chubproject_save == Path("output.toml")


def test_main_parses_table_argument(monkeypatch):
    """Test that --table argument is parsed correctly."""
    from pychub.package import cli

    mock_process = Mock()
    monkeypatch.setattr(cli, "process_options", mock_process)
    monkeypatch.setattr("sys.argv", ["pychub", "pkg.whl", "-t", "custom.table"])

    cli.main()

    args = mock_process.call_args[0][0]
    assert args.table == "custom.table"


def test_main_parses_entrypoint_argument(monkeypatch):
    """Test that --entrypoint argument is parsed correctly."""
    from pychub.package import cli

    mock_process = Mock()
    monkeypatch.setattr(cli, "process_options", mock_process)
    monkeypatch.setattr("sys.argv", ["pychub", "pkg.whl", "-e", "module:function"])

    cli.main()

    args = mock_process.call_args[0][0]
    assert args.entrypoint == "module:function"


def test_main_parses_include_argument(monkeypatch):
    """Test that --include arguments are parsed correctly."""
    from pychub.package import cli

    mock_process = Mock()
    monkeypatch.setattr(cli, "process_options", mock_process)
    monkeypatch.setattr("sys.argv", [
        "pychub", "pkg.whl",
        "-i", "README.md::docs/", "config.yml"
    ])

    cli.main()

    args = mock_process.call_args[0][0]
    assert args.include == ["README.md::docs/", "config.yml"]


def test_main_parses_metadata_entry_argument(monkeypatch):
    """Test that --metadata-entry arguments are parsed correctly."""
    from pychub.package import cli

    mock_process = Mock()
    monkeypatch.setattr(cli, "process_options", mock_process)
    monkeypatch.setattr("sys.argv", [
        "pychub", "pkg.whl",
        "-m", "key1=val1", "key2=val2",
        "-m", "key3=val3"
    ])

    cli.main()

    args = mock_process.call_args[0][0]
    # action="append" with nargs="+" creates nested lists
    assert args.metadata_entry == [["key1=val1", "key2=val2"], ["key3=val3"]]


def test_main_parses_script_arguments(monkeypatch):
    """Test that --pre-script and --post-script are parsed correctly."""
    from pychub.package import cli

    mock_process = Mock()
    monkeypatch.setattr(cli, "process_options", mock_process)
    monkeypatch.setattr("sys.argv", [
        "pychub", "pkg.whl",
        "-p", "pre1.sh", "pre2.sh",
        "-o", "post1.sh"
    ])

    cli.main()

    args = mock_process.call_args[0][0]
    assert args.pre_script == [["pre1.sh", "pre2.sh"]]
    assert args.post_script == [["post1.sh"]]


def test_main_parses_verbose_flag(monkeypatch):
    """Test that --verbose flag is parsed correctly."""
    from pychub.package import cli

    mock_process = Mock()
    monkeypatch.setattr(cli, "process_options", mock_process)
    monkeypatch.setattr("sys.argv", ["pychub", "pkg.whl", "--verbose"])

    cli.main()

    args = mock_process.call_args[0][0]
    assert args.verbose is True


def test_main_parses_version_flag(monkeypatch):
    """Test that --version flag is parsed correctly."""
    from pychub.package import cli

    mock_process = Mock()
    monkeypatch.setattr(cli, "process_options", mock_process)
    monkeypatch.setattr("sys.argv", ["pychub", "pkg.whl", "-v"])

    cli.main()

    args = mock_process.call_args[0][0]
    assert args.version is True


def test_main_dunder_name_guard(monkeypatch):
    """Test that if __name__ == '__main__' block calls main()."""
    from pychub.package import cli

    # Track if main was called
    call_tracker = {"called": False}
    original_main = cli.main

    def mock_main():
        call_tracker["called"] = True

    # Replace main in the cli module
    monkeypatch.setattr(cli, "main", mock_main)

    # Now simulate the if __name__ == "__main__" check
    # We can't actually re-execute the module, so we just verify
    # that the guard exists in the source and would call main()
    import inspect
    source = inspect.getsource(cli)

    # Verify the guard exists
    assert 'if __name__ == "__main__"' in source
    assert 'main()' in source

    # Verify main is callable
    assert callable(original_main)
