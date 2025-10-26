#!/usr/bin/env python3

import argparse
import os
import shutil
import subprocess
import sys
import pathlib
from typing import Optional


class ColorPrinter:
    def __init__(self, quiet: bool = False, debug_flag: bool = False):
        self.red = '\033[91m'
        self.green = '\033[92m'
        self.blue = '\033[94m'
        self.yellow = '\033[93m'
        self.magenta = '\033[95m'
        self.cyan = '\033[96m'
        self.white = '\033[97m'
        self.reset = '\033[0m'
        self.quiet = quiet
        self.debug_flag = debug_flag

    def _format(self, message, label, color):
        if self.quiet:
            return
        print(f"{message:<80} [ {color}{label:<5}{self.reset} ]")

    def ok(self, message):
        self._format(message, "OK", self.green)

    def fail(self, message):
        self._format(message, "FAIL", self.red)

    def warn(self, message):
        self._format(message, "WARN", self.yellow)

    def info(self, message):
        self._format(message, "INFO", self.blue)

    def debug(self, message):
        if self.debug_flag:
            self._format(message, "DEBUG", self.cyan)

    def block(self, content):
        for line in content.strip().splitlines():
            print(f"  {self.cyan}>{self.reset} {line}")

    def debug_block(self, content):
        if self.debug_flag:
            self.block(content)


SCRIPT_DIR: pathlib.Path = pathlib.Path(__file__).resolve().parent
PRINTER: Optional[ColorPrinter] = None


def get_printer(quiet: bool = False, debug: bool = False) -> ColorPrinter:
    global PRINTER
    if PRINTER is None:
        PRINTER = ColorPrinter(quiet, debug)
    return PRINTER


def check_python_version():
    version_info = sys.version_info
    if version_info.major != 3 or version_info.minor < 9:
        get_printer().fail("Python 3.9 or higher is required.")
        sys.exit(1)
    elif version_info.minor < 11:
        get_printer().warn(f"Python {version_info.major}.{version_info.minor} is supported, but 3.11+ is recommended.")
    else:
        get_printer().debug(f"Python {version_info.major}.{version_info.minor} detected.")


def check_requirements():
    missing = []
    for tool in ("pip", "poetry"):
        if shutil.which(tool):
           get_printer().debug(f"{tool} is installed")
        else:
            get_printer().debug(f"{tool} is not installed")
            missing.append(tool)
    if missing:
        get_printer().fail("Missing tools: " + ", ".join(missing))
        get_printer().fail("Please install them and re-run this script.")
        sys.exit(1)


def maybe_delete_venv(keep_venv=False):
    venv_path = SCRIPT_DIR / ".venv"
    if not keep_venv and venv_path.exists():
        shutil.rmtree(venv_path)
        get_printer().debug("Removed existing project .venv")
    else:
        get_printer().debug("Keeping existing .venv")


def clean_pycache(no_clean=False):
    if no_clean:
        get_printer().debug("Skipping pycache cleanup")
        return
    for dirpath, dirnames, filenames in os.walk(SCRIPT_DIR):
        for name in dirnames:
            if name == "__pycache__":
                full_path = os.path.join(dirpath, name)
                shutil.rmtree(full_path, ignore_errors=True)
    get_printer().debug("Removed pycache directories")


def clean_lock_file(no_clean=False):
    if no_clean:
        get_printer().debug("Skipping lock file cleanup")
        return
    lock_path = SCRIPT_DIR / "poetry.lock"
    if lock_path.exists():
        lock_path.unlink()
        get_printer().debug("Removed poetry.lock")


def init_venv():
    try:
        config_result = subprocess.run(["poetry", "config", "virtualenvs.in-project", "true", "--local"],
                                       capture_output=True, text=True, check=True)
        if config_result.stdout:
            get_printer().debug_block(f"{config_result.stdout}")
        install_result = subprocess.run(["poetry", "install", "--with", "dev"],
                                        capture_output=True, text=True, check=True)
        if install_result.stdout:
            get_printer().debug_block(f"{install_result.stdout}")
    except subprocess.CalledProcessError as e:
        get_printer().fail(f"Command failed: {e.cmd}")
        sys.exit(e.returncode)
    get_printer().debug("Installed dependencies with poetry")
    venv_bin = SCRIPT_DIR / ".venv" / "bin" / "activate"
    if venv_bin.exists():
        get_printer().info(f"To activate your virtualenv, run: source .venv/bin/activate")


def init_parser():
    parser = argparse.ArgumentParser(description="Setup pychub development environment.")
    parser.add_argument("-d", "--debug",
                        action="store_true",
                        help="Enable debug output")
    parser.add_argument("-k", "--keep-venv",
                        action="store_true",
                        help="Keep existing .venv (do not recreate)")
    parser.add_argument("-n", "--no-clean",
                        action="store_true",
                        help="Skip cleaning __pycache__ and lock files")
    parser.add_argument("-q", "--quiet",
                        action="store_true",
                        help="Suppress status output")
    return parser


def check_dev_env(keep_venv=False, no_clean=False):
    get_printer().info("Setting up the development environment")
    maybe_delete_venv(keep_venv)
    clean_pycache(no_clean)
    clean_lock_file(no_clean)


def check_prereq_deps():
    get_printer().info("Checking for the necessary Python dependencies")
    check_python_version()
    check_requirements()


def main():
    args = init_parser().parse_args()
    get_printer(args.quiet, args.debug).info("Starting pychub project setup")
    check_prereq_deps()
    check_dev_env(args.keep_venv, args.no_clean)
    init_venv()
    get_printer().ok("Project setup complete. You can now open your IDE.")


if __name__ == "__main__":
    main()
