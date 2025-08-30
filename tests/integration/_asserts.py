from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Iterable


def assert_rc_ok(proc, msg: str = "") -> None:
    assert proc.returncode == 0, msg or proc.stderr


def assert_rc_fail(proc, code: int | None = None) -> None:
    assert proc.returncode != 0, "expected non-zero exit code"
    if code is not None:
        assert proc.returncode == code, f"expected rc={code} got {proc.returncode}"


def assert_in_stdout(proc, *needles: str) -> None:
    text = proc.stdout or ""
    for n in needles:
        assert n.lower() in text.lower(), f"missing '{n}' in stdout"


def assert_in_stderr(proc, *needles: str) -> None:
    text = proc.stderr or ""
    for n in needles:
        assert n.lower() in text.lower(), f"missing '{n}' in stderr"


def assert_not_in_stdout(proc, *needles: str) -> None:
    text = proc.stdout or ""
    for n in needles:
        assert n.lower() not in text.lower(), f"unexpected '{n}' in stdout"


def assert_file_exists(path: Path) -> None:
    assert path.exists(), f"missing file: {path}"


def assert_unpacked_contains(dir_: Path, suffixes: Iterable[str]) -> None:
    """
    At least one file with each suffix exists under dir_ (non-recursive
    is usually enough for these tests).
    """
    names = [p.name for p in dir_.iterdir()] if dir_.exists() else []
    for suf in suffixes:
        assert any(n.endswith(suf) for n in names), f"missing '*{suf}'"


def assert_venv_python_exists(venv_path: Path) -> None:
    bin_dir = venv_path / ("Scripts" if os.name == "nt" else "bin")
    py = bin_dir / ("python.exe" if os.name == "nt" else "python3")
    assert py.exists(), f"venv interpreter missing at {py}"


def assert_quiet(proc) -> None:
    """
    Heuristic: in quiet mode, stdout should be very short (or empty) on
    success; stderr empty and rc==0.
    """
    assert_rc_ok(proc)
    assert len(proc.stdout.strip()) < 50, "too chatty in --quiet"
    assert (proc.stderr or "").strip() == "", "stderr should be empty on success"


def assert_verbose(proc, expect_patterns: Iterable[str] = ()) -> None:
    """
    Heuristic: in verbose mode, stdout should include debug-ish lines.
    You can pass a couple of stable substrings to check.
    """
    assert_rc_ok(proc)
    out = proc.stdout or ""
    for pat in expect_patterns:
        assert re.search(pat, out, flags=re.I), f"missing verbose pattern: {pat}"
