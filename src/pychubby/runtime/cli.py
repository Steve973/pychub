#!/usr/bin/env python3
"""
pychubby CLI — Python-native wheel bundle installer/runner.

Default: install all wheels from ./libs into the current interpreter.
Options add entrypoint/file run, listing, dry-run, selective install, unpack.
"""
from __future__ import annotations

import argparse


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="pychubby",
        description="Install bundled wheels into the current Python env.")

    parser.add_argument("-d", "--dry-run",
        action="store_true",
        help="Show actions without performing them")

    parser.add_argument("-e", "--exec",
        action="store_true",
        help="Run the entrypoint directly instead of installing")

    parser.add_argument("-l", "--list",
        action="store_true",
        help="List bundled wheels and exit")

    parser.add_argument("--no-scripts",
        action="store_true",
        help="Skip post-install scripts")

    parser.add_argument("--no-deps",
        action="store_true",
        help="Install/unpack only the main wheel")

    parser.add_argument("-o", "--only",
        metavar="NAMES",
        nargs="+",
        help="Install/unpack only named wheels (comma or space separated)")

    parser.add_argument("--only-deps",
        action="store_true",
        help="Install/unpack only dependency wheels")

    parser.add_argument("-q", "--quiet",
        action="store_true",
        help="Suppress output wherever possible")

    parser.add_argument("-r", "--run",
        nargs="?",
        const="",
        metavar="ENTRYPOINT",
        help="Run baked or specified entrypoint")

    parser.add_argument("-u", "--unpack",
        nargs="?",
        const=".",
        metavar="DIR",
        help="Copy bundled wheels to current or specified directory and exit")

    parser.add_argument("--version",
        action="store_true",
        help="Show version info and exit")

    parser.add_argument("--venv",
        metavar="NAME",
        help="Create a venv and install wheels into it")

    parser.add_argument("-v", "--verbose",
        action="store_true",
        help="Extra logs wherever possible")

    return parser
