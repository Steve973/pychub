from __future__ import annotations
import sys
from pathlib import Path

from .chubconfig import load_chubconfig
from .discover import discover_wheels
from .entrypoint import maybe_run_entrypoint
from .install import install_wheels
from .list import list_wheels
from .post_install import run_post_install_scripts
from .unpack import unpack_wheels
from .venv import create_venv
from .version import show_version
from ..cli import build_parser
from ..constants import DEFAULT_LIBS_DIR
from ..utils import die


def main(argv: list[str] | None = None) -> None:
    argv = sys.argv[1:] if argv is None else argv
    args, passthru = build_parser().parse_known_args(argv)

    bundle_root = Path(__file__).resolve().parent
    libs_dir = (bundle_root / DEFAULT_LIBS_DIR).resolve()
    config = load_chubconfig(bundle_root)
    baked_entrypoint = config.get("baked_entrypoint")

    if args.exec:
        args.no_scripts = True

    if args.list:
        list_wheels(libs_dir)
        return

    if args.unpack:
        unpack_wheels(libs_dir, Path(args.unpack))
        return

    if args.version:
        show_version(libs_dir)
        return

    wheels = discover_wheels(libs_dir, only=args.only)
    if not wheels:
        die("no wheels found in bundle")

    if args.venv:
        create_venv(Path(args.venv), wheels,
                    dry_run=args.dry_run,
                    quiet=args.quiet,
                    verbose=args.verbose)
        return

    install_wheels(
        wheels=wheels,
        dry_run=args.dry_run,
        quiet=args.quiet,
        verbose=args.verbose,
        no_deps=args.no_deps,
    )

    if not args.no_scripts:
        run_post_install_scripts(bundle_root, config.get("post_install_scripts", []))

    if args.exec or args.run is not None:
        maybe_run_entrypoint(args.run, baked_entrypoint, passthru)


if __name__ == "__main__":
    main()
