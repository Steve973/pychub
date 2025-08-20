from pychubby.runtime.actions import list as list_action


def test_list_wheels_prints_none_message(tmp_path, capsys):
    list_action.list_wheels(tmp_path)

    out = capsys.readouterr().out.strip()
    assert out == "(no wheels found)"


def test_list_wheels_prints_sorted_wheel_names(tmp_path, capsys):
    (tmp_path / "zlib.whl").write_text("fake")
    (tmp_path / "alib.whl").write_text("fake")
    (tmp_path / "blib.whl").write_text("fake")
    (tmp_path / "not_a_wheel.txt").write_text("ignore me")

    list_action.list_wheels(tmp_path)

    out = capsys.readouterr().out.strip().splitlines()
    assert out == ["alib.whl", "blib.whl", "zlib.whl"]
