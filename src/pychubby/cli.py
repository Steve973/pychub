import argparse
import sys
from pathlib import Path
from .packager import build_chub
from importlib.metadata import PackageNotFoundError, version as get_version


def main():
    parser = argparse.ArgumentParser(
        prog="pychubby",
        description="Package a wheel and its dependencies into a .chub archive")

    parser.add_argument(
        "wheel",
        type=Path,
        help="Path to the .whl file to package")

    parser.add_argument(
        "-c", "--chub",
        type=Path,
        help="Optional path to output .chub file (defaults to <name>-<version>.chub)")

    parser.add_argument(
        "-e", "--entrypoint",
        help="Optional entrypoint to run after install, in 'module:function' format")

    parser.add_argument(
        "--includes", "-i",
        nargs="+",
        metavar="FILE[::dest]",
        help="Optional extra files to include in the wheel package directory")

    parser.add_argument(
        "-s", "--scripts",
        nargs="+",
        metavar="SCRIPT",
        help="Optional post-install scripts to include and run")

    parser.add_argument(
        "-m", "--metadata-entry",
        nargs=2,
        action="append",
        metavar=("KEY", "VALUE"),
        help="Metadata entry (can be repeated)")

    parser.add_argument("-v", "--version",
        action="store_true",
        help="Show version info and exit")

    args = parser.parse_args()

    if args.version:
        print(f"Python: {sys.version.split()[0]}")
        try:
            version = get_version("pychubby")
        except PackageNotFoundError:
            version = "(source)"
        print(f"pychubby: {version}")
        return

    # Parse metadata entries into a dict
    metadata = {}
    if args.metadata_entry:
        for key, value in args.metadata_entry:
            values = [v.strip() for v in value.split(",") if v.strip()]
            metadata[key] = values if len(values) > 1 else values[0]

    build_chub(
        wheel_path=args.wheel,
        chub_path=args.chub,
        entrypoint=args.entrypoint,
        post_install_scripts=args.scripts or [],
        included_files=args.includes or [],
        metadata=metadata)


if __name__ == "__main__":
    main()
