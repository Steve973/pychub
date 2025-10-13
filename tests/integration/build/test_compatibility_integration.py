import pytest
from pychub.package import compatibility

@pytest.mark.integration
def test_fetch_all_wheel_variants_for_dependencies():
    # Choose a few common, reasonably small deps with multiple wheel variants
    deps = ["attrs>=22.0.0", "packaging", "pyyaml"]
    result = compatibility.fetch_all_wheel_variants(*deps)

    # Validate the result is a dict with all requested keys
    assert isinstance(result, dict)
    for dep in ["attrs", "packaging", "pyyaml"]:
        assert dep in result
        wheels = result[dep]
        assert isinstance(wheels, list)
        assert wheels, f"No wheels found for {dep}"
        for wheel_info in wheels:
            # Should be a dict with expected keys
            assert isinstance(wheel_info, dict)
            assert "filename" in wheel_info
            assert wheel_info["filename"].endswith(".whl")
            assert "url" in wheel_info
            assert "version" in wheel_info
            assert wheel_info["url"].startswith("https://files.pythonhosted.org/packages/")
            assert "tags" in wheel_info
            assert isinstance(wheel_info["tags"], frozenset)
            for tag in wheel_info["tags"]:
                assert hasattr(tag, "interpreter")
                assert hasattr(tag, "abi")
                assert hasattr(tag, "platform")
