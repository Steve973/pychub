from __future__ import annotations

import sys
import shutil
import tempfile
import zipfile
from pathlib import Path

from .chubconfig import load_chubconfig
from .discover import discover_wheels
from .entrypoint import _run_entrypoint_with_python
from .install import install_wheels
from .list import list_wheels
from .install_hooks import run_post_install_scripts, run_pre_install_scripts
from .unpack import unpack_chub
from .venv import create_venv, _venv_python
from .version import show_version
from ..cli import build_parser
from ..constants import CHUB_LIBS_DIR
from ..utils import die
from ..rt_options_processor import validate_and_imply


def main(argv: list[str] | None = None) -> None:
    argv = sys.argv[1:] if argv is None else argv
    parser = build_parser()
    # We use parse_known_args so args after "--" fall into `passthru`.
    args, passthru = parser.parse_known_args(argv)
    ep_argv = passthru[1:] if (passthru and passthru[0] == "--") else (passthru or [])

    try:
        args = validate_and_imply(args)
    except ValueError as e:
        die(str(e))

    # Detect if we're inside a .chub archive
    cur_file = Path(__file__)
    cur_file_str = str(cur_file)
    if ".chub/" in cur_file_str:
        chub_root_str = cur_file_str[: cur_file_str.index(".chub/") + len(".chub")]
        cur_file = Path(chub_root_str)

    if zipfile.is_zipfile(cur_file):
        tmpdir = Path(tempfile.mkdtemp(prefix="chub-extract-"))
        with zipfile.ZipFile(cur_file) as zf:
            zf.extractall(tmpdir)
        bundle_root = tmpdir
    else:
        bundle_root = cur_file.resolve().parent

    bundle_config = load_chubconfig(bundle_root) or None
    libs_dir = (bundle_root / CHUB_LIBS_DIR).resolve()
    baked_entrypoint = bundle_config.entrypoint

    # Simple info actions
    if getattr(args, "list", False):
        list_wheels(bundle_root, quiet=args.quiet, verbose=args.verbose)
        return

    if getattr(args, "unpack", None):
        if not args.unpack:
            args.unpack = "."
        unpack_chub(bundle_root, Path(args.unpack))
        return

    if getattr(args, "version", False):
        show_version(libs_dir)
        return

    # Discover wheel files bundled in this archive
    wheels = discover_wheels(libs_dir)
    if not wheels:
        die("no wheels found in bundle")

    # --venv DIR performs a persistent install and returns
    if getattr(args, "venv", None):
        venv_path = Path(args.venv)
        create_venv(
            venv_path,
            wheels,
            dry_run=getattr(args, "dry_run", False),
            quiet=getattr(args, "quiet", False),
            verbose=getattr(args, "verbose", False))
        vpy = _venv_python(venv_path)

        if (not getattr(args, "no_scripts", False)) and (not getattr(args, "no_pre_scripts", False)):
            run_pre_install_scripts(bundle_root, args.dry_run, bundle_config.scripts.pre or [])
            install_wheels(
                wheels=wheels,
                dry_run=getattr(args, "dry_run", False),
                quiet=getattr(args, "quiet", False),
                verbose=getattr(args, "verbose", False),
                python=str(vpy))

        if (not getattr(args, "no_scripts", False)) and (not getattr(args, "no_post_scripts", False)):
            run_post_install_scripts(bundle_root, args.dry_run, bundle_config.scripts.post or [])

        target = baked_entrypoint if (args.run in (None, "")) else args.run
        code = _run_entrypoint_with_python(vpy, args.dry_run, target, ep_argv)
        if code != 0:
            die(code)
        return

    # decide if we should run after installation
    should_run = bool(getattr(args, "exec", False) or args.run is not None)

    # Non-ephemeral install into current env
    if not getattr(args, "exec", False):
        if not getattr(args, "no_scripts", False) and not getattr(args, "no_pre_scripts", False):
            run_pre_install_scripts(bundle_root, args.dry_run, bundle_config.scripts.pre or [])
        install_wheels(
            wheels=wheels,
            dry_run=getattr(args, "dry_run", False),
            quiet=getattr(args, "quiet", False),
            verbose=getattr(args, "verbose", False),
            python=None)
        if (not getattr(args, "no_scripts", False)) and (not getattr(args, "no_post_scripts", False)):
            run_post_install_scripts(bundle_root, args.dry_run, bundle_config.scripts.post or [])
        if should_run:
            # resolve target: runtime override wins; empty string means
            # no-arg --run → baked entrypoint
            target = baked_entrypoint if (args.run in (None, "")) else args.run
            code = _run_entrypoint_with_python(Path(sys.executable), args.dry_run, target, ep_argv)
            if code != 0:
                die(code)
        return

    # Ephemeral install: create temp venv, install into it, run, cleanup
    temp_root = Path(tempfile.mkdtemp(prefix="chub-venv-"))
    venv_dir = temp_root / "venv"
    try:
        create_venv(
            venv_dir,
            wheels,
            dry_run=getattr(args, "dry_run", False),
            quiet=getattr(args, "quiet", False),
            verbose=getattr(args, "verbose", False))
        vpy = _venv_python(venv_dir)
        install_wheels(
            wheels=wheels,
            dry_run=getattr(args, "dry_run", False),
            quiet=getattr(args, "quiet", False),
            verbose=getattr(args, "verbose", False),
            python=str(vpy))
        # resolve the target as above
        target = baked_entrypoint if (args.run in (None, "")) else args.run
        code = _run_entrypoint_with_python(vpy, args.dry_run, target, ep_argv)
        if code != 0:
            die(code)
    finally:
        shutil.rmtree(temp_root, ignore_errors=True)


if __name__ == "__main__":
    main()
