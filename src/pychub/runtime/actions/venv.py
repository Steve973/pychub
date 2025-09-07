import os
import subprocess
import sys
import venv
from pathlib import Path


def _venv_python(venv_path: Path) -> Path:
    if os.name == "nt":
        return venv_path / "Scripts" / "python.exe"
    return venv_path / "bin" / "python"


def create_venv(path: Path, wheels: list[Path], dry_run: bool = False, quiet: bool = False, verbose: bool = False) -> None:
    if dry_run:
        print(f"[dry-run] would create venv at {path}")
        print("[dry-run] would install wheels:")
        for w in wheels:
            print("  ", w.name)
        return

    builder = venv.EnvBuilder(with_pip=True)
    builder.create(path)

    bin_dir = "Scripts" if os.name == "nt" else "bin"
    pip_path = path / bin_dir / "pip"

    cmd = [str(pip_path), "install"]
    if quiet:
        cmd += ["-q"]
    elif verbose:
        cmd += ["-v"]
    cmd += [str(w) for w in wheels]

    result = subprocess.run(cmd, capture_output=not verbose or quiet, text=True)
    if result.returncode != 0:
        sys.stderr.write(result.stderr or "")
        sys.exit(result.returncode)

    print(f"Created virtualenv at {path}")
    print(f"Use it with: source {path / bin_dir / 'activate'}")
