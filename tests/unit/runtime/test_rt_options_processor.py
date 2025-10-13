"""Unit tests for rt_options_processor.py"""

from argparse import Namespace
import pytest
import pychub.runtime.rt_options_processor as rt_op


# ============================================================================
# _active_options tests
# ============================================================================

def test_active_options_empty_namespace():
    """Test _active_options with empty Namespace."""
    args = Namespace()
    active = rt_op._active_options(args)
    assert active == set()


def test_active_options_with_boolean_flags():
    """Test _active_options correctly identifies active boolean flags."""
    args = Namespace(dry_run=True, verbose=False, exec=True, quiet=False)
    active = rt_op._active_options(args)
    assert active == {"dry-run", "exec"}


def test_active_options_with_string_values():
    """Test _active_options includes options with non-None string values."""
    args = Namespace(venv="/path/to/venv", run="module:main", unpack=None)
    active = rt_op._active_options(args)
    assert active == {"venv", "run"}


def test_active_options_with_empty_strings():
    """Test _active_options includes options with empty string values."""
    args = Namespace(run="", unpack="", venv=None)
    active = rt_op._active_options(args)
    assert active == {"run", "unpack"}


def test_active_options_ignores_underscore_prefixed():
    """Test _active_options ignores attributes starting with underscore."""
    args = Namespace(_internal=True, venv=True)
    active = rt_op._active_options(args)
    assert "venv" in active


def test_active_options_ignores_unknown_options():
    """Test _active_options ignores options not in _OPT_KEYS."""
    args = Namespace(venv=True, unknown_option=True)
    active = rt_op._active_options(args)
    assert active == {"venv"}


def test_active_options_replaces_underscores_with_hyphens():
    """Test _active_options converts underscores to hyphens."""
    args = Namespace(no_scripts=True, no_pre_scripts=True)
    active = rt_op._active_options(args)
    assert active == {"no-scripts", "no-pre-scripts"}


def test_active_options_mixed_types():
    """Test _active_options with mixed boolean, string, and None values."""
    args = Namespace(
        dry_run=True,
        verbose=False,
        venv="/path",
        run="",
        unpack=None,
        info=False
    )
    active = rt_op._active_options(args)
    assert active == {"dry-run", "venv", "run"}


# ============================================================================
# _apply_implications tests
# ============================================================================

def test_apply_implications_no_scripts_sets_both():
    """Test _apply_implications: no_scripts implies no_pre_scripts and no_post_scripts."""
    args = Namespace(no_scripts=True, no_pre_scripts=False, no_post_scripts=False)
    rt_op._apply_implications(args)
    assert args.no_pre_scripts is True
    assert args.no_post_scripts is True


def test_apply_implications_exec_sets_all_no_scripts():
    """Test _apply_implications: exec implies no_scripts, no_pre_scripts, no_post_scripts."""
    args = Namespace(exec=True, no_scripts=False, no_pre_scripts=False, no_post_scripts=False)
    rt_op._apply_implications(args)
    assert args.no_scripts is True
    assert args.no_pre_scripts is True
    assert args.no_post_scripts is True


def test_apply_implications_quiet_disables_verbose():
    """Test _apply_implications: quiet disables verbose."""
    args = Namespace(quiet=True, verbose=True)
    rt_op._apply_implications(args)
    assert args.verbose is False


def test_apply_implications_quiet_preserves_false_verbose():
    """Test _apply_implications: quiet with verbose already False."""
    args = Namespace(quiet=True, verbose=False)
    rt_op._apply_implications(args)
    assert args.verbose is False


def test_apply_implications_no_flags_set():
    """Test _apply_implications with no relevant flags set."""
    args = Namespace(exec=False, no_scripts=False, quiet=False, verbose=True)
    rt_op._apply_implications(args)
    assert args.verbose is True
    assert args.no_scripts is False


def test_apply_implications_exec_overrides_no_scripts():
    """Test _apply_implications: exec sets no_scripts even if already True."""
    args = Namespace(exec=True, no_scripts=True, no_pre_scripts=True, no_post_scripts=False)
    rt_op._apply_implications(args)
    assert args.no_scripts is True
    assert args.no_pre_scripts is True
    assert args.no_post_scripts is True


def test_apply_implications_combined_exec_and_quiet():
    """Test _apply_implications with both exec and quiet."""
    args = Namespace(
        exec=True,
        quiet=True,
        verbose=True,
        no_scripts=False,
        no_pre_scripts=False,
        no_post_scripts=False
    )
    rt_op._apply_implications(args)
    assert args.no_scripts is True
    assert args.no_pre_scripts is True
    assert args.no_post_scripts is True
    assert args.verbose is False


def test_apply_implications_no_scripts_and_exec():
    """Test _apply_implications with both no_scripts and exec."""
    args = Namespace(
        exec=True,
        no_scripts=True,
        no_pre_scripts=False,
        no_post_scripts=False
    )
    rt_op._apply_implications(args)
    assert args.no_scripts is True
    assert args.no_pre_scripts is True
    assert args.no_post_scripts is True


# ============================================================================
# validate_and_imply tests
# ============================================================================

def test_validate_and_imply_no_conflicts():
    """Test validate_and_imply with no incompatible options."""
    args = Namespace(
        dry_run=True,
        verbose=True,
        exec=False,
        info=False,
        no_scripts=False,
        no_pre_scripts=False,
        no_post_scripts=False,
        quiet=False
    )
    result = rt_op.validate_and_imply(args)
    assert result == args


def test_validate_and_imply_incompatible_dry_run_and_info():
    """Test validate_and_imply raises on incompatible dry-run and info."""
    args = Namespace(
        dry_run=True,
        info=True,
        no_scripts=False,
        no_pre_scripts=False,
        no_post_scripts=False,
        exec=False,
        quiet=False
    )
    with pytest.raises(ValueError) as exc_info:
        rt_op.validate_and_imply(args)
    assert "--dry-run is incompatible with --info" in str(exc_info.value)


def test_validate_and_imply_incompatible_exec_and_venv():
    """Test validate_and_imply raises on incompatible exec and venv."""
    args = Namespace(
        exec=True,
        venv="/path/to/venv",
        no_scripts=False,
        no_pre_scripts=False,
        no_post_scripts=False,
        quiet=False
    )
    with pytest.raises(ValueError) as exc_info:
        rt_op.validate_and_imply(args)
    assert "--exec is incompatible with --venv" in str(exc_info.value)


def test_validate_and_imply_incompatible_run_and_list():
    """Test validate_and_imply raises on incompatible run and list."""
    args = Namespace(
        run="module:main",
        list=True,
        no_scripts=False,
        no_pre_scripts=False,
        no_post_scripts=False,
        exec=False,
        quiet=False
    )
    with pytest.raises(ValueError) as exc_info:
        rt_op.validate_and_imply(args)
    assert "--run is incompatible with --list" in str(exc_info.value)


def test_validate_and_imply_multiple_incompatibilities():
    """Test validate_and_imply with multiple incompatible options."""
    args = Namespace(
        dry_run=True,
        info=True,
        version=True,
        no_scripts=False,
        no_pre_scripts=False,
        no_post_scripts=False,
        exec=False,
        quiet=False
    )
    with pytest.raises(ValueError) as exc_info:
        rt_op.validate_and_imply(args)
    error_msg = str(exc_info.value)
    assert "--dry-run is incompatible with --info" in error_msg or \
           "--dry-run is incompatible with --version" in error_msg


def test_validate_and_imply_applies_implications_before_validation():
    """Test validate_and_imply applies implications before checking conflicts."""
    args = Namespace(
        exec=True,
        no_scripts=False,
        no_pre_scripts=False,
        no_post_scripts=False,
        quiet=False,
        venv="/path"
    )
    with pytest.raises(ValueError) as exc_info:
        rt_op.validate_and_imply(args)
    # Should fail on exec+venv incompatibility
    assert "--exec is incompatible with --venv" in str(exc_info.value)


def test_validate_and_imply_compatible_dry_run_and_verbose():
    """Test validate_and_imply allows compatible dry-run and verbose."""
    args = Namespace(
        dry_run=True,
        verbose=True,
        no_scripts=False,
        no_pre_scripts=False,
        no_post_scripts=False,
        exec=False,
        quiet=False
    )
    result = rt_op.validate_and_imply(args)
    assert result == args


def test_validate_and_imply_compatible_venv_and_run():
    """Test validate_and_imply allows compatible venv and run."""
    args = Namespace(
        venv="/path",
        run="module:main",
        no_scripts=False,
        no_pre_scripts=False,
        no_post_scripts=False,
        exec=False,
        quiet=False
    )
    result = rt_op.validate_and_imply(args)
    assert result == args


def test_validate_and_imply_returns_same_namespace():
    """Test validate_and_imply returns the same Namespace object."""
    args = Namespace(verbose=True, no_scripts=False, no_pre_scripts=False, no_post_scripts=False, exec=False, quiet=False)
    result = rt_op.validate_and_imply(args)
    assert result is args


def test_validate_and_imply_incompatible_unpack_and_exec():
    """Test validate_and_imply raises on incompatible unpack and exec."""
    args = Namespace(
        unpack="/path",
        exec=True,
        no_scripts=False,
        no_pre_scripts=False,
        no_post_scripts=False,
        quiet=False
    )
    with pytest.raises(ValueError) as exc_info:
        rt_op.validate_and_imply(args)
    assert "--exec is incompatible with --unpack" in str(exc_info.value)


def test_validate_and_imply_no_post_scripts_incompatible_with_list():
    """Test validate_and_imply raises on incompatible no-post-scripts and list."""
    args = Namespace(
        no_post_scripts=True,
        list=True,
        no_scripts=False,
        no_pre_scripts=False,
        exec=False,
        quiet=False
    )
    with pytest.raises(ValueError) as exc_info:
        rt_op.validate_and_imply(args)
    assert "--no-post-scripts is incompatible with --list" in str(exc_info.value)


# ============================================================================
# COMMANDS constant tests
# ============================================================================

def test_commands_list_exists():
    """Test COMMANDS constant exists and is a list."""
    assert hasattr(rt_op, "COMMANDS")
    assert isinstance(rt_op.COMMANDS, list)


def test_commands_contains_expected_options():
    """Test COMMANDS contains expected option strings."""
    expected = [
        "dry-run", "exec", "help", "info", "list",
        "no-post-scripts", "no-pre-scripts", "no-scripts",
        "quiet", "run", "show-scripts", "show-compatibility",
        "unpack", "venv", "version", "verbose"
    ]
    for opt in expected:
        assert any(opt in cmd for cmd in rt_op.COMMANDS), f"{opt} not found in COMMANDS"


# ============================================================================
# COMPATIBLE_OPTIONS constant tests
# ============================================================================

def test_compatible_options_exists():
    """Test COMPATIBLE_OPTIONS constant exists and is a dict."""
    assert hasattr(rt_op, "COMPATIBLE_OPTIONS")
    assert isinstance(rt_op.COMPATIBLE_OPTIONS, dict)


def test_compatible_options_structure():
    """Test COMPATIBLE_OPTIONS has correct structure."""
    for key, value in rt_op.COMPATIBLE_OPTIONS.items():
        assert isinstance(key, str)
        assert isinstance(value, list)
        assert all(isinstance(item, str) for item in value)


def test_compatible_options_dry_run():
    """Test COMPATIBLE_OPTIONS for dry-run."""
    assert "dry-run" in rt_op.COMPATIBLE_OPTIONS
    compatible = rt_op.COMPATIBLE_OPTIONS["dry-run"]
    assert "verbose" in compatible
    assert "exec" in compatible


def test_compatible_options_exec():
    """Test COMPATIBLE_OPTIONS for exec."""
    assert "exec" in rt_op.COMPATIBLE_OPTIONS
    compatible = rt_op.COMPATIBLE_OPTIONS["exec"]
    assert "run" in compatible
    assert "dry-run" in compatible


# ============================================================================
# INCOMPATIBLE_OPTIONS constant tests
# ============================================================================

def test_incompatible_options_exists():
    """Test INCOMPATIBLE_OPTIONS constant exists and is a dict."""
    assert hasattr(rt_op, "INCOMPATIBLE_OPTIONS")
    assert isinstance(rt_op.INCOMPATIBLE_OPTIONS, dict)


def test_incompatible_options_structure():
    """Test INCOMPATIBLE_OPTIONS has correct structure."""
    for key, value in rt_op.INCOMPATIBLE_OPTIONS.items():
        assert isinstance(key, str)
        assert isinstance(value, list)
        assert all(isinstance(item, str) for item in value)


def test_incompatible_options_exec():
    """Test INCOMPATIBLE_OPTIONS for exec."""
    assert "exec" in rt_op.INCOMPATIBLE_OPTIONS
    incompatible = rt_op.INCOMPATIBLE_OPTIONS["exec"]
    assert "venv" in incompatible
    assert "unpack" in incompatible


def test_incompatible_options_help():
    """Test INCOMPATIBLE_OPTIONS for help."""
    assert "help" in rt_op.INCOMPATIBLE_OPTIONS
    incompatible = rt_op.INCOMPATIBLE_OPTIONS["help"]
    # help is incompatible with most options
    assert len(incompatible) > 5


def test_incompatible_options_symmetry():
    """Test that incompatibility is symmetric where expected."""
    # If A is incompatible with B, B should be incompatible with A
    for opt_a, incompatibles in rt_op.INCOMPATIBLE_OPTIONS.items():
        for opt_b in incompatibles:
            if opt_b in rt_op.INCOMPATIBLE_OPTIONS:
                assert opt_a in rt_op.INCOMPATIBLE_OPTIONS[opt_b], \
                    f"{opt_a} lists {opt_b} as incompatible, but {opt_b} doesn't list {opt_a}"


def test_all_options_are_keys_in_both_dicts():
    """Test that every option in _OPT_KEYS is a key in both COMPATIBLE and INCOMPATIBLE."""
    all_opts = rt_op._OPT_KEYS
    compat_keys = set(rt_op.COMPATIBLE_OPTIONS.keys())
    incompat_keys = set(rt_op.INCOMPATIBLE_OPTIONS.keys())

    missing_from_compat = all_opts - compat_keys
    missing_from_incompat = all_opts - incompat_keys

    assert not missing_from_compat, \
        f"These options are missing as keys in COMPATIBLE_OPTIONS: {missing_from_compat}"

    assert not missing_from_incompat, \
        f"These options are missing as keys in INCOMPATIBLE_OPTIONS: {missing_from_incompat}"


def test_incompatible_equals_complement_of_compatible():
    """Test that INCOMPATIBLE[opt] exactly equals (_OPT_KEYS - COMPATIBLE[opt] - {opt})."""
    all_opts = rt_op._OPT_KEYS

    for opt in all_opts:
        compatible = set(rt_op.COMPATIBLE_OPTIONS.get(opt, []))
        incompatible = set(rt_op.INCOMPATIBLE_OPTIONS.get(opt, []))

        # Calculate what incompatible SHOULD be: everything except compatible and self
        expected_incompatible = all_opts - compatible - {opt}

        assert incompatible == expected_incompatible, \
            f"{opt}: INCOMPATIBLE_OPTIONS must equal (_OPT_KEYS - COMPATIBLE - {{self}})\n" \
            f"  Missing from INCOMPATIBLE: {expected_incompatible - incompatible}\n" \
            f"  Extra in INCOMPATIBLE: {incompatible - expected_incompatible}"


def test_compatible_equals_complement_of_incompatible():
    """Test that COMPATIBLE[opt] exactly equals (_OPT_KEYS - INCOMPATIBLE[opt] - {opt})."""
    all_opts = rt_op._OPT_KEYS

    for opt in all_opts:
        compatible = set(rt_op.COMPATIBLE_OPTIONS.get(opt, []))
        incompatible = set(rt_op.INCOMPATIBLE_OPTIONS.get(opt, []))

        # Calculate what compatible SHOULD be: everything except incompatible and self
        expected_compatible = all_opts - incompatible - {opt}

        assert compatible == expected_compatible, \
            f"{opt}: COMPATIBLE_OPTIONS must equal (_OPT_KEYS - INCOMPATIBLE - {{self}})\n" \
            f"  Missing from COMPATIBLE: {expected_compatible - compatible}\n" \
            f"  Extra in COMPATIBLE: {compatible - expected_compatible}"


# ============================================================================
# _OPT_KEYS constant tests
# ============================================================================

def test_opt_keys_exists():
    """Test _OPT_KEYS constant exists and is a set."""
    assert hasattr(rt_op, "_OPT_KEYS")
    assert isinstance(rt_op._OPT_KEYS, set)


def test_opt_keys_contains_all_options():
    """Test _OPT_KEYS contains all options from both dicts."""
    expected = set(rt_op.COMPATIBLE_OPTIONS.keys()) | set(rt_op.INCOMPATIBLE_OPTIONS.keys())
    assert rt_op._OPT_KEYS == expected


def test_opt_keys_no_extra_keys():
    """Test _OPT_KEYS doesn't contain keys not in source dicts."""
    all_keys = set(rt_op.COMPATIBLE_OPTIONS.keys()) | set(rt_op.INCOMPATIBLE_OPTIONS.keys())
    assert rt_op._OPT_KEYS.issubset(all_keys)


# ============================================================================
# Edge case tests
# ============================================================================

def test_validate_with_empty_string_run():
    """Test validation with run set to empty string (uses baked entrypoint)."""
    args = Namespace(
        run="",
        verbose=True,
        no_scripts=False,
        no_pre_scripts=False,
        no_post_scripts=False,
        exec=False,
        quiet=False
    )
    result = rt_op.validate_and_imply(args)
    assert result == args


def test_validate_with_empty_string_unpack():
    """Test validation with unpack set to empty string (uses default dir)."""
    args = Namespace(
        unpack="",
        verbose=True,
        no_scripts=False,
        no_pre_scripts=False,
        no_post_scripts=False,
        exec=False,
        quiet=False
    )
    result = rt_op.validate_and_imply(args)
    assert result == args


def test_validate_quiet_and_verbose_both_true():
    """Test validation applies quiet wins over verbose implication."""
    args = Namespace(
        quiet=True,
        verbose=True,
        no_scripts=False,
        no_pre_scripts=False,
        no_post_scripts=False,
        exec=False
    )
    result = rt_op.validate_and_imply(args)
    assert result.verbose is False


def test_validate_show_compatibility_only_verbose():
    """Test show-compatibility is only compatible with verbose."""
    args = Namespace(
        show_compatibility=True,
        verbose=True,
        no_scripts=False,
        no_pre_scripts=False,
        no_post_scripts=False,
        exec=False,
        quiet=False
    )
    result = rt_op.validate_and_imply(args)
    assert result == args


def test_validate_show_compatibility_with_incompatible():
    """Test show-compatibility with incompatible option fails."""
    args = Namespace(
        show_compatibility=True,
        dry_run=True,
        no_scripts=False,
        no_pre_scripts=False,
        no_post_scripts=False,
        exec=False,
        quiet=False
    )
    with pytest.raises(ValueError) as exc_info:
        rt_op.validate_and_imply(args)
    assert "--show-compatibility is incompatible with --dry-run" in str(exc_info.value)