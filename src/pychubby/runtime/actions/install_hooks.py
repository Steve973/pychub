import subprocess
import sys
from pathlib import Path

from ..constants import CHUB_POST_INSTALL_SCRIPTS_DIR, CHUB_PRE_INSTALL_SCRIPTS_DIR, CHUB_SCRIPTS_DIR


def run_install_scripts(bundle_root: Path, script_type: str, scripts: list[str]):
    script_base = bundle_root / CHUB_SCRIPTS_DIR / script_type
    scripts.sort()
    for script in scripts:
        script_path = (script_base / script).resolve()
        if not script_path.exists():
            print(f"[warn] {script_type}-install script not found: {script}", file=sys.stderr)
            continue
        result = subprocess.run([script_path], check=False)
        if result.returncode != 0:
            print(f"[error] The {script_type}-install script failed: {script}", file=sys.stderr)
            sys.exit(result.returncode)


def run_post_install_scripts(bundle_root: Path, scripts: list[str]):
    run_install_scripts(bundle_root, CHUB_POST_INSTALL_SCRIPTS_DIR, scripts)


def run_pre_install_scripts(bundle_root: Path, scripts: list[str]):
    run_install_scripts(bundle_root, CHUB_PRE_INSTALL_SCRIPTS_DIR, scripts)
