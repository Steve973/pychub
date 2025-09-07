from __future__ import annotations

import argparse
from pathlib import Path

from pychub.package.bt_options_processor import process_options


def main():
    parser = argparse.ArgumentParser(
        prog="pychub",
        description="Package a wheel and its dependencies into a .chub archive")

    parser.add_argument(
        "wheel",
        type=Path,
        help="Path to the .whl file")

    parser.add_argument(
        "-a",
        "--add-wheel",
        nargs="+",
        type=Path,
        help="One or more additional wheels to include",
        action="append")

    parser.add_argument(
        "-c",
        "--chub",
        type=Path,
        help="Optional path to output .chub (defaults to <name>-<version>.chub)")

    parser.add_argument(
        "--chubproject",
        type=Path,
        help="Optional path to use chubproject.toml as option config source")

    parser.add_argument(
        "--chubproject-save",
        type=Path,
        help="Optional path to output options config to chubproject.toml")

    parser.add_argument(
        "-e",
        "--entrypoint",
        help="Optional 'module:function' to run after install")

    parser.add_argument(
        "-i",
        "--include",
        nargs="+",
        metavar="FILE[::dest]",
        help="Extra files to include (dest is relative to install dir)")

    parser.add_argument(
        "-m",
        "--metadata-entry",
        nargs="+",
        action="append",
        metavar="KEY=VALUE[,VALUE...]",
        help="Extra metadata entries to embed in .chubconfig")

    parser.add_argument(
        "-o",
        "--post-script",
        nargs="+",
        action="append",
        metavar="POST_SCRIPT",
        help="Post-install scripts to include and run")

    parser.add_argument(
        "-p",
        "--pre-script",
        nargs="+",
        action="append",
        metavar="PRE_SCRIPT",
        help="Pre-install scripts to include and run")

    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Set output to verbose")

    parser.add_argument(
        "-v",
        "--version",
        action="store_true",
        help="Show version and exit")

    process_options(parser.parse_args())


if __name__ == "__main__":
    main()
