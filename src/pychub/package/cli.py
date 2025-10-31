from __future__ import annotations

import argparse
from pathlib import Path


def create_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="pychub",
        description="package a wheel and its dependencies into a .chub archive",
        formatter_class=argparse.RawTextHelpFormatter)

    parser.add_argument(
        "--analyze-compatibility",
        action="store_true",
        help="analyze target system compatibility and exit")

    parser.add_argument(
        "-c",
        "--chub",
        type=Path,
        help="optional path to output .chub (defaults to <name>-<version>.chub)")

    parser.add_argument(
        "--chubproject",
        type=Path,
        help="optional path to use chubproject.toml as option config source")

    parser.add_argument(
        "--chubproject-save",
        type=Path,
        help="optional path to output options config to chubproject.toml")

    parser.add_argument(
        "-e",
        "--entrypoint",
        help="optional 'module:function' to run after install")

    parser.add_argument(
        "--entrypoint-args",
        nargs=argparse.REMAINDER,
        type=str,
        default=[],
        metavar="ARG",
        help="default arguments to pass to entrypoint when chub is invoked\n"
             "(must be the last option; all following arguments are captured)")

    parser.add_argument(
        "-i",
        "--include",
        nargs="+",
        type=str,
        default=[],
        metavar="FILE[::dest]",
        action="extend",
        help="extra files to include (dest is relative to install dir)")

    parser.add_argument(
        "--include-chub",
        nargs="+",
        type=str,
        default=[],
        metavar="CHUBFILE",
        action="extend",
        help="chub files to include and install during the pre-install phase")

    parser.add_argument(
        "-m",
        "--metadata-entry",
        nargs="+",
        action="extend",
        metavar="KEY=VALUE[,VALUE...]",
        help="extra metadata entries to embed in .chubconfig")

    parser.add_argument(
        "-o",
        "--post-script",
        nargs="+",
        type=str,
        default=[],
        action="extend",
        metavar="POST_SCRIPT",
        help="post-install scripts to include and run")

    parser.add_argument(
        "-p",
        "--pre-script",
        nargs="+",
        type=str,
        default=[],
        action="extend",
        metavar="PRE_SCRIPT",
        help="pre-install scripts to include and run")

    parser.add_argument(
        "--project-path",
        type=str,
        default=".",
        metavar="PROJ_PATH",
        help="path to project root (defaults to current working directory)")

    parser.add_argument(
        "-t",
        "--table",
        type=str,
        help="optional table to use for options config (defaults to 'tool.pychub.package')")

    parser.add_argument(
        "--verbose",
        action="store_true",
        help="set output to verbose")

    parser.add_argument(
        "-v",
        "--version",
        action="store_true",
        help="show version and exit")

    parser.add_argument(
        "-w",
        "--wheel",
        nargs="+",
        type=str,
        default=[],
        required=False,
        action="extend",
        metavar=("WHEEL_PATH", "PKG_SPEC"),
        help=(
            "specify one or more:\n"
            " - wheels: each may be a local .whl path (e.g. ./dist/pkg-1.0.0.whl)\n"
            " - package: pip-style requirement (e.g. torch==2.2.0)\n"
            " - can be repeated or space-separated"))

    return parser
