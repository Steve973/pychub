import subprocess
import sys
from pathlib import Path

from ..constants import CHUB_POST_INSTALL_SCRIPTS_DIR, CHUB_PRE_INSTALL_SCRIPTS_DIR, CHUB_SCRIPTS_DIR
from ..utils import die


def run_install_scripts(bundle_root: Path, dry_run: bool, script_type: str, scripts: list[str]):
    script_base = bundle_root / CHUB_SCRIPTS_DIR / script_type
    scripts.sort()
    for script in scripts:
        script_path = (script_base / script).resolve()
        if not script_path.exists():
            print(f"[warn] {script_type}-install script not found: {script}", file=sys.stderr)
            continue
        if dry_run:
            print(f"[dry-run] Would install {script_type}-install script: {script}")
            continue
        if script_path.suffix.lower() == ".py":
            result = subprocess.run([sys.executable, str(script_path)], check=False)
        else:
            result = subprocess.run([str(script_path)], check=False)
        if result.returncode != 0:
            print(f"[error] The {script_type}-install script failed: {script}", file=sys.stderr)
            die(result.returncode)


def run_post_install_scripts(bundle_root: Path, dry_run: bool, scripts: list[str]):
    run_install_scripts(bundle_root, dry_run, CHUB_POST_INSTALL_SCRIPTS_DIR, scripts)


def run_pre_install_scripts(bundle_root: Path, dry_run: bool, scripts: list[str]):
    run_install_scripts(bundle_root, dry_run, CHUB_PRE_INSTALL_SCRIPTS_DIR, scripts)
