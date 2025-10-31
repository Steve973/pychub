import sys
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from packaging.requirements import Requirement

from pychub.package.lifecycle.plan.dep_resolution.wheeldeps.index_resolution_strategy import IndexResolutionStrategy


# ============================================================================
# fetch_all_wheel_variant_urls tests
# ============================================================================

def test_fetch_all_wheel_variant_urls_with_version_constraint():
    """Test fetching wheel URLs with a specific version constraint."""
    mock_response = Mock()
    mock_response.json.return_value = {
        "info": {"version": "2.2.0"},
        "releases": {
            "2.2.0": [
                {"filename": "torch-2.2.0-cp39-cp39-linux_x86_64.whl", "url": "https://example.com/torch1.whl"},
                {"filename": "torch-2.2.0-cp310-cp310-linux_x86_64.whl", "url": "https://example.com/torch2.whl"},
                {"filename": "torch-2.2.0.tar.gz", "url": "https://example.com/torch.tar.gz"},
            ],
            "2.1.0": [
                {"filename": "torch-2.1.0-cp39-cp39-linux_x86_64.whl", "url": "https://example.com/torch_old.whl"},
            ],
        },
    }
    mock_response.raise_for_status = Mock()

    with patch("requests.get", return_value=mock_response) as mock_get:
        urls = IndexResolutionStrategy.fetch_all_wheel_variant_urls("torch==2.2.0")

        mock_get.assert_called_once_with("https://pypi.org/pypi/torch/json", timeout=10)
        assert len(urls) == 2
        assert "https://example.com/torch1.whl" in urls
        assert "https://example.com/torch2.whl" in urls
        assert "https://example.com/torch.tar.gz" not in urls


def test_fetch_all_wheel_variant_urls_without_version_constraint():
    """Test fetching wheel URLs for the latest version when no version is specified."""
    mock_response = Mock()
    mock_response.json.return_value = {
        "info": {"version": "3.0.0"},
        "releases": {
            "3.0.0": [
                {"filename": "package-3.0.0-py3-none-any.whl", "url": "https://example.com/pkg3.whl"},
            ],
            "2.0.0": [
                {"filename": "package-2.0.0-py3-none-any.whl", "url": "https://example.com/pkg2.whl"},
            ],
        },
    }
    mock_response.raise_for_status = Mock()

    with patch("requests.get", return_value=mock_response):
        urls = IndexResolutionStrategy.fetch_all_wheel_variant_urls("package")

        assert len(urls) == 1
        assert urls[0] == "https://example.com/pkg3.whl"


def test_fetch_all_wheel_variant_urls_with_custom_index():
    """Test fetching from a custom index URL."""
    mock_response = Mock()
    mock_response.json.return_value = {
        "info": {"version": "1.0.0"},
        "releases": {
            "1.0.0": [
                {"filename": "pkg-1.0.0-py3-none-any.whl", "url": "https://custom.com/pkg.whl"},
            ],
        },
    }
    mock_response.raise_for_status = Mock()

    with patch("requests.get", return_value=mock_response) as mock_get:
        urls = IndexResolutionStrategy.fetch_all_wheel_variant_urls(
            "pkg==1.0.0",
            index_url="https://custom.index/simple"
        )

        mock_get.assert_called_once_with("https://custom.index/simple/pkg/json", timeout=10)
        assert urls == ["https://custom.com/pkg.whl"]


def test_fetch_all_wheel_variant_urls_invalid_requirement():
    """Test that an invalid requirement string raises ValueError."""
    with pytest.raises(ValueError, match="Could not parse requirement"):
        IndexResolutionStrategy.fetch_all_wheel_variant_urls("invalid requirement !!!")


def test_fetch_all_wheel_variant_urls_network_error():
    """Test handling of network errors when fetching package metadata."""
    with patch("requests.get", side_effect=Exception("Network error")):
        with pytest.raises(RuntimeError, match="Failed to fetch metadata for torch"):
            IndexResolutionStrategy.fetch_all_wheel_variant_urls("torch==2.2.0")


def test_fetch_all_wheel_variant_urls_no_wheels_found():
    """Test that RuntimeError is raised when no wheels are found."""
    mock_response = Mock()
    mock_response.json.return_value = {
        "info": {"version": "1.0.0"},
        "releases": {
            "1.0.0": [
                {"filename": "package-1.0.0.tar.gz", "url": "https://example.com/pkg.tar.gz"},
            ],
        },
    }
    mock_response.raise_for_status = Mock()

    with patch("requests.get", return_value=mock_response):
        with pytest.raises(RuntimeError, match="No wheel variants found for package==1.0.0"):
            IndexResolutionStrategy.fetch_all_wheel_variant_urls("package==1.0.0")


def test_fetch_all_wheel_variant_urls_version_range():
    """Test fetching wheels with a version range specifier."""
    mock_response = Mock()
    mock_response.json.return_value = {
        "info": {"version": "2.5.0"},
        "releases": {
            "2.5.0": [
                {"filename": "pkg-2.5.0-py3-none-any.whl", "url": "https://example.com/pkg25.whl"},
            ],
            "2.4.0": [
                {"filename": "pkg-2.4.0-py3-none-any.whl", "url": "https://example.com/pkg24.whl"},
            ],
            "2.3.0": [
                {"filename": "pkg-2.3.0-py3-none-any.whl", "url": "https://example.com/pkg23.whl"},
            ],
            "2.0.0": [
                {"filename": "pkg-2.0.0-py3-none-any.whl", "url": "https://example.com/pkg20.whl"},
            ],
        },
    }
    mock_response.raise_for_status = Mock()

    with patch("requests.get", return_value=mock_response):
        urls = IndexResolutionStrategy.fetch_all_wheel_variant_urls("pkg>=2.3.0,<2.5.0")

        assert len(urls) == 2
        assert "https://example.com/pkg24.whl" in urls
        assert "https://example.com/pkg23.whl" in urls


def test_fetch_all_wheel_variant_urls_no_url_in_file_entry():
    """Test handling when a file entry doesn't have a URL field."""
    mock_response = Mock()
    mock_response.json.return_value = {
        "info": {"version": "1.0.0"},
        "releases": {
            "1.0.0": [
                {"filename": "pkg-1.0.0-py3-none-any.whl"},  # No URL
                {"filename": "pkg-1.0.0-cp39-cp39-linux_x86_64.whl", "url": "https://example.com/pkg.whl"},
            ],
        },
    }
    mock_response.raise_for_status = Mock()

    with patch("requests.get", return_value=mock_response):
        urls = IndexResolutionStrategy.fetch_all_wheel_variant_urls("pkg==1.0.0")

        assert len(urls) == 1
        assert urls[0] == "https://example.com/pkg.whl"


# ============================================================================
# _version_matches tests
# ============================================================================

def test_version_matches_with_exact_version():
    """Test version matching with exact version specifier."""
    req = Requirement("package==2.0.0")
    assert IndexResolutionStrategy._version_matches("2.0.0", req) is True
    assert IndexResolutionStrategy._version_matches("2.0.1", req) is False


def test_version_matches_with_range():
    """Test version matching with range specifiers."""
    req = Requirement("package>=1.0.0,<2.0.0")
    assert IndexResolutionStrategy._version_matches("1.5.0", req) is True
    assert IndexResolutionStrategy._version_matches("2.0.0", req) is False
    assert IndexResolutionStrategy._version_matches("0.9.0", req) is False


def test_version_matches_with_invalid_version():
    """Test that invalid version strings don't match."""
    req = Requirement("package==2.0.0")
    assert IndexResolutionStrategy._version_matches("not-a-version", req) is False


def test_version_matches_with_no_specifier():
    """Test that versions match when no specifier is provided."""
    req = Requirement("package")
    assert IndexResolutionStrategy._version_matches("1.0.0", req) is True
    assert IndexResolutionStrategy._version_matches("2.5.0", req) is True


def test_version_matches_with_prerelease():
    """Test version matching includes prereleases."""
    req = Requirement("package<=2.0.0")
    assert IndexResolutionStrategy._version_matches("2.0.0a1", req) is True
    assert IndexResolutionStrategy._version_matches("2.0.0rc1", req) is True


# ============================================================================
# resolve tests
# ============================================================================

def test_resolve_downloads_wheels_successfully(tmp_path):
    """Test successful wheel download and resolution."""
    output_dir = tmp_path / "wheels"

    # Create mock wheel files that will appear after download
    output_dir.mkdir(parents=True)
    wheel1 = output_dir / "torch-2.2.0-cp39-linux.whl"
    wheel2 = output_dir / "torch-2.2.0-cp310-linux.whl"

    mock_result = Mock()
    mock_result.returncode = 0
    mock_result.stderr = ""

    with patch.object(IndexResolutionStrategy, "fetch_all_wheel_variant_urls",
                      return_value=["https://example.com/torch1.whl", "https://example.com/torch2.whl"]):
        with patch("subprocess.run", return_value=mock_result):
            with patch.object(Path, "glob") as mock_glob:
                # First call returns empty set (before), second call returns wheels (after)
                mock_glob.side_effect = [
                    iter([]),  # before
                    iter([wheel1, wheel2])  # after
                ]

                # Create the actual files so resolve() can process them
                wheel1.touch()
                wheel2.touch()

                strategy = IndexResolutionStrategy()
                result = strategy.resolve("torch==2.2.0", output_dir)

                assert len(result) == 2
                assert all(isinstance(p, Path) for p in result)


def test_resolve_creates_output_directory(tmp_path):
    """Test that resolve creates the output directory if it doesn't exist."""
    output_dir = tmp_path / "nonexistent" / "wheels"

    mock_result = Mock()
    mock_result.returncode = 0
    mock_result.stderr = ""

    wheel1 = output_dir / "pkg-1.0.0-py3-none-any.whl"

    with patch.object(IndexResolutionStrategy, "fetch_all_wheel_variant_urls",
                      return_value=["https://example.com/pkg.whl"]):
        with patch("subprocess.run", return_value=mock_result):
            with patch.object(Path, "glob") as mock_glob:
                mock_glob.side_effect = [
                    iter([]),  # before
                    iter([wheel1])  # after
                ]

                output_dir.mkdir(parents=True)
                wheel1.touch()

                strategy = IndexResolutionStrategy()
                result = strategy.resolve("pkg==1.0.0", output_dir)

                assert output_dir.exists()
                assert len(result) == 1


def test_resolve_pip_download_fails(tmp_path):
    """Test handling of pip download failure."""
    output_dir = tmp_path / "wheels"
    output_dir.mkdir()

    mock_result = Mock()
    mock_result.returncode = 1
    mock_result.stderr = "ERROR: Could not find a version that satisfies the requirement"

    with patch.object(IndexResolutionStrategy, "fetch_all_wheel_variant_urls",
                      return_value=["https://example.com/pkg.whl"]):
        with patch("subprocess.run", return_value=mock_result):
            strategy = IndexResolutionStrategy()
            with pytest.raises(RuntimeError, match="pip download failed for pkg==1.0.0"):
                strategy.resolve("pkg==1.0.0", output_dir)


def test_resolve_no_wheels_downloaded(tmp_path):
    """Test error when no wheels are actually downloaded."""
    output_dir = tmp_path / "wheels"
    output_dir.mkdir()

    mock_result = Mock()
    mock_result.returncode = 0
    mock_result.stderr = ""

    with patch.object(IndexResolutionStrategy, "fetch_all_wheel_variant_urls",
                      return_value=["https://example.com/pkg.whl"]):
        with patch("subprocess.run", return_value=mock_result):
            with patch.object(Path, "glob") as mock_glob:
                # Both calls return empty (no wheels before or after)
                mock_glob.side_effect = [iter([]), iter([])]

                strategy = IndexResolutionStrategy()
                with pytest.raises(RuntimeError, match="No wheels downloaded for pkg==1.0.0"):
                    strategy.resolve("pkg==1.0.0", output_dir)


def test_resolve_constructs_correct_pip_command(tmp_path):
    """Test that the pip download command is constructed correctly."""
    output_dir = tmp_path / "wheels"
    output_dir.mkdir()

    wheel1 = output_dir / "pkg-1.0.0-py3-none-any.whl"

    mock_result = Mock()
    mock_result.returncode = 0
    mock_result.stderr = ""

    wheel_urls = ["https://example.com/pkg1.whl", "https://example.com/pkg2.whl"]

    with patch.object(IndexResolutionStrategy, "fetch_all_wheel_variant_urls",
                      return_value=wheel_urls):
        with patch("subprocess.run", return_value=mock_result) as mock_run:
            with patch.object(Path, "glob") as mock_glob:
                mock_glob.side_effect = [iter([]), iter([wheel1])]
                wheel1.touch()

                strategy = IndexResolutionStrategy()
                strategy.resolve("pkg==1.0.0", output_dir)

                expected_cmd = [
                                   sys.executable, "-m", "pip", "download",
                                   "--only-binary", ":all:",
                                   "--no-deps",
                                   "-d", str(output_dir),
                               ] + wheel_urls

                mock_run.assert_called_once()
                actual_cmd = mock_run.call_args[0][0]
                assert actual_cmd == expected_cmd


def test_resolve_returns_resolved_paths(tmp_path):
    """Test that resolve returns resolved (absolute) paths."""
    output_dir = tmp_path / "wheels"
    output_dir.mkdir()

    wheel1 = output_dir / "pkg-1.0.0-py3-none-any.whl"
    wheel2 = output_dir / "pkg-1.0.0-cp39-linux.whl"

    mock_result = Mock()
    mock_result.returncode = 0

    with patch.object(IndexResolutionStrategy, "fetch_all_wheel_variant_urls",
                      return_value=["https://example.com/pkg.whl"]):
        with patch("subprocess.run", return_value=mock_result):
            with patch.object(Path, "glob") as mock_glob:
                mock_glob.side_effect = [iter([]), iter([wheel1, wheel2])]
                wheel1.touch()
                wheel2.touch()

                strategy = IndexResolutionStrategy()
                result = strategy.resolve("pkg==1.0.0", output_dir)

                assert all(p.is_absolute() for p in result)


# ============================================================================
# Integration-style tests for the strategy name
# ============================================================================

def test_strategy_has_correct_name():
    """Test that the strategy has the correct name attribute."""
    strategy = IndexResolutionStrategy()
    assert strategy.name == "index"