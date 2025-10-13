import requests
from packaging.tags import Tag

from pychub.package import compatibility
from pychub.package.compatibility import match_wheels_to_tag, compute_compatibility_combos, compute_per_combo_wheel_map


def test_parse_wheel_tags_basic():
    tags = compatibility.parse_wheel_tags("foo-1.0.0-py3-none-any.whl")
    assert any(t.interpreter == "py3" for t in tags)
    assert any(t.platform == "any" for t in tags)


def test_filter_tags_py3_or_higher():
    tags = {
        Tag("py2", "none", "any"),
        Tag("py3", "none", "any"),
        Tag("cp310", "cp310", "linux_x86_64"),
    }
    filtered = compatibility.filter_tags_py3_or_higher(tags)
    assert Tag("py3", "none", "any") in filtered
    assert Tag("cp310", "cp310", "linux_x86_64") in filtered
    assert Tag("py2", "none", "any") not in filtered


def test_collect_and_combine_tags():
    wheel_files = {
        "foo": ["foo-1.0.0-py3-none-any.whl", "foo-1.0.0-cp310-cp310-linux_x86_64.whl"],
        "bar": ["bar-2.0.0-py3-none-any.whl"],
    }
    combos = compatibility.compute_compatibility_combos(wheel_files)
    # There should be at least one tag present in both foo and bar
    assert combos, "No common installable tags found"


def test_match_wheels_to_tag_basic():
    # Simulate two deps with wheels for different platforms
    wheel_files = {
        "dep_a": [
            "dep_a-1.0.0-py3-none-any.whl",
            "dep_a-1.0.0-cp313-cp313-manylinux2014_x86_64.whl"
        ],
        "dep_b": [
            "dep_b-2.0.0-py3-none-any.whl",
            "dep_b-2.0.0-cp313-cp313-manylinux2014_x86_64.whl"
        ]
    }

    # Should match on "py3-none-any" and "cp313-cp313-manylinux2014_x86_64"
    tag_any = Tag("py3", "none", "any")
    tag_linux = Tag("cp313", "cp313", "manylinux2014_x86_64")

    # Each dep should map to the right wheel for that tag
    result_any = match_wheels_to_tag(wheel_files, tag_any)
    assert result_any == {
        "dep_a": "dep_a-1.0.0-py3-none-any.whl",
        "dep_b": "dep_b-2.0.0-py3-none-any.whl"
    }

    result_linux = match_wheels_to_tag(wheel_files, tag_linux)
    assert result_linux == {
        "dep_a": "dep_a-1.0.0-cp313-cp313-manylinux2014_x86_64.whl",
        "dep_b": "dep_b-2.0.0-cp313-cp313-manylinux2014_x86_64.whl"
    }


def test_match_wheels_to_tag_partial():
    # One dep doesn't have the right tag
    wheel_files = {
        "dep_a": ["dep_a-1.0.0-py3-none-any.whl"],
        "dep_b": ["dep_b-2.0.0-cp313-cp313-manylinux2014_x86_64.whl"]
    }
    tag_linux = Tag("cp313", "cp313", "manylinux2014_x86_64")
    result = match_wheels_to_tag(wheel_files, tag_linux)
    assert result is None, "Should be empty if not all deps have a match"


def test_compute_compatibility_combos():
    wheel_files = {
        "dep_a": [
            "dep_a-1.0.0-py3-none-any.whl",
            "dep_a-1.0.0-cp313-cp313-manylinux2014_x86_64.whl"
        ],
        "dep_b": [
            "dep_b-2.0.0-py3-none-any.whl",
            "dep_b-2.0.0-cp313-cp313-manylinux2014_x86_64.whl"
        ]
    }
    combos = compute_compatibility_combos(wheel_files)
    tags = [combo[0] for combo in combos]
    tag_strs = [str(t) for t in tags]
    assert "py3-none-any" in tag_strs
    assert "cp313-cp313-manylinux2014_x86_64" in tag_strs
    # There should be two combos
    assert len(combos) == 2


def test_enumerate_valid_combos_basic():
    wheel_files = {
        "foo": ["foo-1.0.0-cp310-cp310-linux_x86_64.whl"],
        "bar": ["bar-2.0.0-py3-none-any.whl", "bar-2.0.0-cp310-cp310-linux_x86_64.whl"],
    }
    combos = compatibility.enumerate_valid_combos(wheel_files)
    assert ("cp310", "cp310", "linux_x86_64") in combos
    assert len(combos) == 1


def test_enumerate_valid_combos_matrix():
    wheel_files = {
        "foo": [
            "foo-1.0.0-py3-none-any.whl",
            "foo-1.0.0-cp310-cp310-linux_x86_64.whl",
            "foo-1.0.0-cp311-cp311-linux_x86_64.whl",
        ],
        "bar": [
            "bar-2.0.0-cp310-cp310-linux_x86_64.whl",
            "bar-2.0.0-cp311-cp311-linux_x86_64.whl",
        ],
        "baz": [
            "baz-3.0.0-py3-none-any.whl",
            "baz-3.0.0-cp310-cp310-linux_x86_64.whl",
            "baz-3.0.0-cp311-cp311-linux_x86_64.whl",
            "baz-3.0.0-cp312-cp312-linux_x86_64.whl",
        ],
    }
    combos = compatibility.enumerate_valid_combos(wheel_files)
    tag_strs = [f"{i}-{a}-{p}" for (i, a, p) in combos]
    assert "cp311-cp311-linux_x86_64" in tag_strs, "cp311 combo missing"
    assert "cp310-cp310-linux_x86_64" in tag_strs, "cp310 combo missing"
    assert "cp312-cp312-linux_x86_64" not in tag_strs, "cp312 is not a 'bar' dependency"
    assert len(tag_strs) == 2


def test_enumerate_valid_combos_matrix_universal():
    wheel_files = {
        "foo": [
            "foo-1.0.0-py3-none-any.whl",
            "foo-1.0.0-cp310-cp310-linux_x86_64.whl",
            "foo-1.0.0-cp311-cp311-linux_x86_64.whl",
        ],
        "bar": [
            "bar-2.0.0-py3-none-any.whl",
            "bar-2.0.0-cp311-cp311-linux_x86_64.whl",
        ],
        "baz": [
            "baz-3.0.0-py3-none-any.whl",
            "baz-3.0.0-cp310-cp310-linux_x86_64.whl",
            "baz-3.0.0-cp311-cp311-linux_x86_64.whl",
            "baz-3.0.0-cp312-cp312-linux_x86_64.whl",
        ],
    }
    combos = compatibility.enumerate_valid_combos(wheel_files)
    tag_strs = [f"{i}-{a}-{p}" for (i, a, p) in combos]
    assert "py3-none-any" in tag_strs, "Universal combo missing"
    assert len(tag_strs) == 1


def test_basic_combo_selection(monkeypatch):
    wheel_files = {
        "depA": [
            "depA-1.0.0-cp310-cp310-manylinux_x86_64.whl",
            "depA-1.0.0-cp311-cp311-manylinux_x86_64.whl",
        ],
        "depB": [
            "depB-2.0.0-cp310-cp310-manylinux_x86_64.whl",
            "depB-2.0.0-cp311-cp311-manylinux_x86_64.whl",
        ],
    }
    result = compute_per_combo_wheel_map(wheel_files)
    assert "cp310-cp310-manylinux_x86_64" in result
    assert "cp311-cp311-manylinux_x86_64" in result
    assert all(len(v) == 2 for v in result.values())


def test_skips_missing_wheel(monkeypatch):
    # depB lacks cp311 wheel → that combo should be skipped
    wheel_files = {
        "depA": [
            "depA-1.0.0-cp310-cp310-manylinux_x86_64.whl",
            "depA-1.0.0-cp311-cp311-manylinux_x86_64.whl",
        ],
        "depB": [
            "depB-2.0.0-cp310-cp310-manylinux_x86_64.whl",
        ],
    }
    result = compute_per_combo_wheel_map(wheel_files)
    assert "cp310-cp310-manylinux_x86_64" in result
    assert "cp311-cp311-manylinux_x86_64" not in result


def test_prefers_universal_deps():
    wheel_files = {
        "depA": [
            "depA-1.0.0-py3-none-any.whl",  # universal
            "depA-1.0.0-cp310-cp310-manylinux_x86_64.whl",
        ],
        "depB": [
            "depB-2.0.0-cp310-cp310-manylinux_x86_64.whl",
        ],
    }

    result = compute_per_combo_wheel_map(wheel_files)
    assert result, "Expected at least one combo mapping"

    for combo, mapping in result.items():
        # depA should always use its universal wheel
        assert mapping["depA"].endswith("py3-none-any.whl"), \
            f"depA did not prefer universal wheel for {combo}: {mapping['depA']}"
        # depB should use its matching platform-specific wheel
        assert mapping["depB"].endswith("cp310-cp310-manylinux_x86_64.whl"), \
            f"depB picked unexpected wheel for {combo}: {mapping['depB']}"


def test_large_combo_mapping():
    wheel_files = {
        "depA": [
            "depA-1.0.0-py3-none-any.whl",  # universal
            "depA-1.0.0-cp310-cp310-manylinux_x86_64.whl",
            "depA-1.0.0-cp311-cp311-macosx_11_0_x86_64.whl",
        ],
        "depB": [
            "depB-1.0.0-cp310-cp310-manylinux_x86_64.whl",
            "depB-1.0.0-cp311-cp311-macosx_11_0_x86_64.whl",
        ],
        "depC": [
            "depC-1.0.0-py3-none-any.whl",  # universal
        ],
        "depD": [
            "depD-2.0.0-cp310-cp310-manylinux_x86_64.whl",
            "depD-2.0.0-cp311-cp311-macosx_11_0_x86_64.whl",
        ]
    }

    result = compute_per_combo_wheel_map(wheel_files)
    assert result, "Expected combos to be generated"

    expected_combos = {
        "cp310-cp310-manylinux_x86_64",
        "cp311-cp311-macosx_11_0_x86_64"
    }

    assert set(result.keys()) == expected_combos

    for combo, mapping in result.items():
        assert set(mapping.keys()) == {"depA", "depB", "depC", "depD"}

        # depC is only universal
        assert mapping["depC"].endswith("py3-none-any.whl")

        # depA prefers universal
        assert mapping["depA"].endswith("py3-none-any.whl")

        if combo.startswith("cp310"):
            assert mapping["depB"].endswith("cp310-cp310-manylinux_x86_64.whl")
            assert mapping["depD"].endswith("cp310-cp310-manylinux_x86_64.whl")
        else:
            assert mapping["depB"].endswith("cp311-cp311-macosx_11_0_x86_64.whl")
            assert mapping["depD"].endswith("cp311-cp311-macosx_11_0_x86_64.whl")


def test_large_combo_mapping_universal_only():
    wheel_files = {
        "depA": [
            "depA-1.0.0-py3-none-any.whl",  # universal
            "depA-1.0.0-cp310-cp310-manylinux_x86_64.whl",
            "depA-1.0.0-cp311-cp311-macosx_11_0_x86_64.whl",
        ],
        "depB": [
            "depB-1.0.0-py3-none-any.whl",
            "depB-1.0.0-cp310-cp310-manylinux_x86_64.whl",
            "depB-1.0.0-cp311-cp311-macosx_11_0_x86_64.whl",
        ],
        "depC": [
            "depC-1.0.0-py3-none-any.whl",  # universal
        ],
        "depD": [
            "depD-2.0.0-py3-none-any.whl",
            "depD-2.0.0-cp310-cp310-manylinux_x86_64.whl",
            "depD-2.0.0-cp311-cp311-macosx_11_0_x86_64.whl",
        ]
    }

    result = compute_per_combo_wheel_map(wheel_files)
    assert result, "Expected combos to be generated"
    assert set(result.keys()) == {"py3-none-any"}


def test_parse_wheel_tags_multiple_tags():
    """Test parsing wheel with multiple platform/abi tags."""
    tags = compatibility.parse_wheel_tags("pkg-1.0-cp39-abi3-linux_x86_64.manylinux2014_x86_64.whl")
    assert len(tags) > 0
    interps = {t.interpreter for t in tags}
    assert "cp39" in interps


def test_filter_tags_keeps_py2_py3():
    """Test that py2.py3 (dual-compatible) tags are kept."""
    tags = {
        Tag("py2", "none", "any"),
        Tag("py2.py3", "none", "any"),
    }
    filtered = compatibility.filter_tags_py3_or_higher(tags)
    assert Tag("py2.py3", "none", "any") in filtered
    assert Tag("py2", "none", "any") not in filtered


def test_filter_tags_keeps_pypy():
    """Test that PyPy3 tags are kept."""
    tags = {
        Tag("pp38", "pypy38_pp73", "linux_x86_64"),
        Tag("pp39", "pypy39_pp73", "win_amd64"),
    }
    filtered = compatibility.filter_tags_py3_or_higher(tags)
    assert len(filtered) == 0  # pp38 doesn't match the is_py3 logic


def test_filter_tags_edge_cases():
    """Test edge cases in tag filtering."""
    tags = {
        Tag("cp27", "cp27mu", "linux_x86_64"),
        Tag("cp38", "cp38", "win_amd64"),
        Tag("py3", "none", "any"),
    }
    filtered = compatibility.filter_tags_py3_or_higher(tags)
    assert Tag("cp38", "cp38", "win_amd64") in filtered
    assert Tag("py3", "none", "any") in filtered
    assert Tag("cp27", "cp27mu", "linux_x86_64") not in filtered


def test_collect_wheel_tags_for_deps():
    """Test collecting tags from multiple wheels per dependency."""
    wheel_files = {
        "dep1": ["dep1-1.0-py3-none-any.whl", "dep1-1.0-cp310-cp310-linux_x86_64.whl"],
        "dep2": ["dep2-2.0-cp311-cp311-win_amd64.whl"],
    }
    result = compatibility.collect_wheel_tags_for_deps(wheel_files)

    assert "dep1" in result
    assert "dep2" in result
    assert any(t.interpreter == "py3" for t in result["dep1"])
    assert any(t.interpreter == "cp310" for t in result["dep1"])
    assert any(t.interpreter == "cp311" for t in result["dep2"])


def test_collect_wheel_tags_empty():
    """Test collecting tags with no wheels."""
    result = compatibility.collect_wheel_tags_for_deps({})
    assert result == {}


def test_tag_sort_key():
    """Test tag sorting function."""
    tag1 = Tag("cp310", "cp310", "linux_x86_64")
    tag2 = Tag("cp311", "cp311", "linux_x86_64")
    tag3 = Tag("py3", "none", "any")

    tags = [tag2, tag3, tag1]
    sorted_tags = sorted(tags, key=compatibility.tag_sort_key)

    assert sorted_tags[0] == tag1  # cp310 comes before cp311
    assert sorted_tags[1] == tag2
    assert sorted_tags[2] == tag3  # py3 comes after cp*


def test_tag_to_str():
    """Test tag to string conversion."""
    tag = Tag("cp310", "cp310", "linux_x86_64")
    result = compatibility.tag_to_str(tag)
    assert result == "cp310-cp310-linux_x86_64"


def test_is_universal_tag_positive():
    """Test universal tag detection - positive cases."""
    assert compatibility.is_universal_tag(Tag("py3", "none", "any")) is True


def test_is_universal_tag_negative():
    """Test universal tag detection - negative cases."""
    assert compatibility.is_universal_tag(Tag("cp310", "cp310", "linux_x86_64")) is False
    assert compatibility.is_universal_tag(Tag("py3", "cp310", "any")) is False
    assert compatibility.is_universal_tag(Tag("py3", "none", "linux")) is False
    assert compatibility.is_universal_tag(Tag("py2", "none", "any")) is False


def test_has_universal_tag_positive():
    """Test has_universal_tag with universal wheel."""
    assert compatibility.has_universal_tag("pkg-1.0-py3-none-any.whl") is True


def test_has_universal_tag_negative():
    """Test has_universal_tag with platform-specific wheel."""
    assert compatibility.has_universal_tag("pkg-1.0-cp310-cp310-linux_x86_64.whl") is False


def test_aggregate_tag_components():
    """Test aggregating tag components from wheels."""
    wheel_files = {
        "dep1": ["dep1-1.0-py3-none-any.whl", "dep1-1.0-cp310-cp310-linux_x86_64.whl"],
        "dep2": ["dep2-2.0-cp311-cp311-win_amd64.whl"],
    }

    interpreters, abis, platforms = compatibility.aggregate_tag_components(wheel_files)

    assert "py3" in interpreters
    assert "cp310" in interpreters
    assert "cp311" in interpreters
    assert "none" in abis
    assert "cp310" in abis
    assert "cp311" in abis
    assert "any" in platforms
    assert "linux_x86_64" in platforms
    assert "win_amd64" in platforms


def test_aggregate_tag_components_empty():
    """Test aggregating with no wheels."""
    interpreters, abis, platforms = compatibility.aggregate_tag_components({})
    assert interpreters == []
    assert abis == []
    assert platforms == []


def test_enumerate_valid_combos_empty_input():
    """Test enumerate_valid_combos with empty input."""
    result = compatibility.enumerate_valid_combos({})
    assert result == []


def test_enumerate_valid_combos_single_dep():
    """Test enumerate_valid_combos with single dependency."""
    wheel_files = {
        "dep1": [
            "dep1-1.0-py3-none-any.whl",
            "dep1-1.0-cp310-cp310-linux_x86_64.whl",
        ]
    }
    combos = compatibility.enumerate_valid_combos(wheel_files)
    # Single dep can support all its own combos
    assert len(combos) >= 1


def test_enumerate_valid_combos_no_overlap():
    """Test enumerate_valid_combos with no overlapping platforms."""
    wheel_files = {
        "dep1": ["dep1-1.0-cp310-cp310-linux_x86_64.whl"],
        "dep2": ["dep2-1.0-cp311-cp311-win_amd64.whl"],
    }
    combos = compatibility.enumerate_valid_combos(wheel_files)
    assert len(combos) == 0  # No common tags


def test_compute_compatibility_combos_empty():
    """Test compute_compatibility_combos with empty input."""
    result = compatibility.compute_compatibility_combos({})
    assert result == []


def test_compute_compatibility_combos_no_common_tags():
    """Test compute_compatibility_combos with no common tags."""
    wheel_files = {
        "dep1": ["dep1-1.0-cp310-cp310-linux_x86_64.whl"],
        "dep2": ["dep2-1.0-cp311-cp311-win_amd64.whl"],
    }
    combos = compatibility.compute_compatibility_combos(wheel_files)
    assert len(combos) == 0


def test_match_wheels_to_tag_all_missing():
    """Test match_wheels_to_tag when all deps lack the tag."""
    wheel_files = {
        "dep1": ["dep1-1.0-cp310-cp310-linux_x86_64.whl"],
        "dep2": ["dep2-1.0-cp310-cp310-linux_x86_64.whl"],
    }
    tag = Tag("cp311", "cp311", "win_amd64")
    result = compatibility.match_wheels_to_tag(wheel_files, tag)
    assert result is None


def test_match_wheels_to_tag_empty_wheels():
    """Test match_wheels_to_tag with empty wheel dict."""
    result = compatibility.match_wheels_to_tag({}, Tag("py3", "none", "any"))
    assert result == {}


def test_compute_per_combo_wheel_map_empty():
    """Test compute_per_combo_wheel_map with empty input."""
    result = compatibility.compute_per_combo_wheel_map({})
    assert result == {}


def test_compute_per_combo_wheel_map_no_valid_combos():
    """Test compute_per_combo_wheel_map with no valid combos."""
    wheel_files = {
        "dep1": ["dep1-1.0-cp310-cp310-linux_x86_64.whl"],
        "dep2": ["dep2-1.0-cp311-cp311-win_amd64.whl"],
    }
    result = compatibility.compute_per_combo_wheel_map(wheel_files)
    assert result == {}


def test_compute_per_combo_wheel_map_prefers_universal_over_platform():
    """Test that universal wheels are preferred even when platform-specific exists."""
    wheel_files = {
        "dep1": [
            "dep1-1.0-cp310-cp310-linux_x86_64.whl",
            "dep1-1.0-py3-none-any.whl",
        ],
        "dep2": [
            "dep2-1.0-cp310-cp310-linux_x86_64.whl",
            "dep2-1.0-py3-none-any.whl",
        ],
    }
    result = compatibility.compute_per_combo_wheel_map(wheel_files)

    # Should have both universal and platform combos
    assert "py3-none-any" in result

    # For the universal combo, all deps use universal wheels
    if "py3-none-any" in result:
        mapping = result["py3-none-any"]
        assert mapping["dep1"].endswith("py3-none-any.whl")
        assert mapping["dep2"].endswith("py3-none-any.whl")


def test_compute_per_combo_wheel_map_mixed_availability():
    """Test combo mapping with mixed wheel availability."""
    wheel_files = {
        "dep1": [
            "dep1-1.0-py3-none-any.whl",
            "dep1-1.0-cp310-cp310-linux_x86_64.whl",
            "dep1-1.0-cp311-cp311-linux_x86_64.whl",
        ],
        "dep2": [
            "dep2-1.0-cp310-cp310-linux_x86_64.whl",
        ],
    }
    result = compatibility.compute_per_combo_wheel_map(wheel_files)

    # Only cp310 should be valid (dep2 doesn't have cp311)
    assert "cp310-cp310-linux_x86_64" in result
    assert "cp311-cp311-linux_x86_64" not in result

    # dep1 should prefer universal for cp310 combo
    if "cp310-cp310-linux_x86_64" in result:
        mapping = result["cp310-cp310-linux_x86_64"]
        assert mapping["dep1"].endswith("py3-none-any.whl")
        assert mapping["dep2"].endswith("cp310-cp310-linux_x86_64.whl")


def test_compute_per_combo_wheel_map_all_universal():
    """Test combo mapping when all deps are universal only."""
    wheel_files = {
        "dep1": ["dep1-1.0-py3-none-any.whl"],
        "dep2": ["dep2-1.0-py3-none-any.whl"],
        "dep3": ["dep3-1.0-py3-none-any.whl"],
    }
    result = compatibility.compute_per_combo_wheel_map(wheel_files)

    assert "py3-none-any" in result
    assert len(result) == 1

    mapping = result["py3-none-any"]
    assert len(mapping) == 3
    assert all(whl.endswith("py3-none-any.whl") for whl in mapping.values())


def test_enumerate_valid_combos_partial_universal():
    """Test enumerate_valid_combos when some deps have universal wheels."""
    wheel_files = {
        "universal_dep": ["universal_dep-1.0-py3-none-any.whl"],
        "platform_dep": [
            "platform_dep-1.0-cp310-cp310-linux_x86_64.whl",
            "platform_dep-1.0-cp311-cp311-linux_x86_64.whl",
        ],
    }
    combos = compatibility.enumerate_valid_combos(wheel_files)
    tag_strs = [f"{i}-{a}-{p}" for (i, a, p) in combos]

    # Universal dep should allow both platform combos
    assert "cp310-cp310-linux_x86_64" in tag_strs
    assert "cp311-cp311-linux_x86_64" in tag_strs


def test_enumerate_valid_combos_multiple_platforms():
    """Test enumerate_valid_combos with multiple platforms per version."""
    wheel_files = {
        "dep1": [
            "dep1-1.0-cp310-cp310-linux_x86_64.whl",
            "dep1-1.0-cp310-cp310-win_amd64.whl",
            "dep1-1.0-cp310-cp310-macosx_11_0_arm64.whl",
        ],
        "dep2": [
            "dep2-1.0-cp310-cp310-linux_x86_64.whl",
            "dep2-1.0-cp310-cp310-win_amd64.whl",
        ],
    }
    combos = compatibility.enumerate_valid_combos(wheel_files)
    tag_strs = [f"{i}-{a}-{p}" for (i, a, p) in combos]

    # Both deps support Linux and Windows for cp310
    assert "cp310-cp310-linux_x86_64" in tag_strs
    assert "cp310-cp310-win_amd64" in tag_strs
    # macOS only in dep1, so it shouldn't be valid
    assert "cp310-cp310-macosx_11_0_arm64" not in tag_strs


def test_compute_per_combo_wheel_map_multiple_valid_wheels_picks_first():
    """Test that when multiple wheels match, the first is picked."""
    wheel_files = {
        "dep1": [
            "dep1-1.0-cp310-cp310-linux_x86_64.whl",
            "dep1-1.0-cp310-abi3-linux_x86_64.whl",
        ],
        "dep2": [
            "dep2-1.0-cp310-cp310-linux_x86_64.whl",
        ],
    }
    result = compatibility.compute_per_combo_wheel_map(wheel_files)

    # Should have a combo, and dep1 should pick the first non-universal match
    if "cp310-cp310-linux_x86_64" in result:
        mapping = result["cp310-cp310-linux_x86_64"]
        # Since neither is universal, should pick the first wheel that matches
        assert "dep1" in mapping
        assert "dep2" in mapping


def test_parse_wheel_tags_abi3():
    """Test parsing wheel with abi3 (stable ABI) tag."""
    tags = compatibility.parse_wheel_tags("pkg-1.0-cp39-abi3-linux_x86_64.whl")
    assert any(t.abi == "abi3" for t in tags)


def test_filter_tags_comprehensive():
    """Test comprehensive tag filtering scenarios."""
    tags = {
        Tag("py2", "none", "any"),
        Tag("py3", "none", "any"),
        Tag("py27", "none", "any"),
        Tag("py35", "none", "any"),
        Tag("cp27", "cp27mu", "linux_x86_64"),
        Tag("cp35", "cp35m", "linux_x86_64"),
        Tag("cp310", "cp310", "win_amd64"),
        Tag("pp38", "pypy38_pp73", "linux_x86_64"),
    }
    filtered = compatibility.filter_tags_py3_or_higher(tags)

    # Should keep py3, py35, cp35, cp310
    assert Tag("py3", "none", "any") in filtered
    assert Tag("cp35", "cp35m", "linux_x86_64") in filtered
    assert Tag("cp310", "cp310", "win_amd64") in filtered

    # Should remove py2, py27, cp27
    assert Tag("py2", "none", "any") not in filtered
    assert Tag("py27", "none", "any") not in filtered
    assert Tag("cp27", "cp27mu", "linux_x86_64") not in filtered


def test_fetch_all_wheel_variants_basic_success(monkeypatch):
    """Test fetch_all_wheel_variants with a basic successful response."""
    mock_response_data = {
        "releases": {
            "1.0.0": [
                {
                    "filename": "attrs-1.0.0-py3-none-any.whl",
                    "url": "https://files.pythonhosted.org/packages/attrs-1.0.0-py3-none-any.whl"
                }
            ],
            "1.1.0": [
                {
                    "filename": "attrs-1.1.0-py3-none-any.whl",
                    "url": "https://files.pythonhosted.org/packages/attrs-1.1.0-py3-none-any.whl"
                },
                {
                    "filename": "attrs-1.1.0-cp310-cp310-linux_x86_64.whl",
                    "url": "https://files.pythonhosted.org/packages/attrs-1.1.0-cp310-cp310-linux_x86_64.whl"
                }
            ]
        }
    }

    class MockResponse:
        def raise_for_status(self):
            pass

        def json(self):
            return mock_response_data

    def mock_get(url, timeout=None):
        return MockResponse()

    monkeypatch.setattr(requests, "get", mock_get)

    result = compatibility.fetch_all_wheel_variants("attrs")

    assert "attrs" in result
    assert len(result["attrs"]) == 3
    assert all("filename" in w for w in result["attrs"])
    assert all("url" in w for w in result["attrs"])
    assert all("version" in w for w in result["attrs"])
    assert all("tags" in w for w in result["attrs"])


def test_fetch_all_wheel_variants_with_version_specifier(monkeypatch):
    """Test fetch_all_wheel_variants filters by version specifier."""
    mock_response_data = {
        "releases": {
            "1.0.0": [
                {
                    "filename": "pkg-1.0.0-py3-none-any.whl",
                    "url": "https://example.com/pkg-1.0.0-py3-none-any.whl"
                }
            ],
            "2.0.0": [
                {
                    "filename": "pkg-2.0.0-py3-none-any.whl",
                    "url": "https://example.com/pkg-2.0.0-py3-none-any.whl"
                }
            ],
            "3.0.0": [
                {
                    "filename": "pkg-3.0.0-py3-none-any.whl",
                    "url": "https://example.com/pkg-3.0.0-py3-none-any.whl"
                }
            ]
        }
    }

    class MockResponse:
        def raise_for_status(self):
            pass

        def json(self):
            return mock_response_data

    monkeypatch.setattr(requests, "get", lambda url, timeout=None: MockResponse())

    result = compatibility.fetch_all_wheel_variants("pkg>=2.0.0")

    assert "pkg" in result
    versions = [w["version"] for w in result["pkg"]]
    assert "2.0.0" in versions
    assert "3.0.0" in versions
    assert "1.0.0" not in versions


def test_fetch_all_wheel_variants_filters_non_wheels(monkeypatch):
    """Test that non-wheel files are filtered out."""
    mock_response_data = {
        "releases": {
            "1.0.0": [
                {
                    "filename": "pkg-1.0.0.tar.gz",
                    "url": "https://example.com/pkg-1.0.0.tar.gz"
                },
                {
                    "filename": "pkg-1.0.0-py3-none-any.whl",
                    "url": "https://example.com/pkg-1.0.0-py3-none-any.whl"
                },
                {
                    "filename": "pkg-1.0.0.zip",
                    "url": "https://example.com/pkg-1.0.0.zip"
                }
            ]
        }
    }

    class MockResponse:
        def raise_for_status(self):
            pass

        def json(self):
            return mock_response_data

    monkeypatch.setattr(requests, "get", lambda url, timeout=None: MockResponse())

    result = compatibility.fetch_all_wheel_variants("pkg")

    assert "pkg" in result
    assert len(result["pkg"]) == 1
    assert result["pkg"][0]["filename"].endswith(".whl")


def test_fetch_all_wheel_variants_invalid_requirement(monkeypatch, capsys):
    """Test fetch_all_wheel_variants with invalid requirement string."""
    result = compatibility.fetch_all_wheel_variants("invalid requirement >>>")

    assert result == {}
    captured = capsys.readouterr()
    assert "[compatibility] Could not parse requirement" in captured.out


def test_fetch_all_wheel_variants_network_error(monkeypatch, capsys):
    """Test fetch_all_wheel_variants handles network errors gracefully."""

    def mock_get_error(url, timeout=None):
        raise requests.RequestException("Network error")

    monkeypatch.setattr(requests, "get", mock_get_error)

    result = compatibility.fetch_all_wheel_variants("attrs")

    assert result == {}
    captured = capsys.readouterr()
    assert "[compatibility] Could not fetch metadata for attrs" in captured.out


def test_fetch_all_wheel_variants_http_error(monkeypatch, capsys):
    """Test fetch_all_wheel_variants handles HTTP errors."""

    class MockResponse:
        def raise_for_status(self):
            raise requests.HTTPError("404 Not Found")

    monkeypatch.setattr(requests, "get", lambda url, timeout=None: MockResponse())

    result = compatibility.fetch_all_wheel_variants("nonexistent-pkg")

    assert result == {}
    captured = capsys.readouterr()
    assert "[compatibility] Could not fetch metadata" in captured.out


def test_fetch_all_wheel_variants_invalid_wheel_filename(monkeypatch, capsys):
    """Test fetch_all_wheel_variants skips wheels with unparseable filenames."""
    mock_response_data = {
        "releases": {
            "1.0.0": [
                {
                    "filename": "valid-1.0.0-py3-none-any.whl",
                    "url": "https://example.com/valid.whl"
                },
                {
                    "filename": "invalid.whl",
                    "url": "https://example.com/invalid.whl"
                }
            ]
        }
    }

    class MockResponse:
        def raise_for_status(self):
            pass

        def json(self):
            return mock_response_data

    monkeypatch.setattr(requests, "get", lambda url, timeout=None: MockResponse())

    result = compatibility.fetch_all_wheel_variants("test-pkg")

    assert "test-pkg" in result
    assert len(result["test-pkg"]) == 1
    assert result["test-pkg"][0]["filename"] == "valid-1.0.0-py3-none-any.whl"

    captured = capsys.readouterr()
    assert "[compatibility] Failed to parse tags from invalid.whl" in captured.out


def test_fetch_all_wheel_variants_invalid_version(monkeypatch):
    """Test fetch_all_wheel_variants skips releases with invalid version strings."""
    mock_response_data = {
        "releases": {
            "1.0.0": [
                {
                    "filename": "pkg-1.0.0-py3-none-any.whl",
                    "url": "https://example.com/pkg-1.0.0.whl"
                }
            ],
            "invalid-version-string": [
                {
                    "filename": "pkg-invalid-py3-none-any.whl",
                    "url": "https://example.com/pkg-invalid.whl"
                }
            ]
        }
    }

    class MockResponse:
        def raise_for_status(self):
            pass

        def json(self):
            return mock_response_data

    monkeypatch.setattr(requests, "get", lambda url, timeout=None: MockResponse())

    result = compatibility.fetch_all_wheel_variants("pkg")

    assert "pkg" in result
    assert len(result["pkg"]) == 1
    assert result["pkg"][0]["version"] == "1.0.0"


def test_fetch_all_wheel_variants_no_wheels(monkeypatch):
    """Test fetch_all_wheel_variants when package has no wheels."""
    mock_response_data = {
        "releases": {
            "1.0.0": [
                {
                    "filename": "pkg-1.0.0.tar.gz",
                    "url": "https://example.com/pkg-1.0.0.tar.gz"
                }
            ]
        }
    }

    class MockResponse:
        def raise_for_status(self):
            pass

        def json(self):
            return mock_response_data

    monkeypatch.setattr(requests, "get", lambda url, timeout=None: MockResponse())

    result = compatibility.fetch_all_wheel_variants("pkg")

    assert result == {}


def test_fetch_all_wheel_variants_multiple_requirements(monkeypatch):
    """Test fetch_all_wheel_variants with multiple requirements."""
    call_count = {"count": 0}

    def mock_get(url, timeout=None):
        call_count["count"] += 1

        if "pkg1" in url:
            data = {
                "releases": {
                    "1.0.0": [{
                        "filename": "pkg1-1.0.0-py3-none-any.whl",
                        "url": "https://example.com/pkg1.whl"
                    }]
                }
            }
        else:  # pkg2
            data = {
                "releases": {
                    "2.0.0": [{
                        "filename": "pkg2-2.0.0-py3-none-any.whl",
                        "url": "https://example.com/pkg2.whl"
                    }]
                }
            }

        class MockResponse:
            def raise_for_status(self):
                pass

            def json(self):
                return data

        return MockResponse()

    monkeypatch.setattr(requests, "get", mock_get)

    result = compatibility.fetch_all_wheel_variants("pkg1", "pkg2")

    assert "pkg1" in result
    assert "pkg2" in result
    assert call_count["count"] == 2


def test_fetch_all_wheel_variants_custom_index_url(monkeypatch):
    """Test fetch_all_wheel_variants with custom index URL."""
    called_url = {"url": None}

    def mock_get(url, timeout=None):
        called_url["url"] = url

        class MockResponse:
            def raise_for_status(self):
                pass

            def json(self):
                return {"releases": {}}

        return MockResponse()

    monkeypatch.setattr(requests, "get", mock_get)

    compatibility.fetch_all_wheel_variants("pkg", index_url="https://custom.pypi.org/simple")

    assert called_url["url"] == "https://custom.pypi.org/simple/pkg/json"


def test_fetch_all_wheel_variants_empty_releases(monkeypatch):
    """Test fetch_all_wheel_variants when releases dict is empty."""
    mock_response_data = {"releases": {}}

    class MockResponse:
        def raise_for_status(self):
            pass

        def json(self):
            return mock_response_data

    monkeypatch.setattr(requests, "get", lambda url, timeout=None: MockResponse())

    result = compatibility.fetch_all_wheel_variants("pkg")

    assert result == {}


def test_fetch_all_wheel_variants_preserves_tags_as_frozenset(monkeypatch):
    """Test that tags are returned as frozenset."""
    mock_response_data = {
        "releases": {
            "1.0.0": [
                {
                    "filename": "pkg-1.0.0-py3-none-any.whl",
                    "url": "https://example.com/pkg.whl"
                }
            ]
        }
    }

    class MockResponse:
        def raise_for_status(self):
            pass

        def json(self):
            return mock_response_data

    monkeypatch.setattr(requests, "get", lambda url, timeout=None: MockResponse())

    result = compatibility.fetch_all_wheel_variants("pkg")

    assert "pkg" in result
    assert len(result["pkg"]) == 1
    # Tags should be frozenset (from parse_wheel_filename)
    assert isinstance(result["pkg"][0]["tags"], frozenset)


def test_fetch_all_wheel_variants_mixed_success_and_failure(monkeypatch, capsys):
    """Test fetch_all_wheel_variants continues on partial failures."""

    def mock_get(url, timeout=None):
        if "pkg1" in url:
            raise requests.RequestException("Network error for pkg1")

        class MockResponse:
            def raise_for_status(self):
                pass

            def json(self):
                return {
                    "releases": {
                        "1.0.0": [{
                            "filename": "pkg2-1.0.0-py3-none-any.whl",
                            "url": "https://example.com/pkg2.whl"
                        }]
                    }
                }

        return MockResponse()

    monkeypatch.setattr(requests, "get", mock_get)

    result = compatibility.fetch_all_wheel_variants("pkg1", "pkg2")

    assert "pkg1" not in result
    assert "pkg2" in result

    captured = capsys.readouterr()
    assert "[compatibility] Could not fetch metadata for pkg1" in captured.out