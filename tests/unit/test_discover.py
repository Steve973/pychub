from pychub.runtime.actions import discover


def test_discover_wheels_empty_dir(tmp_path):
    """Returns empty list when directory exists but has no wheels."""
    wheels = discover.discover_wheels(tmp_path)
    assert wheels == []


def test_discover_wheels_returns_all_sorted(tmp_path):
    """Unfiltered results are sorted lexicographically by filename."""
    (tmp_path / "zlib.whl").write_text("z")
    (tmp_path / "alib.whl").write_text("a")
    (tmp_path / "blib.whl").write_text("b")

    wheels = discover.discover_wheels(tmp_path)
    names = [w.name for w in wheels]
    assert names == ["alib.whl", "blib.whl", "zlib.whl"]


def test_discover_wheels_creates_dir_if_missing(tmp_path):
    """The function ensures the directory exists (creates if missing)."""
    libs_dir = tmp_path / "nonexistent"
    assert not libs_dir.exists()
    wheels = discover.discover_wheels(libs_dir)
    assert libs_dir.exists()
    assert wheels == []


def test_discover_wheels_ignores_non_whl_files(tmp_path):
    """Only files with the .whl suffix are returned."""
    (tmp_path / "keep.whl").write_text("k")
    (tmp_path / "skip.txt").write_text("s")
    (tmp_path / "also_skip.tar.gz").write_text("t")

    wheels = discover.discover_wheels(tmp_path)
    names = [w.name for w in wheels]
    assert names == ["keep.whl"]


def test_discover_wheels_ignores_subdirectories(tmp_path):
    """Matches are not recursive; wheels in subdirectories are ignored."""
    (tmp_path / "top.whl").write_text("t")
    sub = tmp_path / "subdir"
    sub.mkdir()
    (sub / "nested.whl").write_text("n")

    wheels = discover.discover_wheels(tmp_path)
    names = [w.name for w in wheels]
    assert names == ["top.whl"]
