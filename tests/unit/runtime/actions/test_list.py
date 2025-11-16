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


# --- Quiet mode with config ---

def test_list_wheels_quiet_with_config_outputs_compact_format(monkeypatch, tmp_path, capsys):
    cfg = SimpleNamespace(
        wheels={
            "A.whl": ["dep1.whl", "dep2.whl"],
            "B.whl": [],
        }
    )
    monkeypatch.setattr(list_action, "load_chubconfig", lambda root: cfg)

    list_action.list_wheels(tmp_path, quiet=True)

    out = capsys.readouterr().out.strip().splitlines()
    assert out == [
        "w:A.whl, d:2",
        "w:B.whl, d:0",
    ]


def test_list_wheels_quiet_with_empty_config_outputs_nothing(monkeypatch, tmp_path, capsys):
    cfg = SimpleNamespace(wheels={})
    monkeypatch.setattr(list_action, "load_chubconfig", lambda root: cfg)

    list_action.list_wheels(tmp_path, quiet=True)

    # Should fall back to libs scan, which finds nothing, and quiet mode suppresses message
    assert capsys.readouterr().out.strip() == ""


# --- Verbose mode with config ---

def test_list_wheels_verbose_with_config_outputs_detailed_format(monkeypatch, tmp_path, capsys):
    cfg = SimpleNamespace(
        wheels={
            "Main.whl": ["dep1.whl", "dep2.whl"],
            "Other.whl": [],
        }
    )
    monkeypatch.setattr(list_action, "load_chubconfig", lambda root: cfg)

    list_action.list_wheels(tmp_path, verbose=True)

    out = capsys.readouterr().out.strip().splitlines()
    assert out == [
        "Wheel: Main.whl",
        "  Deps:",
        "  - dep1.whl",
        "  - dep2.whl",
        "Wheel: Other.whl",
    ]


def test_list_wheels_verbose_with_no_deps_omits_deps_section(monkeypatch, tmp_path, capsys):
    cfg = SimpleNamespace(
        wheels={
            "Solo.whl": [],
        }
    )
    monkeypatch.setattr(list_action, "load_chubconfig", lambda root: cfg)

    list_action.list_wheels(tmp_path, verbose=True)

    out = capsys.readouterr().out.strip().splitlines()
    assert out == ["Wheel: Solo.whl"]


def test_list_wheels_verbose_with_multiple_wheels_some_with_deps(monkeypatch, tmp_path, capsys):
    cfg = SimpleNamespace(
        wheels={
            "First.whl": ["a.whl"],
            "Second.whl": [],
            "Third.whl": ["x.whl", "y.whl", "z.whl"],
        }
    )
    monkeypatch.setattr(list_action, "load_chubconfig", lambda root: cfg)

    list_action.list_wheels(tmp_path, verbose=True)

    out = capsys.readouterr().out.strip().splitlines()
    assert out == [
        "Wheel: First.whl",
        "  Deps:",
        "  - a.whl",
        "Wheel: Second.whl",
        "Wheel: Third.whl",
        "  Deps:",
        "  - x.whl",
        "  - y.whl",
        "  - z.whl",
    ]


def test_list_wheels_fallback_with_verbose_flag(tmp_path, capsys):
    # Verbose mode doesn't affect fallback (scanning libs/)
    libs = tmp_path / "libs"
    libs.mkdir()
    (libs / "x.whl").write_text("fake")
    (libs / "y.whl").write_text("fake")

    list_action.list_wheels(tmp_path, verbose=True)

    out = capsys.readouterr().out.strip().splitlines()
    assert out == ["x.whl", "y.whl"]


def test_list_wheels_quiet_and_verbose_together_quiet_wins(monkeypatch, tmp_path, capsys):
    # When both quiet and verbose are set, quiet formatting takes precedence
    cfg = SimpleNamespace(
        wheels={
            "Test.whl": ["dep.whl"],
        }
    )
    monkeypatch.setattr(list_action, "load_chubconfig", lambda root: cfg)

    list_action.list_wheels(tmp_path, quiet=True, verbose=True)

    out = capsys.readouterr().out.strip().splitlines()
    # Quiet mode has priority over verbose
    assert out == ["w:Test.whl, d:1"]


def test_list_wheels_with_config_but_produces_empty_lines(monkeypatch, tmp_path, capsys):
    # Edge case: config.wheels is truthy, but the line list ends up empty
    # This tests the `elif not quiet` branch
    # We achieve this by having a config that passes the truthiness check
    # but doesn't produce any output lines

    # Create a minimal truthy wheels object that won't produce lines
    class EmptyWheelsdict(dict):
        def __bool__(self):
            return True  # Truthy

        def items(self):
            return []  # But produces no items

    cfg = SimpleNamespace(wheels=EmptyWheelsdict())
    monkeypatch.setattr(list_action, "load_chubconfig", lambda root: cfg)

    list_action.list_wheels(tmp_path)

    out = capsys.readouterr().out.strip()
    assert out == "(no wheels found)"
