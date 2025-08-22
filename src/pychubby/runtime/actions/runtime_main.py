from __future__ import annotations
import sys
import tempfile
import zipfile
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

    # Detect if we're inside a .chub archive
    chub_path = str(Path(__file__))
    print(f"Checking if {chub_path} is inside a .chub archive...")

    cur_file = Path(__file__)
    if ".chub/" in chub_path:
        chub_str = chub_path[:chub_path.index(".chub/") + len(".chub")]
        cur_file = Path(chub_str)

    if zipfile.is_zipfile(cur_file):
        tmpdir = Path(tempfile.mkdtemp(prefix="chub-extract-"))
        print(f"Extracting {cur_file} to {tmpdir}...")
        with zipfile.ZipFile(cur_file) as zf:
            zf.extractall(tmpdir)
        bundle_root = tmpdir
    else:
        print("Not inside a .chub archive, using current directory...")
        bundle_root = cur_file.resolve().parent

    config_docs = load_chubconfig(bundle_root)
    bundle_config = config_docs[0] if config_docs else {}
    module_name = f'{bundle_config["name"]}-{bundle_config["version"]}'
    libs_dir = (bundle_root / module_name / DEFAULT_LIBS_DIR).resolve()
    entrypoint = bundle_config["entrypoint"]

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
        run_post_install_scripts(
            bundle_root,
            bundle_config.get("post_install_scripts", []))

    if args.exec or args.run is not None:
        print(f"Running entrypoint: {entrypoint}...")
        maybe_run_entrypoint(args.run, entrypoint, passthru)


if __name__ == "__main__":
    main()
