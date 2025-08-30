import os
import pathlib
import pytest

@pytest.fixture(autouse=True)
def _fixup_path_class_after_each_test():
    yield
    # force platform-appropriate concrete Path class
    correct = pathlib.PosixPath if os.name == "posix" else pathlib.WindowsPath
    if pathlib.Path is not correct:
        pathlib.Path = correct
