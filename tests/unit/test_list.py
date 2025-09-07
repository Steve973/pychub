from types import SimpleNamespace

from pychub.runtime.actions import list as list_action


# --- Fallback (no config / libs scanning) ---

def test_list_wheels_prints_none_message_when_no_libs(tmp_path, capsys):
    list_action.list_wheels(tmp_path)
    out = capsys.readouterr().out.strip()
    assert out == "(no wheels found)"


def test_list_wheels_fallback_prints_sorted_wheel_names(tmp_path, capsys):
    libs = tmp_path / "libs"
    libs.mkdir()
    (libs / "zlib.whl").write_text("fake")
    (libs / "alib.whl").write_text("fake")
    (libs / "blib.whl").write_text("fake")
    (libs / "not_a_wheel.txt").write_text("ignore me")

    list_action.list_wheels(tmp_path)

    out = capsys.readouterr().out.strip().splitlines()
    assert out == ["alib.whl", "blib.whl", "zlib.whl"]


def test_list_wheels_fallback_ignores_subdirectories(tmp_path, capsys):
    libs = tmp_path / "libs"
    libs.mkdir()
    (libs / "top.whl").write_text("fake")
    sub = libs / "nested"
    sub.mkdir()
    (sub / "nested.whl").write_text("fake")

    list_action.list_wheels(tmp_path)
    out = capsys.readouterr().out.strip().splitlines()
    assert out == ["top.whl"]


def test_list_wheels_quiet_suppresses_none_message(tmp_path, capsys):
    list_action.list_wheels(tmp_path, quiet=True)
    assert capsys.readouterr().out.strip() == ""


# --- Config-driven output (preferred path) ---

def test_list_wheels_with_config_preserves_order_and_deps(monkeypatch, tmp_path, capsys):
    cfg = SimpleNamespace(
        wheels={
            "A.whl": ["dep1.whl", "dep2.whl"],
            "B.whl": [],
            "C.whl": ["x.whl"],
        }
    )
    monkeypatch.setattr(list_action, "load_chubconfig", lambda root: cfg)

    list_action.list_wheels(tmp_path)

    out = capsys.readouterr().out.strip().splitlines()
    assert out == [
        "A.whl",
        "dep1.whl",
        "dep2.whl",
        "B.whl",
        "C.whl",
        "x.whl",
    ]


def test_list_wheels_with_config_only_top_level_when_no_deps(monkeypatch, tmp_path, capsys):
    cfg = SimpleNamespace(wheels={"Solo.whl": []})
    monkeypatch.setattr(list_action, "load_chubconfig", lambda root: cfg)

    list_action.list_wheels(tmp_path)
    out = capsys.readouterr().out.strip().splitlines()
    assert out == ["Solo.whl"]


def test_list_wheels_with_empty_config_falls_back_to_libs(monkeypatch, tmp_path, capsys):
    # Empty mapping -> falsy, triggers fallback scanning
    cfg = SimpleNamespace(wheels={})
    monkeypatch.setattr(list_action, "load_chubconfig", lambda root: cfg)

    libs = tmp_path / "libs"
    libs.mkdir()
    (libs / "b.whl").write_text("fake")
    (libs / "a.whl").write_text("fake")

    list_action.list_wheels(tmp_path)
    out = capsys.readouterr().out.strip().splitlines()
    assert out == ["a.whl", "b.whl"]


def test_list_wheels_verbose_flag_does_not_change_output(monkeypatch, tmp_path, capsys):
    # Signature includes verbose, currently informational only
    libs = tmp_path / "libs"
    libs.mkdir()
    (libs / "a.whl").write_text("fake")
    (libs / "b.whl").write_text("fake")

    list_action.list_wheels(tmp_path, verbose=True)
    out = capsys.readouterr().out.strip().splitlines()
    assert out == ["a.whl", "b.whl"]
