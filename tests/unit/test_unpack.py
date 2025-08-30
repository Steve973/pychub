import pytest

from pychubby.runtime.actions import unpack


def test_unpack_chub_default_dest_and_counts(tmp_path, capsys):
    bundle = tmp_path / "bundle"
    (bundle / "libs" / "sub").mkdir(parents=True)
    (bundle / "scripts" / "tools").mkdir(parents=True)
    (bundle / "includes").mkdir(parents=True)

    # libs (2 files)
    (bundle / "libs" / "a.whl").write_text("a")
    (bundle / "libs" / "sub" / "b.whl").write_text("b")
    # scripts (2 files)
    (bundle / "scripts" / "run.sh").write_text("run")
    (bundle / "scripts" / "tools" / "helper.sh").write_text("help")
    # includes (1 file)
    (bundle / "includes" / "readme.txt").write_text("README")
    # config (1 file)
    (bundle / ".chubconfig").write_text("cfg")

    unpack.unpack_chub(bundle, dest=None)

    dest = tmp_path / "bundle_unpacked"
    assert dest.exists() and dest.is_dir()

    # libs copied + nested
    assert (dest / "libs" / "a.whl").read_text() == "a"
    assert (dest / "libs" / "sub" / "b.whl").read_text() == "b"
    # scripts copied + nested
    assert (dest / "scripts" / "run.sh").read_text() == "run"
    assert (dest / "scripts" / "tools" / "helper.sh").read_text() == "help"
    # includes copied
    assert (dest / "includes" / "readme.txt").read_text() == "README"
    # config copied at root
    assert (dest / ".chubconfig").read_text() == "cfg"

    out = capsys.readouterr().out.strip()
    assert f"unpacked 6 files to {dest}" in out


def test_unpack_chub_handles_missing_dirs_and_no_config(tmp_path, capsys):
    bundle = tmp_path / "bundle"
    bundle.mkdir()

    unpack.unpack_chub(bundle, dest=None)

    dest = tmp_path / "bundle_unpacked"
    assert dest.exists() and not any(dest.iterdir())
    assert "unpacked 0 files" in capsys.readouterr().out


def test_unpack_chub_copies_config_only(tmp_path, capsys):
    bundle = tmp_path / "bundle"
    bundle.mkdir()
    (bundle / ".chubconfig").write_text("cfg")

    unpack.unpack_chub(bundle, dest=None)

    dest = tmp_path / "bundle_unpacked"
    assert (dest / ".chubconfig").read_text() == "cfg"
    assert "unpacked 1 files" in capsys.readouterr().out


def test_unpack_chub_overwrites_existing_files(tmp_path, capsys):
    bundle = tmp_path / "bundle"
    (bundle / "libs").mkdir(parents=True)
    (bundle / "libs" / "x.whl").write_text("new")

    dest = tmp_path / "custom"
    (dest / "libs").mkdir(parents=True)
    (dest / "libs" / "x.whl").write_text("old")

    unpack.unpack_chub(bundle, dest)

    assert (dest / "libs" / "x.whl").read_text() == "new"
    assert f"unpacked 1 files to {dest}" in capsys.readouterr().out


def test_unpack_chub_respects_explicit_dest(tmp_path, capsys):
    bundle = tmp_path / "bundle"
    (bundle / "includes").mkdir(parents=True)
    (bundle / "includes" / "a.txt").write_text("A")

    explicit = tmp_path / "where" / "to" / "go"
    unpack.unpack_chub(bundle, explicit)

    assert (explicit / "includes" / "a.txt").read_text() == "A"
    out = capsys.readouterr().out
    assert f"unpacked 1 files to {explicit}" in out


def test_unpack_chub_creates_parent_dirs_for_nested_tree(tmp_path):
    bundle = tmp_path / "bundle"
    (bundle / "scripts" / "deep" / "dir").mkdir(parents=True)
    (bundle / "scripts" / "deep" / "dir" / "x.sh").write_text("x")

    dest = tmp_path / "d"
    unpack.unpack_chub(bundle, dest)

    assert (dest / "scripts" / "deep" / "dir" / "x.sh").read_text() == "x"


# Optional: lightly exercise the helper via missing source behavior through public API
@pytest.mark.parametrize("subdir", ["libs", "scripts", "includes"])
def test_unpack_chub_ignores_absent_source_dirs(tmp_path, subdir, capsys):
    bundle = tmp_path / "bundle"
    bundle.mkdir()
    # Only create one of the three, varying by param
    (bundle / subdir).mkdir()

    unpack.unpack_chub(bundle, None)

    dest = tmp_path / "bundle_unpacked"
    assert dest.exists()
    # No files created inside when the created subdir is empty
    assert not any((dest / subdir).glob("**/*"))
