from pychubby.runtime.actions import discover


def test_discover_wheels_empty_dir(tmp_path):
    """Returns empty list when directory exists but has no wheels."""
    wheels = discover.discover_wheels(tmp_path, only=None)
    assert wheels == []


def test_discover_wheels_returns_all_sorted(tmp_path):
    """Unfiltered results are sorted lexicographically by filename."""
    (tmp_path / "zlib.whl").write_text("z")
    (tmp_path / "alib.whl").write_text("a")
    (tmp_path / "blib.whl").write_text("b")

    wheels = discover.discover_wheels(tmp_path, only=None)
    names = [w.name for w in wheels]
    assert names == ["alib.whl", "blib.whl", "zlib.whl"]


def test_discover_wheels_filters_by_single_prefix(tmp_path):
    """Filtering by a single prefix includes only matching wheels."""
    (tmp_path / "foo-utils.whl").write_text("f")
    (tmp_path / "bar-tools.whl").write_text("b")
    (tmp_path / "baz-data.whl").write_text("b2")

    wheels = discover.discover_wheels(tmp_path, only="bar")
    names = [w.name for w in wheels]
    assert names == ["bar-tools.whl"]


def test_discover_wheels_filters_multiple_prefixes(tmp_path):
    """Multiple comma-separated prefixes are all honored (OR behavior)."""
    (tmp_path / "foo-alpha.whl").write_text("1")
    (tmp_path / "bar-beta.whl").write_text("2")
    (tmp_path / "baz-gamma.whl").write_text("3")
    (tmp_path / "nope.whl").write_text("4")

    wheels = discover.discover_wheels(tmp_path, only="foo, bar,  baz")
    names = sorted(w.name for w in wheels)
    assert names == ["bar-beta.whl", "baz-gamma.whl", "foo-alpha.whl"]


def test_discover_wheels_returns_empty_on_no_matches(tmp_path):
    """Returns empty list when no wheels match the given prefixes."""
    (tmp_path / "libx.whl").write_text("x")
    wheels = discover.discover_wheels(tmp_path, only="zzz")
    assert wheels == []


def test_discover_wheels_creates_dir_if_missing(tmp_path):
    """The function ensures the directory exists (creates if missing)."""
    libs_dir = tmp_path / "nonexistent"
    assert not libs_dir.exists()
    wheels = discover.discover_wheels(libs_dir, only=None)
    assert libs_dir.exists()
    assert wheels == []


def test_discover_wheels_ignores_non_whl_files(tmp_path):
    """Only files with the .whl suffix are returned."""
    (tmp_path / "keep.whl").write_text("k")
    (tmp_path / "skip.txt").write_text("s")
    (tmp_path / "also_skip.tar.gz").write_text("t")

    wheels = discover.discover_wheels(tmp_path, only=None)
    names = [w.name for w in wheels]
    assert names == ["keep.whl"]


def test_discover_wheels_ignores_subdirectories(tmp_path):
    """Matches are not recursive; wheels in subdirectories are ignored."""
    (tmp_path / "top.whl").write_text("t")
    sub = tmp_path / "subdir"
    sub.mkdir()
    (sub / "nested.whl").write_text("n")

    wheels = discover.discover_wheels(tmp_path, only=None)
    names = [w.name for w in wheels]
    assert names == ["top.whl"]


def test_discover_wheels_empty_string_only_no_filter(tmp_path):
    """Empty string for `only` is treated as falsy -> no filtering applied."""
    (tmp_path / "a.whl").write_text("a")
    (tmp_path / "b.whl").write_text("b")

    wheels = discover.discover_wheels(tmp_path, only="")
    names = [w.name for w in wheels]
    assert names == ["a.whl", "b.whl"]


def test_discover_wheels_trailing_commas_and_spaces(tmp_path):
    """Extra commas and spaces in `only` are ignored when extracting prefixes."""
    (tmp_path / "foo-one.whl").write_text("1")
    (tmp_path / "bar-two.whl").write_text("2")
    (tmp_path / "zzz-three.whl").write_text("3")

    wheels = discover.discover_wheels(tmp_path, only=" foo ,, bar , ")
    names = sorted(w.name for w in wheels)
    assert names == ["bar-two.whl", "foo-one.whl"]


def test_discover_wheels_is_case_sensitive(tmp_path):
    """Prefix matching is case-sensitive (str.startswith semantics)."""
    (tmp_path / "Foo-core.whl").write_text("1")
    (tmp_path / "foo-utils.whl").write_text("2")

    wheels = discover.discover_wheels(tmp_path, only="Foo")
    names = [w.name for w in wheels]
    assert names == ["Foo-core.whl"]
