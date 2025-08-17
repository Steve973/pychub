import sys
import importlib.metadata as im

from pychubby.runtime.actions.discover import discover_wheels


def show_version(libs_dir) -> None:
    print(f"Python: {sys.version.split()[0]}")

    try:
        version = im.version("pychubby")
        print(f"pychubby: {version}")
    except im.PackageNotFoundError:
        print("pychubby: (not installed)")

    wheels = discover_wheels(libs_dir, only=None)
    print("Bundled wheels:")
    if wheels:
        for w in wheels:
            print(f"  - {w.name}")
    else:
        print("  (none)")