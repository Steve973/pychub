#!/usr/bin/env python3

from __future__ import annotations

import argparse


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="pychub",
        description=(
            "Install bundled wheels into the current Python environment; "
            "optionally run a baked or specified entrypoint."
        ),
        add_help=False,  # we add -h/--help explicitly to match table
    )

    # Core/runtime operations ----------------------------------------------
    p.add_argument("-d", "--dry-run",
                   action="store_true",
                   help="Show actions without performing them")

    p.add_argument("-e", "--exec",
                   action="store_true",
                   help=(
                       "Run entrypoint in a temporary venv (deleted after); "
                       "implies --no-scripts and a no-arg --run unless an "
                       "ENTRYPOINT is provided"
                   ))

    p.add_argument("-h", "--help",
                   action="help",
                   help="Show help and exit")

    p.add_argument("-i", "--info",
                   action="store_true",
                   help="Display .chub info and exit")

    p.add_argument("-l", "--list",
                   action="store_true",
                   help="List bundled wheels and exit")

    p.add_argument("--no-post-scripts",
                   action="store_true",
                   help="Skip post install scripts")

    p.add_argument("--no-pre-scripts",
                   action="store_true",
                   help="Skip pre install scripts")

    p.add_argument("--no-scripts",
                   action="store_true",
                   help="Skip pre/post install scripts")

    p.add_argument("-q", "--quiet",
                   action="store_true",
                   help="Suppress output wherever possible")

    p.add_argument("-r", "--run",
                   nargs="?",
                   const="",
                   metavar="ENTRYPOINT",
                   help=(
                       "Run the baked-in or specified ENTRYPOINT; omit the "
                       "value to use the baked one if present"
                   ))

    p.add_argument("-s", "--show-scripts",
                   action="store_true",
                   help="Show the pre/post install scripts and exit")

    p.add_argument("-u", "--unpack",
                   nargs="?",
                   const="",
                   metavar="DIR",
                   help=(
                       "Extract .chubconfig and all wheel-related files; if "
                       "DIR is omitted, extract under a derived directory in "
                       "the current working directory"
                   ))

    p.add_argument("--venv",
                   metavar="DIR",
                   help=(
                       "Create a venv at DIR and install wheels into it"
                   ))

    p.add_argument("--version",
                   action="store_true",
                   help="Show version info and exit")

    p.add_argument("-v", "--verbose",
                   action="store_true",
                   help="Extra logs wherever possible")

    # POSIX end-of-options; passthrough to entrypoint unchanged -------------
    p.add_argument("--", dest="entrypoint_args",
                   nargs=argparse.REMAINDER,
                   help=(
                       "Arguments after -- are forwarded unchanged to the "
                       "entrypoint"
                   ))

    return p


if __name__ == "__main__":  # pragma: no cover
    parser = build_parser()
    args = parser.parse_args()
