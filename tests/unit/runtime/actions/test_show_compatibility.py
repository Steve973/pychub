import io
from pathlib import Path

from packaging.tags import sys_tags

from pychub.runtime.actions.show_compatibility import show_compatibility
import pychub.runtime.actions.show_compatibility as show_mod


universal_tag = "py3-none-any"
local_tags = {f"{tag.interpreter}-{tag.abi}-{tag.platform}" for tag in sys_tags()}
test_targets = [
    # CPython 3.10 - major Linux distros
    "cp310-cp310-manylinux_2_17_x86_64",
    "cp310-cp310-manylinux_2_28_x86_64",
    "cp310-cp310-manylinux_2_24_x86_64",
    "cp310-cp310-musllinux_1_1_x86_64",
    "cp310-cp310-win_amd64",
    "cp310-cp310-macosx_10_9_x86_64",
    "cp310-cp310-macosx_11_0_arm64",

    # CPython 3.11 - various platforms
    "cp311-cp311-manylinux_2_17_x86_64",
    "cp311-cp311-manylinux_2_28_x86_64",
    "cp311-cp311-musllinux_1_1_x86_64",
    "cp311-cp311-win_amd64",
    "cp311-cp311-win_arm64",
    "cp311-cp311-macosx_10_9_x86_64",
    "cp311-cp311-macosx_11_0_arm64",

    # CPython 3.12 - latest
    "cp312-cp312-manylinux_2_28_x86_64",
    "cp312-cp312-manylinux_2_17_x86_64",
    "cp312-cp312-musllinux_1_2_x86_64",
    "cp312-cp312-win_amd64",
    "cp312-cp312-win_arm64",
    "cp312-cp312-macosx_10_9_x86_64",
    "cp312-cp312-macosx_14_0_arm64",

    # Manylinux and musllinux for arm and i686
    "cp311-cp311-manylinux_2_17_aarch64",
    "cp311-cp311-manylinux_2_17_i686",
    "cp311-cp311-musllinux_1_1_aarch64",
    "cp311-cp311-musllinux_1_1_i686",

    # PyPy examples
    "pp310-pypy310_pp73-manylinux_2_17_x86_64",
    "pp311-pypy311_pp73-win_amd64",

    # ABI3 (for extension modules compatible with multiple CPython versions)
    "cp39-abi3-manylinux_2_17_x86_64",
    "cp310-abi3-win_amd64",
    "cp311-abi3-macosx_10_9_x86_64",

    # Older platforms (just for realism)
    "cp38-cp38-win_amd64",
    "cp37-cp37m-manylinux1_x86_64",
    "cp36-cp36m-macosx_10_6_x86_64",
    "cp27-cp27mu-manylinux1_x86_64",
]


class FakeConfig:
    def __init__(self, targets: list[str]):
        self.compatibility = {"targets": targets}


def test_print_lines(monkeypatch, capsys):
    """Test that _print_lines correctly prints each line."""
    # --- Arrange ---
    test_lines = [
        "Line 1",
        "Line 2",
        "Line 3",
    ]

    # --- Act ---
    show_mod._print_lines(test_lines)

    # --- Assert ---
    captured = capsys.readouterr()
    output_lines = captured.out.splitlines()

    assert len(output_lines) == 3
    assert output_lines[0] == "Line 1"
    assert output_lines[1] == "Line 2"
    assert output_lines[2] == "Line 3"


def test_print_lines_empty(capsys):
    """Test that _print_lines handles empty list."""
    # --- Act ---
    show_mod._print_lines([])

    # --- Assert ---
    captured = capsys.readouterr()
    assert captured.out == ""


def test_show_compatibility_no_targets(monkeypatch):
    # --- Act ---
    buf = io.StringIO()
    monkeypatch.setattr(show_mod, "load_chubconfig", lambda bundle_root: FakeConfig([]))
    monkeypatch.setattr(show_mod, "_print_lines", lambda lines: print("\n".join(lines), file=buf))
    show_compatibility(Path("../.."))

    # --- Assert ---
    buf.seek(0)
    output_lines = [line.rstrip() for line in buf.read().splitlines() if line.strip()]

    assert len(output_lines) == 3
    assert " - No supported targets found!" in output_lines
    assert " - No target compatibility detected!" in output_lines


def test_show_compatibility_malformed_targets(monkeypatch):
    """
    This test case is one that should never happen, but this ensures graceful handling.
    """
    # --- Act ---
    buf = io.StringIO()
    monkeypatch.setattr(show_mod, "load_chubconfig", lambda bundle_root: FakeConfig({}))
    monkeypatch.setattr(show_mod, "_print_lines", lambda lines: print("\n".join(lines), file=buf))
    show_compatibility(Path("../.."))

    # --- Assert ---
    buf.seek(0)
    output_lines = [line.rstrip() for line in buf.read().splitlines() if line.strip()]

    assert len(output_lines) == 3
    assert " - No supported targets found!" in output_lines
    assert " - No target compatibility detected!" in output_lines


def test_show_compatibility_universal_target(monkeypatch):
    # --- Act ---
    buf = io.StringIO()
    monkeypatch.setattr(show_mod, "load_chubconfig", lambda bundle_root: FakeConfig(["py3-none-any"]))
    monkeypatch.setattr(show_mod, "_print_lines", lambda lines: print("\n".join(lines), file=buf))
    show_compatibility(Path("../.."))

    # --- Assert ---
    buf.seek(0)
    output_lines = [line.rstrip() for line in buf.read().splitlines() if line.strip()]

    assert len(output_lines) == 2
    assert " - universal (py3-none-any)" in output_lines
    assert " - No target compatibility detected!" not in output_lines


def test_show_compatibility_invalid_target_list(monkeypatch):
    """
    This test case is one that should never happen, but we are testing what happens, anyway.
    """
    # --- Act ---
    buf = io.StringIO()
    local_tag = next(iter(local_tags))
    monkeypatch.setattr(show_mod, "load_chubconfig", lambda bundle_root: FakeConfig(["py3-none-any", local_tag]))
    monkeypatch.setattr(show_mod, "_print_lines", lambda lines: print("\n".join(lines), file=buf))
    show_compatibility(Path("../.."))

    # --- Assert ---
    buf.seek(0)
    output_lines = [line.rstrip() for line in buf.read().splitlines() if line.strip()]

    assert len(output_lines) == 3
    assert " - universal (py3-none-any)" in output_lines
    assert f" - {local_tag} (detected compatibility)" in output_lines
    assert " - No target compatibility detected!" not in output_lines


def test_show_compatibility_no_compatibility_detected(monkeypatch):
    # --- Act ---
    buf = io.StringIO()
    test_targets_without_local = []
    for target in test_targets:
        if target not in local_tags:
            test_targets_without_local.append(target)
    monkeypatch.setattr(show_mod, "load_chubconfig", lambda bundle_root: FakeConfig(test_targets_without_local))
    monkeypatch.setattr(show_mod, "_print_lines", lambda lines: print("\n".join(lines), file=buf))
    show_compatibility(Path("../.."))

    # --- Assert ---
    buf.seek(0)
    output_lines = [line.rstrip() for line in buf.read().splitlines() if line.strip()]

    assert len(output_lines) == 35
    assert " - No target compatibility detected!" in output_lines


def test_show_compatibility_only_local(monkeypatch):
    # --- Act ---
    buf = io.StringIO()
    monkeypatch.setattr(show_mod, "load_chubconfig", lambda bundle_root: FakeConfig([next(iter(local_tags))]))
    monkeypatch.setattr(show_mod, "_print_lines", lambda lines: print("\n".join(lines), file=buf))
    show_compatibility(Path("../.."))

    # --- Assert ---
    buf.seek(0)
    output_lines = [line.rstrip() for line in buf.read().splitlines() if line.strip()]

    assert len(output_lines) == 2
    assert "(detected compatibility)" in output_lines[1]
    assert " - No target compatibility detected!" not in output_lines


def test_show_compatibility(monkeypatch):
    # --- Act ---
    buf = io.StringIO()
    monkeypatch.setattr(show_mod, "load_chubconfig", lambda bundle_root: FakeConfig(test_targets))
    monkeypatch.setattr(show_mod, "_print_lines", lambda lines: print("\n".join(lines), file=buf))
    show_compatibility(Path("../.."))

    # --- Assert ---
    buf.seek(0)
    output_lines = [line.rstrip() for line in buf.read().splitlines() if line.strip()]

    assert len(output_lines) == 35
    assert " - No target compatibility detected!" not in output_lines
