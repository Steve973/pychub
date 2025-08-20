from pychubby.runtime.actions import discover


def test_discover_wheels_empty_dir(tmp_path):
    wheels = discover.discover_wheels(tmp_path, only=None)
    assert wheels == []


def test_discover_wheels_returns_all_sorted(tmp_path):
    (tmp_path / "zlib.whl").write_text("z")
    (tmp_path / "alib.whl").write_text("a")
    (tmp_path / "blib.whl").write_text("b")

    wheels = discover.discover_wheels(tmp_path, only=None)
    names = [w.name for w in wheels]
    assert names == ["alib.whl", "blib.whl", "zlib.whl"]


def test_discover_wheels_filters_by_single_prefix(tmp_path):
    (tmp_path / "foo-utils.whl").write_text("f")
    (tmp_path / "bar-tools.whl").write_text("b")
    (tmp_path / "baz-data.whl").write_text("b2")

    wheels = discover.discover_wheels(tmp_path, only="bar")
    names = [w.name for w in wheels]
    assert names == ["bar-tools.whl"]


def test_discover_wheels_filters_multiple_prefixes(tmp_path):
    (tmp_path / "foo-alpha.whl").write_text("1")
    (tmp_path / "bar-beta.whl").write_text("2")
    (tmp_path / "baz-gamma.whl").write_text("3")
    (tmp_path / "nope.whl").write_text("4")

    wheels = discover.discover_wheels(tmp_path, only="foo, bar,  baz")
    names = sorted(w.name for w in wheels)
    assert names == ["bar-beta.whl", "baz-gamma.whl", "foo-alpha.whl"]


def test_discover_wheels_returns_empty_on_no_matches(tmp_path):
    (tmp_path / "libx.whl").write_text("x")
    wheels = discover.discover_wheels(tmp_path, only="zzz")
    assert wheels == []


def test_discover_wheels_creates_dir_if_missing(tmp_path):
    libs_dir = tmp_path / "nonexistent"
    assert not libs_dir.exists()
    wheels = discover.discover_wheels(libs_dir, only=None)
    assert libs_dir.exists()
    assert wheels == []
