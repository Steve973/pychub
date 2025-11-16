import pytest

from pychub.model.includes_model import IncludeSpec


# ===========================
# IncludeSpec.parse() tests
# ===========================

def test_parse_simple_string():
    """Parse a simple string without destination."""
    spec = IncludeSpec.parse("path/to/file.txt")
    assert spec.src == "path/to/file.txt"
    assert spec.dest is None


def test_parse_string_with_destination():
    """Parse a string with :: separator and destination."""
    spec = IncludeSpec.parse("src/file.txt::dest/file.txt")
    assert spec.src == "src/file.txt"
    assert spec.dest == "dest/file.txt"


def test_parse_string_with_destination_strips_whitespace():
    """Parse should strip whitespace from both src and dest."""
    spec = IncludeSpec.parse("  src/file.txt  ::  dest/file.txt  ")
    assert spec.src == "src/file.txt"
    assert spec.dest == "dest/file.txt"


def test_parse_string_with_empty_destination():
    """Parse string with :: but empty dest should set dest to None."""
    spec = IncludeSpec.parse("src/file.txt::")
    assert spec.src == "src/file.txt"
    assert spec.dest is None


def test_parse_string_with_empty_destination_whitespace():
    """Parse string with :: and only whitespace dest should set dest to None."""
    spec = IncludeSpec.parse("src/file.txt::   ")
    assert spec.src == "src/file.txt"
    assert spec.dest is None


def test_parse_string_with_multiple_colons():
    """Parse string with multiple :: should split only on first occurrence."""
    spec = IncludeSpec.parse("src/file.txt::dest/path::subdir")
    assert spec.src == "src/file.txt"
    assert spec.dest == "dest/path::subdir"


def test_parse_dict_with_src_only():
    """Parse dict with only src field."""
    spec = IncludeSpec.parse({"src": "path/to/file.txt"})
    assert spec.src == "path/to/file.txt"
    assert spec.dest is None


def test_parse_dict_with_src_and_dest():
    """Parse dict with both src and dest fields."""
    spec = IncludeSpec.parse({"src": "src/file.txt", "dest": "dest/file.txt"})
    assert spec.src == "src/file.txt"
    assert spec.dest == "dest/file.txt"


def test_parse_dict_strips_whitespace_from_src():
    """Parse dict should strip whitespace from src."""
    spec = IncludeSpec.parse({"src": "  path/to/file.txt  "})
    assert spec.src == "path/to/file.txt"
    assert spec.dest is None


def test_parse_dict_with_dest_none():
    """Parse dict with dest=None should set dest to None."""
    spec = IncludeSpec.parse({"src": "src/file.txt", "dest": None})
    assert spec.src == "src/file.txt"
    assert spec.dest is None


def test_parse_dict_with_dest_empty_string():
    """Parse dict with dest="" should set dest to None."""
    spec = IncludeSpec.parse({"src": "src/file.txt", "dest": ""})
    assert spec.src == "src/file.txt"
    assert spec.dest is None


def test_parse_dict_with_dest_non_string_coerced():
    """Parse dict with non-string dest should coerce to string."""
    spec = IncludeSpec.parse({"src": "src/file.txt", "dest": 123})
    assert spec.src == "src/file.txt"
    assert spec.dest == "123"


def test_parse_dict_with_src_non_string_coerced():
    """Parse dict with non-string src should coerce to string."""
    spec = IncludeSpec.parse({"src": 456})
    assert spec.src == "456"
    assert spec.dest is None


def test_parse_dict_missing_src_raises():
    """Parse dict without src field should raise ValueError."""
    with pytest.raises(ValueError, match="missing 'src'"):
        IncludeSpec.parse({})


def test_parse_dict_with_empty_src_raises():
    """Parse dict with empty src should raise ValueError."""
    with pytest.raises(ValueError, match="missing 'src'"):
        IncludeSpec.parse({"src": ""})


def test_parse_dict_with_whitespace_only_src_raises():
    """Parse dict with whitespace-only src should raise ValueError."""
    with pytest.raises(ValueError, match="missing 'src'"):
        IncludeSpec.parse({"src": "   "})


def test_parse_dict_with_extra_fields():
    """Parse dict with extra fields should ignore them."""
    spec = IncludeSpec.parse({"src": "file.txt", "dest": "out.txt", "extra": "ignored"})
    assert spec.src == "file.txt"
    assert spec.dest == "out.txt"


# ===========================
# IncludeSpec.as_string() tests
# ===========================

def test_as_string_without_dest():
    """as_string() without dest should return just src."""
    spec = IncludeSpec(src="path/to/file.txt")
    assert spec.as_string() == "path/to/file.txt"


def test_as_string_with_dest():
    """as_string() with dest should return src::dest format."""
    spec = IncludeSpec(src="src/file.txt", dest="dest/file.txt")
    assert spec.as_string() == "src/file.txt::dest/file.txt"


def test_as_string_roundtrip_without_dest():
    """Parse and as_string should roundtrip correctly without dest."""
    original = "path/to/file.txt"
    spec = IncludeSpec.parse(original)
    assert spec.as_string() == original


def test_as_string_roundtrip_with_dest():
    """Parse and as_string should roundtrip correctly with dest."""
    original = "src/file.txt::dest/file.txt"
    spec = IncludeSpec.parse(original)
    assert spec.as_string() == original


# ===========================
# IncludeSpec.to_mapping() tests
# ===========================

def test_to_mapping_without_dest():
    """to_mapping() without dest should return dict with only src."""
    spec = IncludeSpec(src="path/to/file.txt")
    mapping = spec.to_mapping()
    assert mapping == {"src": "path/to/file.txt"}


def test_to_mapping_with_dest():
    """to_mapping() with dest should return dict with both src and dest."""
    spec = IncludeSpec(src="src/file.txt", dest="dest/file.txt")
    mapping = spec.to_mapping()
    assert mapping == {"src": "src/file.txt", "dest": "dest/file.txt"}


def test_to_mapping_roundtrip_without_dest():
    """Parse dict and to_mapping should roundtrip correctly without dest."""
    original = {"src": "path/to/file.txt"}
    spec = IncludeSpec.parse(original)
    assert spec.to_mapping() == original


def test_to_mapping_roundtrip_with_dest():
    """Parse dict and to_mapping should roundtrip correctly with dest."""
    original = {"src": "src/file.txt", "dest": "dest/file.txt"}
    spec = IncludeSpec.parse(original)
    assert spec.to_mapping() == original


# ===========================
# Edge case and integration tests
# ===========================

def test_parse_handles_dict_like_objects():
    """Parse should work with any Mapping, not just dict."""
    from collections import Ordereddict

    spec = IncludeSpec.parse(Ordereddict([("src", "file.txt"), ("dest", "out.txt")]))
    assert spec.src == "file.txt"
    assert spec.dest == "out.txt"


def test_direct_instantiation():
    """Test direct instantiation of IncludeSpec."""
    spec = IncludeSpec(src="file.txt", dest="out.txt")
    assert spec.src == "file.txt"
    assert spec.dest == "out.txt"


def test_direct_instantiation_without_dest():
    """Test direct instantiation without dest (should default to None)."""
    spec = IncludeSpec(src="file.txt")
    assert spec.src == "file.txt"
    assert spec.dest is None


def test_equality_with_dest():
    """Test equality of IncludeSpec instances with dest."""
    spec1 = IncludeSpec(src="file.txt", dest="out.txt")
    spec2 = IncludeSpec(src="file.txt", dest="out.txt")
    assert spec1 == spec2


def test_equality_without_dest():
    """Test equality of IncludeSpec instances without dest."""
    spec1 = IncludeSpec(src="file.txt")
    spec2 = IncludeSpec(src="file.txt")
    assert spec1 == spec2


def test_inequality_different_src():
    """Test inequality when src differs."""
    spec1 = IncludeSpec(src="file1.txt")
    spec2 = IncludeSpec(src="file2.txt")
    assert spec1 != spec2


def test_inequality_different_dest():
    """Test inequality when dest differs."""
    spec1 = IncludeSpec(src="file.txt", dest="out1.txt")
    spec2 = IncludeSpec(src="file.txt", dest="out2.txt")
    assert spec1 != spec2


def test_inequality_one_with_dest_one_without():
    """Test inequality when one has dest and the other doesn't."""
    spec1 = IncludeSpec(src="file.txt", dest="out.txt")
    spec2 = IncludeSpec(src="file.txt")
    assert spec1 != spec2


def test_parse_string_with_relative_paths():
    """Parse should handle relative paths correctly."""
    spec = IncludeSpec.parse("../parent/file.txt::./dest/file.txt")
    assert spec.src == "../parent/file.txt"
    assert spec.dest == "./dest/file.txt"


def test_parse_string_with_absolute_paths():
    """Parse should handle absolute paths correctly."""
    spec = IncludeSpec.parse("/absolute/path/file.txt::/absolute/dest/file.txt")
    assert spec.src == "/absolute/path/file.txt"
    assert spec.dest == "/absolute/dest/file.txt"


def test_parse_string_with_special_characters():
    """Parse should handle special characters in paths."""
    spec = IncludeSpec.parse("file-name_123.txt::dest/file-name_123.txt")
    assert spec.src == "file-name_123.txt"
    assert spec.dest == "dest/file-name_123.txt"


def test_parse_string_with_spaces_in_path():
    """Parse should handle paths with spaces."""
    spec = IncludeSpec.parse("path with spaces/file.txt::dest with spaces/file.txt")
    assert spec.src == "path with spaces/file.txt"
    assert spec.dest == "dest with spaces/file.txt"


def test_parse_empty_string():
    """Parse empty string should create spec with empty src."""
    spec = IncludeSpec.parse("")
    assert spec.src == ""
    assert spec.dest is None


def test_parse_string_only_separator():
    """Parse string with only :: should create spec with empty src and None dest."""
    spec = IncludeSpec.parse("::")
    assert spec.src == ""
    assert spec.dest is None


def test_parse_dict_with_dest_whitespace_only():
    """Parse dict with whitespace-only dest should NOT set dest to None (converts to string)."""
    spec = IncludeSpec.parse({"src": "file.txt", "dest": "   "})
    # Note: the code only checks for None or "" but not whitespace-only for dest
    assert spec.src == "file.txt"
    assert spec.dest == "   "  # This is preserved as-is for dict parsing


def test_multiple_parse_methods_same_result():
    """Parsing string vs dict with same values should yield equivalent specs."""
    spec_str = IncludeSpec.parse("src/file.txt::dest/file.txt")
    spec_dict = IncludeSpec.parse({"src": "src/file.txt", "dest": "dest/file.txt"})
    assert spec_str.src == spec_dict.src
    assert spec_str.dest == spec_dict.dest


def test_as_string_then_parse_preserves_data():
    """Converting to string and parsing back should preserve data."""
    original = IncludeSpec(src="path/to/file.txt", dest="output/file.txt")
    string_form = original.as_string()
    parsed = IncludeSpec.parse(string_form)
    assert parsed == original


def test_to_mapping_then_parse_preserves_data():
    """Converting to mapping and parsing back should preserve data."""
    original = IncludeSpec(src="path/to/file.txt", dest="output/file.txt")
    mapping = original.to_mapping()
    parsed = IncludeSpec.parse(mapping)
    assert parsed == original


def test_repr():
    """Test string representation of IncludeSpec."""
    spec = IncludeSpec(src="file.txt", dest="out.txt")
    repr_str = repr(spec)
    # Should contain class name and field values
    assert "IncludeSpec" in repr_str
    assert "file.txt" in repr_str
    assert "out.txt" in repr_str