import sys
import pytest
from types import SimpleNamespace
from pychubby.runtime.actions import entrypoint


@pytest.fixture
def fake_entrypoint():
    def make(name, func):
        return SimpleNamespace(name=name, group="console_scripts", load=lambda: func)
    return make


def test__select_console_entrypoint_with_select(monkeypatch, fake_entrypoint):
    fake_func = lambda: None
    ep1 = fake_entrypoint("foo", fake_func)
    ep2 = fake_entrypoint("bar", lambda: None)

    monkeypatch.setattr(entrypoint.im, "entry_points", lambda: SimpleNamespace(select=lambda group: [ep1, ep2]))

    result = entrypoint._select_console_entrypoint("foo")
    assert result.name == "foo"
    assert result.load() is fake_func


def test__select_console_entrypoint_with_fallback(monkeypatch, fake_entrypoint):
    fake_func = lambda: None
    ep = fake_entrypoint("mytool", fake_func)

    class FakeEPs:
        def select(self, group):
            raise Exception("nope")

        def __iter__(self):
            return iter([ep])

    monkeypatch.setattr(entrypoint.im, "entry_points", lambda: FakeEPs())

    result = entrypoint._select_console_entrypoint("mytool")
    assert result.name == "mytool"


def test_run_entrypoint_invokes_loaded_function(monkeypatch, fake_entrypoint):
    called = {}

    def dummy():
        called["was"] = True

    ep = fake_entrypoint("runme", dummy)

    monkeypatch.setattr(entrypoint, "_select_console_entrypoint", lambda name: ep)
    monkeypatch.setattr(entrypoint, "die", lambda msg: pytest.fail("die() should not be called"))

    old_argv = sys.argv[:]
    entrypoint.run_entrypoint("runme", ["--foo", "bar"])
    assert called["was"]
    assert sys.argv == ["runme", "--foo", "bar"]
    sys.argv = old_argv


def test_run_entrypoint_fails_if_not_found(monkeypatch):
    monkeypatch.setattr(entrypoint, "_select_console_entrypoint", lambda name: None)

    called = {}

    def fake_die(msg):
        called["msg"] = msg
        raise SystemExit(1)

    monkeypatch.setattr(entrypoint, "die", fake_die)

    with pytest.raises(SystemExit):
        entrypoint.run_entrypoint("nope", [])

    assert "no console_scripts entry point named 'nope'" in called["msg"]


@pytest.mark.parametrize(
    "run_arg, baked_arg, expected",
    [
        ("cli-main", None, "cli-main"),
        (None, "default-main", "default-main"),
    ]
)
def test_maybe_run_entrypoint(monkeypatch, run_arg, baked_arg, expected):
    called = {}

    def fake_run_entrypoint(name, args):
        called["name"] = name
        called["args"] = args

    monkeypatch.setattr(entrypoint, "run_entrypoint", fake_run_entrypoint)

    entrypoint.maybe_run_entrypoint(run_arg, baked_arg, ["--x", "1"])
    assert called["name"] == expected
    assert called["args"] == ["--x", "1"]
