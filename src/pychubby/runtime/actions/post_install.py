import subprocess
import sys
from pathlib import Path

def run_post_install_scripts(bundle_root: Path, scripts: list[str]):
    for script in scripts:
        script_path = (bundle_root / script).resolve()
        if not script_path.exists():
            print(f"[warn] post-install script not found: {script}", file=sys.stderr)
            continue
        result = subprocess.run([script_path], shell=True)
        if result.returncode != 0:
            sys.exit(f"Post-install script failed: {script}")
