import sys

from pychub.runtime.actions import runtime_main


def test_main_imports_correctly():
    """Test that __main__ can import the main function."""
    from pychub.runtime.__main__ import main
    # If import succeeds, the module is valid
    assert callable(main)


import runpy

def test_main_calls_runtime_main(monkeypatch):
    called = {"flag": False}
    monkeypatch.setattr(runtime_main, "main", lambda: called.__setitem__("flag", True))

    # Remove the module so that runpy performs a fresh import, so
    # this prevents the "module found in sys.modules" warning
    sys.modules.pop("pychub.runtime.__main__", None)
    runpy.run_module("pychub.runtime.__main__", run_name="__main__")

    assert called["flag"]
