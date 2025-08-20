from pychubby.runtime.actions import unpack


def test_unpack_wheels_no_wheels(tmp_path, capsys):
    libs_dir = tmp_path / "libs"
    libs_dir.mkdir()
    dest = tmp_path / "dest"

    unpack.unpack_wheels(libs_dir, dest)

    assert dest.exists() and dest.is_dir()
    assert not any(dest.iterdir())

    out = capsys.readouterr().out
    assert "unpacked 0 wheels" in out


def test_unpack_wheels_copies_all_and_logs(tmp_path, capsys):
    libs_dir = tmp_path / "libs"
    dest_dir = tmp_path / "dest"
    libs_dir.mkdir()

    # Create fake wheel files
    (libs_dir / "a.whl").write_text("a")
    (libs_dir / "b.whl").write_text("b")
    (libs_dir / "not_a_wheel.txt").write_text("nope")

    unpack.unpack_wheels(libs_dir, dest_dir)

    # Check copied files
    wheels = list(dest_dir.glob("*.whl"))
    wheel_names = sorted(w.name for w in wheels)
    assert wheel_names == ["a.whl", "b.whl"]

    # Check content was copied correctly
    assert (dest_dir / "a.whl").read_text() == "a"
    assert (dest_dir / "b.whl").read_text() == "b"

    # Check logging
    out = capsys.readouterr().out
    assert "unpacked 2 wheels" in out


def test_unpack_wheels_overwrites_existing(tmp_path, capsys):
    libs_dir = tmp_path / "libs"
    dest_dir = tmp_path / "dest"
    libs_dir.mkdir()
    dest_dir.mkdir()

    (libs_dir / "x.whl").write_text("from libs")
    (dest_dir / "x.whl").write_text("original")

    unpack.unpack_wheels(libs_dir, dest_dir)

    # Should overwrite existing
    assert (dest_dir / "x.whl").read_text() == "from libs"

    out = capsys.readouterr().out
    assert "unpacked 1 wheels" in out
