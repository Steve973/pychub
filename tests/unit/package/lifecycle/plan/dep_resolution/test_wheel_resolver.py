from pathlib import Path
from unittest.mock import Mock, MagicMock, patch

import pytest

from pychub.package.lifecycle.plan.dep_resolution.wheel_resolver import (
    parse_requires_dist,
    resolve_dependency_graph
)


# Tests for parse_requires_dist

def test_parse_requires_dist_with_dependencies():
    """Test parsing Requires-Dist from wheel with dependencies."""
    mock_metadata = """Metadata-Version: 2.1
Name: test-package
Version: 1.0.0
Requires-Dist: requests>=2.0.0
Requires-Dist: pytest>=7.0.0; extra == "test"
Requires-Dist: numpy>=1.20.0
"""

    mock_zipfile = MagicMock()
    mock_zipfile.__enter__.return_value = mock_zipfile
    mock_zipfile.__exit__.return_value = None
    mock_zipfile.namelist.return_value = ["test_package-1.0.0.dist-info/METADATA", "other_file.py"]
    mock_zipfile.read.return_value = mock_metadata.encode("utf-8")

    with patch("zipfile.ZipFile", return_value=mock_zipfile):
        wheel_path = Path("/fake/path/test_package-1.0.0-py3-none-any.whl")
        result = parse_requires_dist(wheel_path)

    assert len(result) == 3
    assert "requests>=2.0.0" in result
    assert "pytest>=7.0.0; extra == \"test\"" in result
    assert "numpy>=1.20.0" in result


def test_parse_requires_dist_no_dependencies():
    """Test parsing wheel with no dependencies."""
    mock_metadata = """Metadata-Version: 2.1
Name: test-package
Version: 1.0.0
"""

    mock_zipfile = MagicMock()
    mock_zipfile.__enter__.return_value = mock_zipfile
    mock_zipfile.__exit__.return_value = None
    mock_zipfile.namelist.return_value = ["test_package-1.0.0.dist-info/METADATA"]
    mock_zipfile.read.return_value = mock_metadata.encode("utf-8")

    with patch("zipfile.ZipFile", return_value=mock_zipfile):
        wheel_path = Path("/fake/path/test_package-1.0.0-py3-none-any.whl")
        result = parse_requires_dist(wheel_path)

    assert result == []


def test_parse_requires_dist_no_metadata_file():
    """Test parsing wheel without METADATA file."""
    mock_zipfile = MagicMock()
    mock_zipfile.__enter__.return_value = mock_zipfile
    mock_zipfile.__exit__.return_value = None
    mock_zipfile.namelist.return_value = ["some_file.py", "other_file.py"]

    with patch("zipfile.ZipFile", return_value=mock_zipfile):
        wheel_path = Path("/fake/path/test_package-1.0.0-py3-none-any.whl")
        result = parse_requires_dist(wheel_path)

    assert result == []


def test_parse_requires_dist_metadata_with_encoding_errors():
    """Test parsing METADATA with encoding issues."""
    # Create metadata with some invalid UTF-8 bytes that should be replaced
    mock_metadata = b"Metadata-Version: 2.1\nName: test\nRequires-Dist: requests>=2.0.0\n"

    mock_zipfile = MagicMock()
    mock_zipfile.__enter__.return_value = mock_zipfile
    mock_zipfile.__exit__.return_value = None
    mock_zipfile.namelist.return_value = ["test-1.0.0.dist-info/METADATA"]
    mock_zipfile.read.return_value = mock_metadata

    with patch("zipfile.ZipFile", return_value=mock_zipfile):
        wheel_path = Path("/fake/path/test-1.0.0-py3-none-any.whl")
        result = parse_requires_dist(wheel_path)

    assert len(result) == 1
    assert "requests>=2.0.0" in result


def test_parse_requires_dist_multiple_dist_info_dirs():
    """Test parsing wheel with multiple .dist-info directories (picks first)."""
    mock_metadata = """Metadata-Version: 2.1
Name: test-package
Version: 1.0.0
Requires-Dist: requests>=2.0.0
"""

    mock_zipfile = MagicMock()
    mock_zipfile.__enter__.return_value = mock_zipfile
    mock_zipfile.__exit__.return_value = None
    mock_zipfile.namelist.return_value = [
        "test_package-1.0.0.dist-info/METADATA",
        "another-1.0.0.dist-info/METADATA"
    ]
    mock_zipfile.read.return_value = mock_metadata.encode("utf-8")

    with patch("zipfile.ZipFile", return_value=mock_zipfile):
        wheel_path = Path("/fake/path/test_package-1.0.0-py3-none-any.whl")
        result = parse_requires_dist(wheel_path)

    assert len(result) == 1
    assert "requests>=2.0.0" in result
    # Verify it read from the first METADATA file found
    mock_zipfile.read.assert_called_once_with("test_package-1.0.0.dist-info/METADATA")


# Tests for resolve_dependency_graph

def _create_mock_wheel(tmp_path, name, version, dependencies):
    """Helper to create a mock wheel file with metadata."""
    wheel_path = tmp_path / f"{name}-{version}-py3-none-any.whl"
    wheel_path.touch()

    # Create metadata content
    metadata = f"Metadata-Version: 2.1\nName: {name}\nVersion: {version}\n"
    for dep in dependencies:
        metadata += f"Requires-Dist: {dep}\n"

    return wheel_path, metadata


def test_resolve_dependency_graph_single_wheel_no_deps(tmp_path):
    """Test resolving a single wheel with no dependencies."""
    wheel_path, metadata = _create_mock_wheel(tmp_path, "test", "1.0.0", [])
    output_dir = tmp_path / "output"
    output_dir.mkdir()

    mock_zipfile = MagicMock()
    mock_zipfile.__enter__.return_value = mock_zipfile
    mock_zipfile.__exit__.return_value = None
    mock_zipfile.namelist.return_value = ["test-1.0.0.dist-info/METADATA"]
    mock_zipfile.read.return_value = metadata.encode("utf-8")

    with patch("zipfile.ZipFile", return_value=mock_zipfile):
        strategies = []
        result = resolve_dependency_graph([wheel_path], output_dir, strategies)

    assert len(result) == 1
    assert "test" in result
    assert result["test"] == wheel_path


def test_resolve_dependency_graph_single_wheel_with_dep(tmp_path):
    """Test resolving a wheel with one dependency."""
    root_wheel, root_metadata = _create_mock_wheel(tmp_path, "myapp", "1.0.0", ["requests>=2.0.0"])
    dep_wheel, dep_metadata = _create_mock_wheel(tmp_path, "requests", "2.28.0", [])
    output_dir = tmp_path / "output"
    output_dir.mkdir()

    # Mock strategy that resolves requests
    mock_strategy = Mock()
    mock_strategy.resolve.return_value = dep_wheel

    mock_zipfile = MagicMock()
    mock_zipfile.__enter__.return_value = mock_zipfile
    mock_zipfile.__exit__.return_value = None

    def namelist_side_effect():
        # Return appropriate dist-info based on which wheel is being read
        return ["myapp-1.0.0.dist-info/METADATA"]

    def read_side_effect(path):
        if "myapp" in path:
            return root_metadata.encode("utf-8")
        elif "requests" in path:
            return dep_metadata.encode("utf-8")
        return b""

    mock_zipfile.namelist.side_effect = [
        ["myapp-1.0.0.dist-info/METADATA"],
        ["requests-2.28.0.dist-info/METADATA"]
    ]
    mock_zipfile.read.side_effect = [root_metadata.encode("utf-8"), dep_metadata.encode("utf-8")]

    with patch("zipfile.ZipFile", return_value=mock_zipfile):
        result = resolve_dependency_graph([root_wheel], output_dir, [mock_strategy])

    assert len(result) == 2
    assert "myapp" in result
    assert "requests" in result
    assert result["myapp"] == root_wheel
    assert result["requests"] == dep_wheel
    mock_strategy.resolve.assert_called_once_with("requests>=2.0.0", output_dir)


def test_resolve_dependency_graph_multiple_root_wheels(tmp_path):
    """Test resolving multiple root wheels."""
    wheel1, metadata1 = _create_mock_wheel(tmp_path, "app1", "1.0.0", [])
    wheel2, metadata2 = _create_mock_wheel(tmp_path, "app2", "2.0.0", [])
    output_dir = tmp_path / "output"
    output_dir.mkdir()

    mock_zipfile = MagicMock()
    mock_zipfile.__enter__.return_value = mock_zipfile
    mock_zipfile.__exit__.return_value = None
    mock_zipfile.namelist.side_effect = [
        ["app1-1.0.0.dist-info/METADATA"],
        ["app2-2.0.0.dist-info/METADATA"]
    ]
    mock_zipfile.read.side_effect = [metadata1.encode("utf-8"), metadata2.encode("utf-8")]

    with patch("zipfile.ZipFile", return_value=mock_zipfile):
        result = resolve_dependency_graph([wheel1, wheel2], output_dir, [])

    assert len(result) == 2
    assert "app1" in result
    assert "app2" in result
    assert result["app1"] == wheel1
    assert result["app2"] == wheel2


def test_resolve_dependency_graph_transitive_dependencies(tmp_path):
    """Test resolving transitive dependencies (A -> B -> C)."""
    # Create actual wheel files with proper names
    wheel_a = tmp_path / "pkg_a-1.0.0-py3-none-any.whl"
    wheel_a.touch()
    wheel_b = tmp_path / "pkg_b-1.0.0-py3-none-any.whl"
    wheel_b.touch()
    wheel_c = tmp_path / "pkg_c-1.0.0-py3-none-any.whl"
    wheel_c.touch()

    metadata_a = "Metadata-Version: 2.1\nName: pkg-a\nVersion: 1.0.0\nRequires-Dist: pkg-b>=1.0.0\n"
    metadata_b = "Metadata-Version: 2.1\nName: pkg-b\nVersion: 1.0.0\nRequires-Dist: pkg-c>=1.0.0\n"
    metadata_c = "Metadata-Version: 2.1\nName: pkg-c\nVersion: 1.0.0\n"

    output_dir = tmp_path / "output"
    output_dir.mkdir()

    mock_strategy = Mock()
    mock_strategy.resolve.side_effect = [wheel_b, wheel_c]

    def mock_zipfile_factory(path, *args, **kwargs):
        mock_zip = MagicMock()
        mock_zip.__enter__ = Mock(return_value=mock_zip)
        mock_zip.__exit__ = Mock(return_value=None)

        path_str = str(path)
        if "pkg_a" in path_str:
            mock_zip.namelist.return_value = ["pkg_a-1.0.0.dist-info/METADATA"]
            mock_zip.read.return_value = metadata_a.encode("utf-8")
        elif "pkg_b" in path_str:
            mock_zip.namelist.return_value = ["pkg_b-1.0.0.dist-info/METADATA"]
            mock_zip.read.return_value = metadata_b.encode("utf-8")
        elif "pkg_c" in path_str:
            mock_zip.namelist.return_value = ["pkg_c-1.0.0.dist-info/METADATA"]
            mock_zip.read.return_value = metadata_c.encode("utf-8")

        return mock_zip

    with patch("zipfile.ZipFile", side_effect=mock_zipfile_factory):
        result = resolve_dependency_graph([wheel_a], output_dir, [mock_strategy])

    assert len(result) == 3
    assert "pkg-a" in result
    assert "pkg-b" in result
    assert "pkg-c" in result


def test_resolve_dependency_graph_shared_dependency(tmp_path):
    """Test that shared dependencies are only resolved once."""
    wheel_a = tmp_path / "app_a-1.0.0-py3-none-any.whl"
    wheel_a.touch()
    wheel_b = tmp_path / "app_b-1.0.0-py3-none-any.whl"
    wheel_b.touch()
    wheel_shared = tmp_path / "requests-2.28.0-py3-none-any.whl"
    wheel_shared.touch()

    metadata_a = "Metadata-Version: 2.1\nName: app-a\nVersion: 1.0.0\nRequires-Dist: requests>=2.0.0\n"
    metadata_b = "Metadata-Version: 2.1\nName: app-b\nVersion: 1.0.0\nRequires-Dist: requests>=2.0.0\n"
    metadata_shared = "Metadata-Version: 2.1\nName: requests\nVersion: 2.28.0\n"

    output_dir = tmp_path / "output"
    output_dir.mkdir()

    mock_strategy = Mock()
    mock_strategy.resolve.return_value = wheel_shared

    def mock_zipfile_factory(path, *args, **kwargs):
        mock_zip = MagicMock()
        mock_zip.__enter__ = Mock(return_value=mock_zip)
        mock_zip.__exit__ = Mock(return_value=None)

        path_str = str(path)
        if "app_a" in path_str:
            mock_zip.namelist.return_value = ["app_a-1.0.0.dist-info/METADATA"]
            mock_zip.read.return_value = metadata_a.encode("utf-8")
        elif "app_b" in path_str:
            mock_zip.namelist.return_value = ["app_b-1.0.0.dist-info/METADATA"]
            mock_zip.read.return_value = metadata_b.encode("utf-8")
        elif "requests" in path_str:
            mock_zip.namelist.return_value = ["requests-2.28.0.dist-info/METADATA"]
            mock_zip.read.return_value = metadata_shared.encode("utf-8")

        return mock_zip

    with patch("zipfile.ZipFile", side_effect=mock_zipfile_factory):
        result = resolve_dependency_graph([wheel_a, wheel_b], output_dir, [mock_strategy])

    assert len(result) == 3
    assert "app-a" in result
    assert "app-b" in result
    assert "requests" in result
    assert mock_strategy.resolve.call_count == 1


def test_resolve_dependency_graph_circular_dependency(tmp_path):
    """Test handling circular dependencies (A -> B -> A)."""
    wheel_a = tmp_path / "pkg_a-1.0.0-py3-none-any.whl"
    wheel_a.touch()
    wheel_b = tmp_path / "pkg_b-1.0.0-py3-none-any.whl"
    wheel_b.touch()

    metadata_a = "Metadata-Version: 2.1\nName: pkg-a\nVersion: 1.0.0\nRequires-Dist: pkg-b>=1.0.0\n"
    metadata_b = "Metadata-Version: 2.1\nName: pkg-b\nVersion: 1.0.0\nRequires-Dist: pkg-a>=1.0.0\n"

    output_dir = tmp_path / "output"
    output_dir.mkdir()

    mock_strategy = Mock()
    mock_strategy.resolve.return_value = wheel_b

    def mock_zipfile_factory(path, *args, **kwargs):
        mock_zip = MagicMock()
        mock_zip.__enter__ = Mock(return_value=mock_zip)
        mock_zip.__exit__ = Mock(return_value=None)

        path_str = str(path)
        if "pkg_a" in path_str:
            mock_zip.namelist.return_value = ["pkg_a-1.0.0.dist-info/METADATA"]
            mock_zip.read.return_value = metadata_a.encode("utf-8")
        elif "pkg_b" in path_str:
            mock_zip.namelist.return_value = ["pkg_b-1.0.0.dist-info/METADATA"]
            mock_zip.read.return_value = metadata_b.encode("utf-8")

        return mock_zip

    with patch("zipfile.ZipFile", side_effect=mock_zipfile_factory):
        result = resolve_dependency_graph([wheel_a], output_dir, [mock_strategy])

    assert len(result) == 2
    assert "pkg-a" in result
    assert "pkg-b" in result
    assert mock_strategy.resolve.call_count == 1


def test_resolve_dependency_graph_multiple_strategies(tmp_path):
    """Test that strategies are tried in order until one succeeds."""
    root_wheel, root_metadata = _create_mock_wheel(tmp_path, "myapp", "1.0.0", ["requests>=2.0.0"])
    dep_wheel, dep_metadata = _create_mock_wheel(tmp_path, "requests", "2.28.0", [])
    output_dir = tmp_path / "output"
    output_dir.mkdir()

    # First strategy fails, second succeeds
    strategy1 = Mock()
    strategy1.resolve.side_effect = Exception("Failed")

    strategy2 = Mock()
    strategy2.resolve.return_value = dep_wheel

    mock_zipfile = MagicMock()
    mock_zipfile.__enter__.return_value = mock_zipfile
    mock_zipfile.__exit__.return_value = None
    mock_zipfile.namelist.side_effect = [
        ["myapp-1.0.0.dist-info/METADATA"],
        ["requests-2.28.0.dist-info/METADATA"]
    ]
    mock_zipfile.read.side_effect = [root_metadata.encode("utf-8"), dep_metadata.encode("utf-8")]

    with patch("zipfile.ZipFile", return_value=mock_zipfile):
        result = resolve_dependency_graph([root_wheel], output_dir, [strategy1, strategy2])

    assert len(result) == 2
    assert "requests" in result
    strategy1.resolve.assert_called_once()
    strategy2.resolve.assert_called_once()


def test_resolve_dependency_graph_all_strategies_fail(tmp_path):
    """Test error when all strategies fail to resolve a dependency."""
    root_wheel, root_metadata = _create_mock_wheel(tmp_path, "myapp", "1.0.0", ["unknown-pkg>=1.0.0"])
    output_dir = tmp_path / "output"
    output_dir.mkdir()

    strategy1 = Mock()
    strategy1.resolve.side_effect = Exception("Failed 1")

    strategy2 = Mock()
    strategy2.resolve.side_effect = Exception("Failed 2")

    mock_zipfile = MagicMock()
    mock_zipfile.__enter__.return_value = mock_zipfile
    mock_zipfile.__exit__.return_value = None
    mock_zipfile.namelist.return_value = ["myapp-1.0.0.dist-info/METADATA"]
    mock_zipfile.read.return_value = root_metadata.encode("utf-8")

    with patch("zipfile.ZipFile", return_value=mock_zipfile):
        with pytest.raises(RuntimeError, match="Could not resolve dependency unknown-pkg"):
            resolve_dependency_graph([root_wheel], output_dir, [strategy1, strategy2])


def test_resolve_dependency_graph_canonicalized_names(tmp_path):
    """Test that package names are canonicalized correctly."""
    # Wheel filename uses underscore, dependency might use dash
    wheel_path, metadata = _create_mock_wheel(tmp_path, "My_Package", "1.0.0", [])
    output_dir = tmp_path / "output"
    output_dir.mkdir()

    mock_zipfile = MagicMock()
    mock_zipfile.__enter__.return_value = mock_zipfile
    mock_zipfile.__exit__.return_value = None
    mock_zipfile.namelist.return_value = ["My_Package-1.0.0.dist-info/METADATA"]
    mock_zipfile.read.return_value = metadata.encode("utf-8")

    with patch("zipfile.ZipFile", return_value=mock_zipfile):
        result = resolve_dependency_graph([wheel_path], output_dir, [])

    # Should be canonicalized to lowercase with hyphens replaced
    assert "my-package" in result
    assert result["my-package"] == wheel_path


def test_resolve_dependency_graph_empty_root_wheels(tmp_path):
    """Test with no root wheels."""
    output_dir = tmp_path / "output"
    output_dir.mkdir()

    result = resolve_dependency_graph([], output_dir, [])

    assert result == {}


def test_resolve_dependency_graph_dependency_with_extras(tmp_path):
    """Test resolving dependencies with extras specified."""
    root_wheel, root_metadata = _create_mock_wheel(tmp_path, "myapp", "1.0.0", ["requests[security]>=2.0.0"])
    dep_wheel, dep_metadata = _create_mock_wheel(tmp_path, "requests", "2.28.0", [])
    output_dir = tmp_path / "output"
    output_dir.mkdir()

    mock_strategy = Mock()
    mock_strategy.resolve.return_value = dep_wheel

    mock_zipfile = MagicMock()
    mock_zipfile.__enter__.return_value = mock_zipfile
    mock_zipfile.__exit__.return_value = None
    mock_zipfile.namelist.side_effect = [
        ["myapp-1.0.0.dist-info/METADATA"],
        ["requests-2.28.0.dist-info/METADATA"]
    ]
    mock_zipfile.read.side_effect = [root_metadata.encode("utf-8"), dep_metadata.encode("utf-8")]

    with patch("zipfile.ZipFile", return_value=mock_zipfile):
        result = resolve_dependency_graph([root_wheel], output_dir, [mock_strategy])

    assert len(result) == 2
    assert "requests" in result
    # The full requirement string with extras should be passed to strategy
    mock_strategy.resolve.assert_called_once_with("requests[security]>=2.0.0", output_dir)


def test_resolve_dependency_graph_dependency_with_environment_markers(tmp_path):
    """Test resolving dependencies with environment markers."""
    root_wheel, root_metadata = _create_mock_wheel(tmp_path, "myapp", "1.0.0",
                                                   ['pytest>=7.0.0; python_version >= "3.8"'])
    dep_wheel, dep_metadata = _create_mock_wheel(tmp_path, "pytest", "7.0.0", [])
    output_dir = tmp_path / "output"
    output_dir.mkdir()

    mock_strategy = Mock()
    mock_strategy.resolve.return_value = dep_wheel

    mock_zipfile = MagicMock()
    mock_zipfile.__enter__.return_value = mock_zipfile
    mock_zipfile.__exit__.return_value = None
    mock_zipfile.namelist.side_effect = [
        ["myapp-1.0.0.dist-info/METADATA"],
        ["pytest-7.0.0.dist-info/METADATA"]
    ]
    mock_zipfile.read.side_effect = [root_metadata.encode("utf-8"), dep_metadata.encode("utf-8")]

    with patch("zipfile.ZipFile", return_value=mock_zipfile):
        result = resolve_dependency_graph([root_wheel], output_dir, [mock_strategy])

    assert len(result) == 2
    assert "pytest" in result
    # The requirement with markers should be passed to strategy
    mock_strategy.resolve.assert_called_once_with('pytest>=7.0.0; python_version >= "3.8"', output_dir)


def test_resolve_dependency_graph_complex_wheel_name(tmp_path):
    """Test extracting package name from complex wheel filenames."""
    # Wheel with platform-specific tags
    wheel_path = tmp_path / "numpy-1.24.0-cp311-cp311-manylinux_2_17_x86_64.manylinux2014_x86_64.whl"
    wheel_path.touch()
    metadata = "Metadata-Version: 2.1\nName: numpy\nVersion: 1.24.0\n"
    output_dir = tmp_path / "output"
    output_dir.mkdir()

    mock_zipfile = MagicMock()
    mock_zipfile.__enter__.return_value = mock_zipfile
    mock_zipfile.__exit__.return_value = None
    mock_zipfile.namelist.return_value = ["numpy-1.24.0.dist-info/METADATA"]
    mock_zipfile.read.return_value = metadata.encode("utf-8")

    with patch("zipfile.ZipFile", return_value=mock_zipfile):
        result = resolve_dependency_graph([wheel_path], output_dir, [])

    assert "numpy" in result
    assert result["numpy"] == wheel_path


def test_resolve_dependency_graph_no_strategies_no_dependencies(tmp_path):
    """Test with no strategies but also no dependencies needed."""
    wheel_path, metadata = _create_mock_wheel(tmp_path, "standalone", "1.0.0", [])
    output_dir = tmp_path / "output"
    output_dir.mkdir()

    mock_zipfile = MagicMock()
    mock_zipfile.__enter__.return_value = mock_zipfile
    mock_zipfile.__exit__.return_value = None
    mock_zipfile.namelist.return_value = ["standalone-1.0.0.dist-info/METADATA"]
    mock_zipfile.read.return_value = metadata.encode("utf-8")

    with patch("zipfile.ZipFile", return_value=mock_zipfile):
        result = resolve_dependency_graph([wheel_path], output_dir, [])

    assert len(result) == 1
    assert "standalone" in result


def test_resolve_dependency_graph_multiple_versions_same_package(tmp_path):
    """Test that when same package appears multiple times, last one wins (LIFO stack)."""
    wheel_v1, metadata_v1 = _create_mock_wheel(tmp_path, "mylib", "1.0.0", [])
    wheel_v2, metadata_v2 = _create_mock_wheel(tmp_path, "mylib", "2.0.0", [])
    output_dir = tmp_path / "output"
    output_dir.mkdir()

    mock_zipfile = MagicMock()
    mock_zipfile.__enter__.return_value = mock_zipfile
    mock_zipfile.__exit__.return_value = None
    # Stack is [wheel_v1, wheel_v2], pop() takes from end (wheel_v2 first)
    mock_zipfile.namelist.return_value = ["mylib-2.0.0.dist-info/METADATA"]
    mock_zipfile.read.return_value = metadata_v2.encode("utf-8")

    with patch("zipfile.ZipFile", return_value=mock_zipfile):
        result = resolve_dependency_graph([wheel_v1, wheel_v2], output_dir, [])

    # Only first processed (last in list due to stack LIFO) should be kept
    assert len(result) == 1
    assert "mylib" in result
    assert result["mylib"] == wheel_v2