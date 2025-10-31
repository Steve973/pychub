import argparse
from pathlib import Path

import pytest

from pychub.package import cli


# ===========================
# Parser Creation Tests
# ===========================

def test_create_arg_parser_returns_argument_parser():
    """Test that create_arg_parser returns an ArgumentParser instance."""
    parser = cli.create_arg_parser()
    assert isinstance(parser, argparse.ArgumentParser)


def test_parser_has_correct_prog_name():
    """Test that parser has correct program name."""
    parser = cli.create_arg_parser()
    assert parser.prog == "pychub"


def test_parser_has_description():
    """Test that parser has a description."""
    parser = cli.create_arg_parser()
    assert "package a wheel" in parser.description


# ===========================
# Boolean Flag Tests
# ===========================

def test_analyze_compatibility_flag():
    """Test --analyze-compatibility flag."""
    parser = cli.create_arg_parser()
    args = parser.parse_args(["--analyze-compatibility"])
    assert args.analyze_compatibility is True

    args = parser.parse_args([])
    assert args.analyze_compatibility is False


def test_verbose_flag():
    """Test --verbose flag."""
    parser = cli.create_arg_parser()
    args = parser.parse_args(["--verbose"])
    assert args.verbose is True

    args = parser.parse_args([])
    assert args.verbose is False


def test_version_flag():
    """Test -v/--version flag."""
    parser = cli.create_arg_parser()

    args = parser.parse_args(["-v"])
    assert args.version is True

    args = parser.parse_args(["--version"])
    assert args.version is True

    args = parser.parse_args([])
    assert args.version is False


# ===========================
# Path Argument Tests
# ===========================

def test_chub_argument():
    """Test -c/--chub argument converts to Path."""
    parser = cli.create_arg_parser()

    args = parser.parse_args(["-c", "output.chub"])
    assert args.chub == Path("output.chub")

    args = parser.parse_args(["--chub", "path/to/file.chub"])
    assert args.chub == Path("path/to/file.chub")

    args = parser.parse_args([])
    assert args.chub is None


def test_chubproject_argument():
    """Test --chubproject argument converts to Path."""
    parser = cli.create_arg_parser()

    args = parser.parse_args(["--chubproject", "config.toml"])
    assert args.chubproject == Path("config.toml")

    args = parser.parse_args([])
    assert args.chubproject is None


def test_chubproject_save_argument():
    """Test --chubproject-save argument converts to Path."""
    parser = cli.create_arg_parser()

    args = parser.parse_args(["--chubproject-save", "output.toml"])
    assert args.chubproject_save == Path("output.toml")

    args = parser.parse_args([])
    assert args.chubproject_save is None


# ===========================
# String Argument Tests
# ===========================

def test_entrypoint_argument():
    """Test -e/--entrypoint argument."""
    parser = cli.create_arg_parser()

    args = parser.parse_args(["-e", "module:function"])
    assert args.entrypoint == "module:function"

    args = parser.parse_args(["--entrypoint", "app.main:run"])
    assert args.entrypoint == "app.main:run"

    args = parser.parse_args([])
    assert args.entrypoint is None


def test_table_argument():
    """Test -t/--table argument."""
    parser = cli.create_arg_parser()

    args = parser.parse_args(["-t", "custom.table"])
    assert args.table == "custom.table"

    args = parser.parse_args(["--table", "tool.myapp"])
    assert args.table == "tool.myapp"

    args = parser.parse_args([])
    assert args.table is None


def test_project_path_argument():
    """Test --project-path argument with default."""
    parser = cli.create_arg_parser()

    args = parser.parse_args(["--project-path", "/path/to/project"])
    assert args.project_path == "/path/to/project"

    args = parser.parse_args([])
    assert args.project_path == "."


# ===========================
# List/Extend Action Tests
# ===========================

def test_wheel_argument_single():
    """Test -w/--wheel with single value."""
    parser = cli.create_arg_parser()

    args = parser.parse_args(["-w", "pkg.whl"])
    assert args.wheel == ["pkg.whl"]

    args = parser.parse_args(["--wheel", "dist/package.whl"])
    assert args.wheel == ["dist/package.whl"]


def test_wheel_argument_multiple():
    """Test -w/--wheel with multiple values (extend action)."""
    parser = cli.create_arg_parser()

    args = parser.parse_args(["-w", "pkg1.whl", "pkg2.whl"])
    assert args.wheel == ["pkg1.whl", "pkg2.whl"]

    args = parser.parse_args(["-w", "a.whl", "-w", "b.whl", "c.whl"])
    assert args.wheel == ["a.whl", "b.whl", "c.whl"]


def test_wheel_argument_default_empty():
    """Test --wheel defaults to empty list."""
    parser = cli.create_arg_parser()
    args = parser.parse_args([])
    assert args.wheel == []


def test_include_argument():
    """Test -i/--include with extend action."""
    parser = cli.create_arg_parser()

    args = parser.parse_args(["-i", "file.txt"])
    assert args.include == ["file.txt"]

    args = parser.parse_args(["-i", "a.txt", "b.txt", "-i", "c.txt"])
    assert args.include == ["a.txt", "b.txt", "c.txt"]

    args = parser.parse_args(["--include", "README.md::docs/", "config.yml"])
    assert args.include == ["README.md::docs/", "config.yml"]


def test_include_chub_argument():
    """Test --include-chub with extend action."""
    parser = cli.create_arg_parser()

    args = parser.parse_args(["--include-chub", "dep.chub"])
    assert args.include_chub == ["dep.chub"]

    args = parser.parse_args(["--include-chub", "a.chub", "b.chub"])
    assert args.include_chub == ["a.chub", "b.chub"]

    args = parser.parse_args([])
    assert args.include_chub == []


def test_metadata_entry_argument():
    """Test -m/--metadata-entry with extend action."""
    parser = cli.create_arg_parser()

    args = parser.parse_args(["-m", "key=value"])
    assert args.metadata_entry == ["key=value"]

    args = parser.parse_args(["-m", "k1=v1", "k2=v2", "-m", "k3=v3"])
    assert args.metadata_entry == ["k1=v1", "k2=v2", "k3=v3"]

    args = parser.parse_args([])
    assert args.metadata_entry is None


def test_pre_script_argument():
    """Test -p/--pre-script with extend action."""
    parser = cli.create_arg_parser()

    args = parser.parse_args(["-p", "setup.sh"])
    assert args.pre_script == ["setup.sh"]

    args = parser.parse_args(["-p", "a.sh", "b.sh", "-p", "c.sh"])
    assert args.pre_script == ["a.sh", "b.sh", "c.sh"]

    args = parser.parse_args([])
    assert args.pre_script == []


def test_post_script_argument():
    """Test -o/--post-script with extend action."""
    parser = cli.create_arg_parser()

    args = parser.parse_args(["-o", "cleanup.sh"])
    assert args.post_script == ["cleanup.sh"]

    args = parser.parse_args(["--post-script", "a.sh", "b.sh"])
    assert args.post_script == ["a.sh", "b.sh"]

    args = parser.parse_args([])
    assert args.post_script == []


# ===========================
# Special Argument Tests
# ===========================

def test_entrypoint_args_remainder():
    """Test --entrypoint-args captures all remaining arguments."""
    parser = cli.create_arg_parser()

    args = parser.parse_args(["--entrypoint-args", "arg1", "arg2", "--flag"])
    assert args.entrypoint_args == ["arg1", "arg2", "--flag"]

    args = parser.parse_args([])
    assert args.entrypoint_args == []


def test_entrypoint_args_must_be_last():
    """Test that --entrypoint-args captures everything after it."""
    parser = cli.create_arg_parser()

    # Everything after --entrypoint-args is captured
    args = parser.parse_args(["--verbose", "--entrypoint-args", "-w", "test.whl"])
    assert args.verbose is True
    assert args.entrypoint_args == ["-w", "test.whl"]
    # wheel won't be parsed because it's after --entrypoint-args


# ===========================
# Combined Arguments Tests
# ===========================

def test_multiple_arguments_together():
    """Test parsing multiple arguments together."""
    parser = cli.create_arg_parser()

    args = parser.parse_args([
        "-w", "pkg.whl",
        "-c", "output.chub",
        "-e", "main:run",
        "--verbose",
        "-i", "README.md",
        "-p", "setup.sh",
        "-m", "author=John"
    ])

    assert args.wheel == ["pkg.whl"]
    assert args.chub == Path("output.chub")
    assert args.entrypoint == "main:run"
    assert args.verbose is True
    assert args.include == ["README.md"]
    assert args.pre_script == ["setup.sh"]
    assert args.metadata_entry == ["author=John"]


def test_all_defaults():
    """Test that all arguments have appropriate defaults."""
    parser = cli.create_arg_parser()
    args = parser.parse_args([])

    assert args.analyze_compatibility is False
    assert args.chub is None
    assert args.chubproject is None
    assert args.chubproject_save is None
    assert args.entrypoint is None
    assert args.entrypoint_args == []
    assert args.include == []
    assert args.include_chub == []
    assert args.metadata_entry is None
    assert args.post_script == []
    assert args.pre_script == []
    assert args.project_path == "."
    assert args.table is None
    assert args.verbose is False
    assert args.version is False
    assert args.wheel == []


# ===========================
# Short vs Long Form Tests
# ===========================

@pytest.mark.parametrize("short,long,value", [
    ("-c", "--chub", "test.chub"),
    ("-e", "--entrypoint", "main:run"),
    ("-i", "--include", "file.txt"),
    ("-m", "--metadata-entry", "key=val"),
    ("-o", "--post-script", "post.sh"),
    ("-p", "--pre-script", "pre.sh"),
    ("-t", "--table", "custom"),
    ("-v", "--version", None),
    ("-w", "--wheel", "pkg.whl"),
])
def test_short_and_long_forms_equivalent(short, long, value):
    """Test that short and long forms produce same results."""
    parser = cli.create_arg_parser()

    if value:
        args_short = parser.parse_args([short, value])
        args_long = parser.parse_args([long, value])

        attr_name = long.lstrip("-").replace("-", "_")
        assert getattr(args_short, attr_name) == getattr(args_long, attr_name)
    else:
        # Boolean flags
        args_short = parser.parse_args([short])
        args_long = parser.parse_args([long])

        attr_name = long.lstrip("-").replace("-", "_")
        assert getattr(args_short, attr_name) == getattr(args_long, attr_name) == True


# ===========================
# Edge Cases
# ===========================

def test_empty_string_values():
    """Test handling of empty string values."""
    parser = cli.create_arg_parser()

    args = parser.parse_args(["-e", ""])
    assert args.entrypoint == ""

    args = parser.parse_args(["-t", ""])
    assert args.table == ""


def test_path_with_spaces():
    """Test paths with spaces are handled correctly."""
    parser = cli.create_arg_parser()

    args = parser.parse_args(["-c", "path with spaces.chub"])
    assert args.chub == Path("path with spaces.chub")


def test_special_characters_in_strings():
    """Test special characters in string arguments."""
    parser = cli.create_arg_parser()

    args = parser.parse_args(["-e", "my_module:my-function"])
    assert args.entrypoint == "my_module:my-function"

    args = parser.parse_args(["-m", "key=value,with,commas"])
    assert args.metadata_entry == ["key=value,with,commas"]