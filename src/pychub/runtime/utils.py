#!/usr/bin/env python3
from __future__ import annotations
import sys


def pep668_blocked(stderr_text: str | None) -> bool:
    if not stderr_text:
        return False
    s = stderr_text.lower()
    return "externally managed" in s or "externally-managed-environment" in s


def die(msg_or_code) -> None:
    if isinstance(msg_or_code, int):
        sys.exit(msg_or_code)
    print(f"pychub: {msg_or_code}", file=sys.stderr)
    sys.exit(2)
