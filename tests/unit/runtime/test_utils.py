import inspect

import pytest

from pychub.runtime import utils


# ============================================================================
# pep668_blocked tests
# ============================================================================

@pytest.mark.parametrize("stderr_text,expected", [
    # None and empty cases
    (None, False),
    ("", False),

    # Positive cases - "externally managed"
    ("error: externally managed environment", True),
    ("ERROR: EXTERNALLY MANAGED ENVIRONMENT", True),
    ("Error: Externally Managed Environment", True),
    ("  externally managed  environment  ", True),

    # Positive cases - "externally-managed-environment"
    ("error: externally-managed-environment marker found", True),
    ("ERROR: EXTERNALLY-MANAGED-ENVIRONMENT", True),

    # Both markers present
    ("externally managed and externally-managed-environment", True),

    # Multiline
    ("Some error occurred\nerror: externally managed environment\nAdditional info", True),

    # Negative cases
    ("error: package not found", False),
    ("error: external manager failed", False),
    ("some other error message", False),
])
def test_pep668_blocked(stderr_text, expected):
    """Test pep668_blocked with various inputs."""
    assert utils.pep668_blocked(stderr_text) is expected


# ============================================================================
# die tests - exit codes
# ============================================================================

@pytest.mark.parametrize("exit_code", [0, 1, 2, 42, -1, 127])
def test_die_with_integer_exit_code(exit_code):
    """Test that die exits with the provided integer code."""
    with pytest.raises(SystemExit) as exc_info:
        utils.die(exit_code)
    assert exc_info.value.code == exit_code


# ============================================================================
# die tests - messages
# ============================================================================

@pytest.mark.parametrize("message", [
    "Something went wrong",
    "",
    "Error occurred\nAdditional details",
    "Error: 'quote' and \"doublequote\" and \ttab",
    "Error: файл не найден 🔥",
])
def test_die_with_string_message(capsys, message):
    """Test that die prints message to stderr and exits with code 2."""
    with pytest.raises(SystemExit) as exc_info:
        utils.die(message)

    assert exc_info.value.code == 2

    captured = capsys.readouterr()
    assert f"pychub: {message}" in captured.err
    assert captured.out == ""  # Nothing on stdout


# ============================================================================
# die tests - behavior verification
# ============================================================================

def test_die_always_exits():
    """Test that die never returns normally."""
    with pytest.raises(SystemExit):
        utils.die("message")


# ============================================================================
# Module structure tests
# ============================================================================

@pytest.mark.parametrize("func_name,expected_params", [
    ("pep668_blocked", ["stderr_text"]),
    ("die", ["msg_or_code"]),
])
def test_function_signatures(func_name, expected_params):
    """Test that functions have correct signatures."""
    func = getattr(utils, func_name)
    assert callable(func)

    sig = inspect.signature(func)
    params = list(sig.parameters.keys())
    assert params == expected_params