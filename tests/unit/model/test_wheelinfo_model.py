from __future__ import annotations

import json
import re
from email.parser import Parser
from importlib import resources
from typing import Any, Mapping

import pytest

from pychub.model.wheelinfo_model import WheelInfo, ExtrasInfo, SourceInfo

# ---------- helpers (test-local) ----------

EXTRA_RE = re.compile(r"""extra\s*==\s*['"]([^'"]+)['"]""")

def parse_metadata_text_to_dict(text: str) -> dict[str, Any]:
    """Turn RFC822 METADATA text into the dict shape your code expects."""
    msg = Parser().parsestr(text)

    def many(name: str) -> list[str]:
        vals = msg.get_all(name) or []
        return [v.strip() for v in vals if v and v.strip()]

    meta: dict[str, Any] = {
        "name": msg.get("Name"),
        "version": msg.get("Version"),
        "requires_python": msg.get("Requires-Python"),
        "provides_extra": many("Provides-Extra"),
        "requires_dist": many("Requires-Dist"),
    }
    # drop Nones
    return {k: v for k, v in meta.items() if v is not None}

def expected_extras_from_text(text: str) -> dict[str, list[str]]:
    """
    Compute the expected {extra: [spec,...]} mapping directly from raw METADATA text,
    by reading Requires-Dist lines and extracting the 'extra == "..."' markers.
    """
    expected: dict[str, list[str]] = {}
    for line in text.splitlines():
        if not line.startswith("Requires-Dist:"):
            continue
        body = line.split(":", 1)[1].strip()
        if ";" in body:
            spec, marker = body.split(";", 1)
            m = EXTRA_RE.search(marker)
            if m:
                extra = m.group(1)
                expected.setdefault(extra, [])
                spec = spec.strip()
                if spec not in expected[extra]:
                    expected[extra].append(spec)
    # Ensure declared extras exist even if no gated deps
    for line in text.splitlines():
        if line.startswith("Provides-Extra:"):
            name = line.split(":", 1)[1].strip()
            expected.setdefault(name, [])
    return expected


# ---------- fixtures ----------

@pytest.fixture(scope="module")
def metadata_text() -> str:
    """
    Load tests data: test_data/wheel_metadata.txt
    (Make sure test_data is a package with that file included.)
    """
    with resources.files("tests.test_data").joinpath("wheel_metadata.txt").open("r", encoding="utf-8") as f:
        return f.read()

@pytest.fixture(scope="module")
def metadata_dict(metadata_text: str) -> dict[str, Any]:
    return parse_metadata_text_to_dict(metadata_text)


# ---------- tests ----------

def test_extrasinfo_groups_match_metadata_markers(metadata_text: str, metadata_dict: Mapping[str, Any]):
    # What ExtrasInfo computes from METADATA
    extras = ExtrasInfo.from_metadata(metadata_dict).to_mapping()

    # What we expect by regexing the raw lines
    expected = expected_extras_from_text(metadata_text)

    # Must have the same extra names
    assert set(extras.keys()) == set(expected.keys())

    # And each list of specs should match exactly (order doesn’t strictly matter, but we preserved it)
    for name, specs in expected.items():
        assert extras.get(name, []) == specs


def test_wheelinfo_includes_extras(metadata_dict: Mapping[str, Any]):
    """
    Build a minimal WheelInfo using the parsed METADATA, then ensure extras are present
    and survive a to_mapping() round-trip.
    """
    # Build ExtrasInfo from METADATA
    extras = ExtrasInfo.from_metadata(metadata_dict)

    # Minimal WheelInfo (fill required fields; you can adapt if your signature differs)
    wi = WheelInfo(
        filename=(metadata_dict.get("name") or "pkg") + ".whl",
        name=metadata_dict.get("name") or "pkg",
        version=metadata_dict.get("version") or "0",
        size=0,
        sha256="",
        tags=[],
        requires_python=metadata_dict.get("requires_python"),
        deps=[],                  # base deps not under extras are outside this test’s scope
        source=None,
        meta=dict(metadata_dict),
        wheel={},
        extras=extras)

    # Has extras
    assert wi.extras.to_mapping()  # non-empty dict or {} if the fixture has none

    # Round-trip via to_mapping preserves extras
    mapping = wi.to_mapping()
    assert "extras" in mapping
    assert isinstance(mapping["extras"], dict)
    # spot check: extras in mapping match the constructed ExtrasInfo
    assert mapping["extras"] == wi.extras.to_mapping()


def test_wheelinfo_matches_testdata(metadata_dict: Mapping[str, Any]):
    wi = WheelInfo(
        filename=f"{metadata_dict.get('name','pkg')}.whl",
        name=metadata_dict.get("name") or "pkg",
        version=metadata_dict.get("version") or "0",
        size=0,
        sha256="",
        tags=[],
        requires_python=metadata_dict.get("requires_python"),
        deps=[],  # you can parse base deps too if you want
        source=None,
        meta=dict(metadata_dict),
        wheel={},
        extras=ExtrasInfo.from_metadata(metadata_dict))
    current = wi.to_mapping()

    testdata_path = resources.files("tests.test_data").joinpath("wheelinfo.json")
    if not testdata_path.is_file():
        pytest.skip("Test data file wheelinfo.json missing")

    testdata = json.loads(testdata_path.read_text(encoding="utf-8"))

    assert current == testdata


# ============================================================================
# SourceInfo tests
# ============================================================================

def test_sourceinfo_to_mapping_minimal():
    """Test SourceInfo.to_mapping with minimal fields."""
    si = SourceInfo(type="local")
    assert si.to_mapping() == {"type": "local"}


def test_sourceinfo_to_mapping_complete():
    """Test SourceInfo.to_mapping with all fields populated."""
    si = SourceInfo(
        type="index",
        url="https://example.com/pkg.whl",
        index_url="https://pypi.org/simple",
        downloaded_at="2025-01-15T10:30:00Z"
    )
    result = si.to_mapping()
    assert result == {
        "type": "index",
        "url": "https://example.com/pkg.whl",
        "index_url": "https://pypi.org/simple",
        "downloaded_at": "2025-01-15T10:30:00Z"
    }


# ============================================================================
# ExtrasInfo tests - constructors
# ============================================================================

def test_extrasinfo_from_mapping_empty():
    """Test ExtrasInfo.from_mapping with empty dict."""
    ei = ExtrasInfo.from_mapping({})
    assert ei.extras == {}
    assert len(ei) == 0
    assert not ei


def test_extrasinfo_from_mapping_with_data():
    """Test ExtrasInfo.from_mapping with populated data."""
    data = {"dev": ["pytest>=7.0"], "docs": ["sphinx>=4.0"]}
    ei = ExtrasInfo.from_mapping(data)
    assert ei.get("dev") == ["pytest>=7.0"]
    assert ei.get("docs") == ["sphinx>=4.0"]
    assert len(ei) == 2
    assert ei  # __bool__ should return True


def test_extrasinfo_from_lists_no_extras():
    """Test ExtrasInfo.from_lists with no extras declared."""
    ei = ExtrasInfo.from_lists([], [])
    assert ei.extras == {}


def test_extrasinfo_from_lists_with_base_deps_only():
    """Test ExtrasInfo.from_lists filters out base deps (no extra marker)."""
    requires = ["requests>=2.0", "urllib3>=1.26"]
    ei = ExtrasInfo.from_lists([], requires)
    # Base deps without extra markers should not appear
    assert ei.extras == {}


def test_extrasinfo_from_lists_preserves_declared_empty_extras():
    """Test that declared extras with no deps still appear."""
    provides = ["test", "dev"]
    ei = ExtrasInfo.from_lists(provides, [])
    assert "test" in ei.extras
    assert "dev" in ei.extras
    assert ei.extras["test"] == []
    assert ei.extras["dev"] == []


def test_extrasinfo_get_nonexistent():
    """Test ExtrasInfo.get() returns empty list for nonexistent extra."""
    ei = ExtrasInfo.from_mapping({"dev": ["pytest"]})
    assert ei.get("nonexistent") == []


def test_extrasinfo_names():
    """Test ExtrasInfo.names() returns list of extra names."""
    ei = ExtrasInfo.from_mapping({"dev": ["pytest"], "docs": ["sphinx"]})
    names = ei.names()
    assert set(names) == {"dev", "docs"}


# ============================================================================
# WheelInfo tests - to_mapping with empty/missing fields
# ============================================================================

def test_wheelinfo_to_mapping_minimal():
    """Test WheelInfo.to_mapping with minimal required fields."""
    wi = WheelInfo(
        filename="pkg-1.0-py3-none-any.whl",
        name="pkg",
        version="1.0",
        size=1024,
        sha256="abc123"
    )
    result = wi.to_mapping()
    assert result["name"] == "pkg"
    assert result["version"] == "1.0"
    assert result["sha256"] == "abc123"
    assert result["size"] == 1024
    assert result["tags"] == []
    assert "requires_python" not in result
    assert "deps" not in result
    assert "extras" not in result
    assert "source" not in result
    assert "meta" not in result
    assert "wheel" not in result


def test_wheelinfo_to_mapping_with_all_fields():
    """Test WheelInfo.to_mapping with all fields populated."""
    si = SourceInfo(type="index", url="https://example.com/pkg.whl")
    ei = ExtrasInfo.from_mapping({"dev": ["pytest"]})

    wi = WheelInfo(
        filename="pkg-1.0-py3-none-any.whl",
        name="pkg",
        version="1.0",
        size=1024,
        sha256="abc123",
        tags=["py3-none-any"],
        requires_python=">=3.9",
        deps=["requests>=2.0"],
        extras=ei,
        source=si,
        meta={"summary": "A package"},
        wheel={"wheel_version": "1.0"}
    )

    result = wi.to_mapping()
    assert "requires_python" in result
    assert "deps" in result
    assert "extras" in result
    assert "source" in result
    assert "meta" in result
    assert "wheel" in result


# ============================================================================
# WheelInfo tests - from_mapping
# ============================================================================

def test_wheelinfo_from_mapping_minimal():
    """Test WheelInfo.from_mapping with minimal data."""
    data = {
        "name": "pkg",
        "version": "1.0",
        "size": 1024,
        "sha256": "abc123"
    }
    wi = WheelInfo.from_mapping("pkg-1.0.whl", data)
    assert wi.filename == "pkg-1.0.whl"
    assert wi.name == "pkg"
    assert wi.version == "1.0"
    assert wi.size == 1024
    assert wi.sha256 == "abc123"
    assert wi.tags == []
    assert wi.requires_python is None
    assert wi.deps == []
    assert wi.source is None


def test_wheelinfo_from_mapping_with_source():
    """Test WheelInfo.from_mapping with source info."""
    data = {
        "name": "pkg",
        "version": "1.0",
        "size": 1024,
        "sha256": "abc123",
        "source": {
            "type": "index",
            "url": "https://example.com/pkg.whl"
        }
    }
    wi = WheelInfo.from_mapping("pkg-1.0.whl", data)
    assert wi.source is not None
    assert wi.source.type == "index"
    assert wi.source.url == "https://example.com/pkg.whl"


def test_wheelinfo_from_mapping_requires_python():
    """Test WheelInfo.from_mapping with requires_python."""
    data = {
        "name": "pkg",
        "version": "1.0",
        "size": 1024,
        "sha256": "abc123",
        "requires_python": ">=3.9"
    }
    wi = WheelInfo.from_mapping("pkg-1.0.whl", data)
    assert wi.requires_python == ">=3.9"


def test_wheelinfo_from_mapping_with_deps():
    """Test WheelInfo.from_mapping with dependencies."""
    data = {
        "name": "pkg",
        "version": "1.0",
        "size": 1024,
        "sha256": "abc123",
        "deps": ["requests>=2.0", "urllib3>=1.26"]
    }
    wi = WheelInfo.from_mapping("pkg-1.0.whl", data)
    assert wi.deps == ["requests>=2.0", "urllib3>=1.26"]


# ============================================================================
# WheelInfo tests - build_from_wheel error cases
# ============================================================================

def test_wheelinfo_build_from_wheel_missing_name(tmp_path, monkeypatch):
    """Test build_from_wheel raises ValueError when Name is missing."""
    wheel_path = tmp_path / "test-1.0-py3-none-any.whl"
    wheel_path.touch()

    # Mock to return metadata without Name
    def mock_read_headers(path, suffix):
        if "METADATA" in suffix:
            return {"Version": ["1.0"]}
        return {}

    monkeypatch.setattr(
        "pychub.model.wheelinfo_model._read_headers_from_wheel",
        mock_read_headers
    )

    with pytest.raises(ValueError, match="METADATA missing Name/Version"):
        WheelInfo.build_from_wheel(wheel_path)


def test_wheelinfo_build_from_wheel_missing_version(tmp_path, monkeypatch):
    """Test build_from_wheel raises ValueError when Version is missing."""
    wheel_path = tmp_path / "test-1.0-py3-none-any.whl"
    wheel_path.touch()

    # Mock to return metadata without Version
    def mock_read_headers(path, suffix):
        if "METADATA" in suffix:
            return {"Name": ["test-pkg"]}
        return {}

    monkeypatch.setattr(
        "pychub.model.wheelinfo_model._read_headers_from_wheel",
        mock_read_headers
    )

    with pytest.raises(ValueError, match="METADATA missing Name/Version"):
        WheelInfo.build_from_wheel(wheel_path)


def test_wheelinfo_build_from_wheel_with_deps_and_source(tmp_path, monkeypatch):
    """Test build_from_wheel with deps and source parameters."""
    wheel_path = tmp_path / "test-1.0-py3-none-any.whl"
    wheel_path.touch()

    def mock_read_headers(path, suffix):
        if "METADATA" in suffix:
            return {"Name": ["test-pkg"], "Version": ["1.0"]}
        return {}

    monkeypatch.setattr(
        "pychub.model.wheelinfo_model._read_headers_from_wheel",
        mock_read_headers
    )

    source = SourceInfo(type="local")
    wi = WheelInfo.build_from_wheel(
        wheel_path,
        deps=["requests>=2.0"],
        source=source
    )

    assert wi.deps == ["requests>=2.0"]
    assert wi.source == source


# ============================================================================
# Helper function tests
# ============================================================================

def test_meta_list_with_none():
    """Test _meta_list handles None."""
    from pychub.model.wheelinfo_model import _meta_list
    assert _meta_list(None) == []


def test_meta_list_with_string():
    """Test _meta_list handles single string."""
    from pychub.model.wheelinfo_model import _meta_list
    assert _meta_list("value") == ["value"]


def test_meta_list_with_list():
    """Test _meta_list handles list."""
    from pychub.model.wheelinfo_model import _meta_list
    assert _meta_list(["a", "b"]) == ["a", "b"]


def test_split_req_marker_with_marker():
    """Test _split_req_marker with marker present."""
    from pychub.model.wheelinfo_model import _split_req_marker
    spec, marker = _split_req_marker("pytest>=7.0; extra == 'test'")
    assert spec == "pytest>=7.0"
    assert marker == "extra == 'test'"


def test_split_req_marker_without_marker():
    """Test _split_req_marker without marker."""
    from pychub.model.wheelinfo_model import _split_req_marker
    spec, marker = _split_req_marker("pytest>=7.0")
    assert spec == "pytest>=7.0"
    assert marker is None


def test_extract_extra_name_with_double_quotes():
    """Test _extract_extra_name with double quotes."""
    from pychub.model.wheelinfo_model import _extract_extra_name
    name = _extract_extra_name('extra == "dev"')
    assert name == "dev"


def test_extract_extra_name_with_single_quotes():
    """Test _extract_extra_name with single quotes."""
    from pychub.model.wheelinfo_model import _extract_extra_name
    name = _extract_extra_name("extra == 'test'")
    assert name == "test"


def test_extract_extra_name_no_match():
    """Test _extract_extra_name when no extra marker."""
    from pychub.model.wheelinfo_model import _extract_extra_name
    name = _extract_extra_name("python_version >= '3.9'")
    assert name is None


def test_extract_extra_name_with_none():
    """Test _extract_extra_name with None."""
    from pychub.model.wheelinfo_model import _extract_extra_name
    name = _extract_extra_name(None)
    assert name is None


def test_append_dedup_adds_new_item():
    """Test _append_dedup adds new item."""
    from pychub.model.wheelinfo_model import _append_dedup
    bucket = ["a", "b"]
    _append_dedup(bucket, "c")
    assert bucket == ["a", "b", "c"]


def test_append_dedup_skips_duplicate():
    """Test _append_dedup skips existing item."""
    from pychub.model.wheelinfo_model import _append_dedup
    bucket = ["a", "b"]
    _append_dedup(bucket, "b")
    assert bucket == ["a", "b"]


# ============================================================================
# _read_headers_from_wheel tests
# ============================================================================

def test_read_headers_from_wheel_missing_file(tmp_path, monkeypatch):
    """Test _read_headers_from_wheel when suffix doesn't match any file."""
    import zipfile
    from pychub.model.wheelinfo_model import _read_headers_from_wheel

    wheel_path = tmp_path / "test.whl"
    with zipfile.ZipFile(wheel_path, "w") as z:
        z.writestr("some_other_file.txt", "content")

    result = _read_headers_from_wheel(wheel_path, ".dist-info/METADATA")
    assert result == {}


def test_read_headers_from_wheel_success(tmp_path):
    """Test _read_headers_from_wheel successfully reads headers."""
    import zipfile
    from pychub.model.wheelinfo_model import _read_headers_from_wheel

    wheel_path = tmp_path / "test.whl"
    metadata_content = "Name: test-pkg\nVersion: 1.0\n"

    with zipfile.ZipFile(wheel_path, "w") as z:
        z.writestr("test-1.0.dist-info/METADATA", metadata_content)

    result = _read_headers_from_wheel(wheel_path, ".dist-info/METADATA")

    assert "Name" in result
    assert result["Name"] == ["test-pkg"]
    assert "Version" in result
    assert result["Version"] == ["1.0"]


def test_sha256_file_multiblock(tmp_path):
    """Test _sha256_file with file larger than one chunk."""
    from pychub.model.wheelinfo_model import _sha256_file

    test_file = tmp_path / "largefile.bin"
    # Create a file that requires multiple chunks (>1MB)
    chunk_size = 1024 * 1024
    data = b"x" * (chunk_size + 1000)
    test_file.write_bytes(data)

    result = _sha256_file(test_file, chunk=chunk_size)

    # Verify it's a valid sha256 hex string
    assert len(result) == 64
    assert all(c in "0123456789abcdef" for c in result)


def test_select_one_with_match(tmp_path):
    """Test _select_one returns value when match found."""
    from pychub.model.wheelinfo_model import _select_one

    headers = {"Name": ["test-pkg"], "Version": ["1.0"]}
    result = _select_one(headers, ("Name",))
    assert result == "test-pkg"


def test_select_one_with_or_alternatives(tmp_path):
    """Test _select_one with OR alternatives (|)."""
    from pychub.model.wheelinfo_model import _select_one

    headers = {"License-Expression": ["MIT"]}
    result = _select_one(headers, ("License|License-Expression",))
    assert result == "MIT"


def test_meta_str_with_value():
    """Test meta_str with non-None value."""
    from pychub.model.wheelinfo_model import meta_str
    assert meta_str("hello") == "hello"
    assert meta_str(42) == "42"


def test_meta_str_with_none():
    """Test meta_str with None value."""
    from pychub.model.wheelinfo_model import meta_str
    assert meta_str(None) is None


# ============================================================================
# ExtrasInfo edge cases
# ============================================================================

def test_extrasinfo_from_metadata_with_string_provides():
    """Test ExtrasInfo.from_metadata when provides_extra is a single string."""
    meta = {
        "provides_extra": "dev",  # Single string, not list
        "requires_dist": []
    }
    ei = ExtrasInfo.from_metadata(meta)
    assert "dev" in ei.extras


def test_extrasinfo_from_metadata_with_string_requires():
    """Test ExtrasInfo.from_metadata when requires_dist is a single string."""
    meta = {
        "provides_extra": [],
        "requires_dist": "pytest>=7.0; extra == 'test'"  # Single string
    }
    ei = ExtrasInfo.from_metadata(meta)
    assert "test" in ei.extras
    assert "pytest>=7.0" in ei.get("test")


# ============================================================================
# Round-trip tests
# ============================================================================

def test_wheelinfo_roundtrip_preserves_data():
    """Test that to_mapping -> from_mapping preserves all data."""
    ei = ExtrasInfo.from_mapping({"dev": ["pytest>=7.0"]})
    si = SourceInfo(type="index", url="https://example.com/pkg.whl")

    original = WheelInfo(
        filename="pkg-1.0-py3-none-any.whl",
        name="pkg",
        version="1.0",
        size=1024,
        sha256="abc123",
        tags=["py3-none-any"],
        requires_python=">=3.9",
        deps=["requests>=2.0"],
        extras=ei,
        source=si,
        meta={"summary": "Test"},
        wheel={"wheel_version": "1.0"}
    )

    mapping = original.to_mapping()
    restored = WheelInfo.from_mapping(original.filename, mapping)

    assert restored.name == original.name
    assert restored.version == original.version
    assert restored.size == original.size
    assert restored.sha256 == original.sha256
    assert restored.tags == original.tags
    assert restored.requires_python == original.requires_python
    assert restored.deps == original.deps
    assert restored.extras.to_mapping() == original.extras.to_mapping()
    assert restored.source.to_mapping() == original.source.to_mapping()
    assert restored.meta == original.meta
    assert restored.wheel == original.wheel