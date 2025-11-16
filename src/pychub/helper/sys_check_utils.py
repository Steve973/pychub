import subprocess
import sys


def check_python_version():
    if sys.version_info < (3, 9):
        raise Exception("Must be using Python 3.9 or higher")


def verify_pip() -> None:
    """Ensure pip is available for the current Python.

    We verify `python -m pip --version` instead of relying on a `pip` script on
    PATH.
    """
    code = subprocess.call([sys.executable, "-m", "pip", "--version"])  # noqa: S603
    if code != 0:
        raise RuntimeError(
            "pip not found. Ensure 'python -m pip' works in this environment.")
