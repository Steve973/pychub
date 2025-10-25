import argparse

import pytest

from pychub.runtime import cli


def test_build_parser_returns_argument_parser():
    """Test that the build_parser returns an ArgumentParser instance."""
    parser = cli.build_parser()
    assert isinstance(parser, argparse.ArgumentParser)
    assert parser.prog == "pychub"


def test_build_parser_has_correct_description():
    """Test that the parser has the expected description."""
    parser = cli.build_parser()
    assert "Install bundled wheels" in parser.description
    assert "optionally run" in parser.description


def test_build_parser_has_dry_run_flag():
    """Test that the parser has a "--dry-run" flag."""
    parser = cli.build_parser()
    args = parser.parse_args(["--dry-run"])
    assert args.dry_run is True

    args = parser.parse_args(["-d"])
    assert args.dry_run is True

    args = parser.parse_args([])
    assert args.dry_run is False


def test_build_parser_has_exec_flag():
    """Test that the parser has an "--exec" flag."""
    parser = cli.build_parser()
    args = parser.parse_args(["--exec"])
    assert args.exec is True

    args = parser.parse_args(["-e"])
    assert args.exec is True

    args = parser.parse_args([])
    assert args.exec is False


def test_build_parser_has_info_flag():
    """Test that the parser has an "--info" flag."""
    parser = cli.build_parser()
    args = parser.parse_args(["--info"])
    assert args.info is True

    args = parser.parse_args(["-i"])
    assert args.info is True

    args = parser.parse_args([])
    assert args.info is False


def test_build_parser_has_list_flag():
    """Test that the parser has a "--list" flag."""
    parser = cli.build_parser()
    args = parser.parse_args(["--list"])
    assert args.list is True

    args = parser.parse_args(["-l"])
    assert args.list is True

    args = parser.parse_args([])
    assert args.list is False


def test_build_parser_has_no_post_scripts_flag():
    """Test that the parser has a "--no-post-scripts" flag."""
    parser = cli.build_parser()
    args = parser.parse_args(["--no-post-scripts"])
    assert args.no_post_scripts is True

    args = parser.parse_args([])
    assert args.no_post_scripts is False


def test_build_parser_has_no_pre_scripts_flag():
    """Test that the parser has a "--no-pre-scripts" flag."""
    parser = cli.build_parser()
    args = parser.parse_args(["--no-pre-scripts"])
    assert args.no_pre_scripts is True

    args = parser.parse_args([])
    assert args.no_pre_scripts is False


def test_build_parser_has_no_scripts_flag():
    """Test that the parser has a "--no-scripts" flag."""
    parser = cli.build_parser()
    args = parser.parse_args(["--no-scripts"])
    assert args.no_scripts is True

    args = parser.parse_args([])
    assert args.no_scripts is False


def test_build_parser_has_quiet_flag():
    """Test that the parser has a "--quiet" flag."""
    parser = cli.build_parser()
    args = parser.parse_args(["--quiet"])
    assert args.quiet is True

    args = parser.parse_args(["-q"])
    assert args.quiet is True

    args = parser.parse_args([])
    assert args.quiet is False


def test_build_parser_has_run_option():
    """Test that the parser has a "--run" option with an optional value."""
    parser = cli.build_parser()

    # --run with no value (const="")
    args = parser.parse_args(["--run"])
    assert args.run == ""

    # -r with no value
    args = parser.parse_args(["-r"])
    assert args.run == ""

    # --run with entrypoint
    args = parser.parse_args(["--run", "module:function"])
    assert args.run == "module:function"

    # Not provided
    args = parser.parse_args([])
    assert args.run is None


def test_build_parser_has_show_scripts_flag():
    """Test that the parser has a "--show-scripts" flag."""
    parser = cli.build_parser()
    args = parser.parse_args(["--show-scripts"])
    assert args.show_scripts is True

    args = parser.parse_args(["-s"])
    assert args.show_scripts is True

    args = parser.parse_args([])
    assert args.show_scripts is False


def test_build_parser_has_unpack_option():
    """Test that the parser has an "--unpack" option with an optional dir."""
    parser = cli.build_parser()

    # --unpack with no value (const="")
    args = parser.parse_args(["--unpack"])
    assert args.unpack == "."

    # -u with no value
    args = parser.parse_args(["-u"])
    assert args.unpack == "."

    # --unpack with directory
    args = parser.parse_args(["--unpack", "/some/dir"])
    assert args.unpack == "/some/dir"

    # Not provided
    args = parser.parse_args([])
    assert args.unpack is None


def test_build_parser_has_venv_option():
    """Test that the parser has a "--venv" option requiring a dir."""
    parser = cli.build_parser()

    # --venv with directory
    args = parser.parse_args(["--venv", "/path/to/venv"])
    assert args.venv == "/path/to/venv"

    # Not provided
    args = parser.parse_args([])
    assert args.venv is None


def test_build_parser_has_version_flag():
    """Test that the parser has a "--version" flag."""
    parser = cli.build_parser()
    args = parser.parse_args(["--version"])
    assert args.version is True

    args = parser.parse_args([])
    assert args.version is False


def test_build_parser_has_verbose_flag():
    """Test that the parser has a "--verbose" flag."""
    parser = cli.build_parser()
    args = parser.parse_args(["--verbose"])
    assert args.verbose is True

    args = parser.parse_args(["-v"])
    assert args.verbose is True

    args = parser.parse_args([])
    assert args.verbose is False


def test_build_parser_has_entrypoint_args():
    """Test that the parser captures args after "--" as entrypoint_args."""
    parser = cli.build_parser()

    # Just -- alone without arguments means an empty remainder
    ns, args = parser.parse_known_args(["-e", "--", "--some-option", "entrypoint_arg"])
    assert "entrypoint_arg" in args
    assert ns.exec is True

    # No -- at all
    ns, args = parser.parse_known_args([])
    assert "entrypoint_arg" not in args
    assert ns.exec is False


def test_build_parser_combined_flags():
    """Test parser with multiple flags combined."""
    parser = cli.build_parser()

    ns, args = parser.parse_known_args([
        "--dry-run",
        "--verbose",
        "--venv", "/path/venv",
        "--run", "module:main",
        "--", "--arg1", "val1"
    ])

    assert ns.dry_run is True
    assert ns.verbose is True
    assert ns.venv == "/path/venv"
    assert ns.run == "module:main"
    assert "--arg1" in args
    assert "val1" in args


def test_build_parser_help_flag_exists():
    """Test that the help flag is available."""
    parser = cli.build_parser()

    # Check that -h is in the parser
    # Note: --help will cause SystemExit, so we just verify it's registered
    actions = {action.dest: action for action in parser._actions}
    assert "help" in actions


def test_build_parser_all_short_forms():
    """Test that all expected short forms are present."""
    parser = cli.build_parser()

    # Map of long -> short
    expected_shorts = {
        "dry_run": "-d",
        "exec": "-e",
        "help": "-h",
        "info": "-i",
        "list": "-l",
        "quiet": "-q",
        "run": "-r",
        "show_scripts": "-s",
        "unpack": "-u",
        "verbose": "-v",
    }

    for dest, short in expected_shorts.items():
        # Parse with short form
        if dest == "help":
            # help causes exit, skip actual parsing
            continue
        elif dest == "run":
            # These take optional values
            args = parser.parse_args([short])
            assert getattr(args, dest) == ""
        elif dest == "unpack":
            # These take optional values
            args = parser.parse_args([short])
            assert getattr(args, dest) == "."
        else:
            args = parser.parse_args([short])
            assert getattr(args, dest) is True


def test_build_parser_no_add_help_default():
    """Test that the parser was created with add_help=False."""
    parser = cli.build_parser()
    # The parser should have add_help=False in its constructor,
    # which means -h/--help are manually added
    # We verify by checking that help exists in actions
    help_action = next((a for a in parser._actions if a.dest == "help"), None)
    assert help_action is not None


def test_cli_module_has_build_parser_function():
    """Test that the cli module exports build_parser."""
    assert hasattr(cli, "build_parser")
    assert callable(cli.build_parser)


def test_cli_module_main_guard_exists():
    """Test that if __name__ == '__main__' guard exists in the source."""
    import inspect

    source = inspect.getsource(cli)
    assert 'if __name__ == "__main__"' in source
    assert "build_parser()" in source
    assert "parse_args()" in source


def test_parser_prog_name():
    """Test that the parser program name is 'pychub'."""
    parser = cli.build_parser()
    assert parser.prog == "pychub"


def test_parser_accepts_empty_args():
    """Test that the parser accepts an empty argument list without error."""
    parser = cli.build_parser()
    ns, args = parser.parse_known_args([])

    # Verify defaults
    for arg in [ns.dry_run,
                ns.exec,
                ns.info,
                ns.list,
                ns.no_post_scripts,
                ns.no_pre_scripts,
                ns.no_scripts,
                ns.quiet,
                ns.show_scripts,
                ns.version,
                ns.verbose]:
        assert arg is False

    for arg in [ns.run, ns.unpack, ns.venv]:
        assert arg is None

    assert not args


def test_venv_option_without_value_fails():
    """Test that --venv without a value raises an error."""
    parser = cli.build_parser()

    with pytest.raises(SystemExit):
        parser.parse_args(["--venv"])


def test_run_with_empty_string_entrypoint():
    """Test "--run" with an empty string value (using baked entrypoint)."""
    parser = cli.build_parser()

    # This simulates: python chub.chub --run (no entrypoint specified)
    args = parser.parse_args(["--run"])
    assert args.run == ""


def test_unpack_with_empty_string_dir():
    """Test "--unpack" with an empty string value (uses derived dir)."""
    parser = cli.build_parser()

    args = parser.parse_args(["--unpack"])
    assert args.unpack == "."


def test_entrypoint_args_without_double_dash():
    """Test that regular args are not captured as entrypoint_args."""
    parser = cli.build_parser()

    ns, args = parser.parse_known_args(["--verbose", "--run", "module:main"])
    assert ns.verbose is True
    assert ns.run == "module:main"
    assert not args


def test_entrypoint_args_with_double_dash():
    """Test that args after "--" are captured correctly."""
    parser = cli.build_parser()

    ns, args = parser.parse_known_args([
        "--verbose",
        "--run", "module:main",
        "--",
        "--custom-flag",
        "custom-value",
        "-x"
    ])

    assert ns.verbose is True
    assert ns.run == "module:main"
    assert "--custom-flag" in args
    assert "custom-value" in args
    assert "-x" in args


def test_multiple_boolean_flags_together():
    """Test multiple boolean flags can be used together."""
    parser = cli.build_parser()

    args = parser.parse_args([
        "--dry-run",
        "--verbose",
        "--quiet",
        "--no-scripts",
        "--exec"
    ])

    assert args.dry_run is True
    assert args.verbose is True
    assert args.quiet is True
    assert args.no_scripts is True
    assert args.exec is True
