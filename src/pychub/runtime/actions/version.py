import sys
import importlib.metadata as im

from .discover import discover_wheels


def show_version(libs_dir) -> None:
    print(f"Python: {sys.version.split()[0]}")

    try:
        version = im.version("pychub")
        print(f"pychub: {version}")
    except im.PackageNotFoundError:
        print("pychub: (not installed)")

    wheels = discover_wheels(libs_dir)
    print("Bundled wheels:")
    if wheels:
        for w in wheels:
            print(f"  - {w.name}")
    else:
        print("  (none)")