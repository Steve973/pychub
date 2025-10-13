def test_main_imports_correctly():
    """Test that __main__ can import the main function."""
    from pychub.runtime.__main__ import main
    # If import succeeds, the module is valid
    assert callable(main)


def test_main_calls_runtime_main(monkeypatch):
    """Test that __main__'s if-block calls runtime_main.main()."""
    import importlib.util
    from pathlib import Path

    # Track if main() was called
    call_tracker = {"called": False}

    def mock_main():
        call_tracker["called"] = True

    # Mock the imported main function
    monkeypatch.setattr("pychub.runtime.actions.runtime_main.main", mock_main)

    # Load __main__.py as if it's being executed
    main_path = Path(__file__).parents[3] / "src" / "pychub" / "runtime" / "__main__.py"
    spec = importlib.util.spec_from_file_location("__main__", main_path)
    module = importlib.util.module_from_spec(spec)
    module.__package__ = "pychub.runtime"

    # Set __name__ to trigger the if-block
    module.__name__ = "__main__"

    # Execute the module
    spec.loader.exec_module(module)

    # Verify the mocked main was called
    assert call_tracker["called"], "main() should be called when __name__ == '__main__'"