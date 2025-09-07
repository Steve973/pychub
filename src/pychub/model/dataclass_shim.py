from __future__ import annotations

import sys as _sys
from dataclasses import dataclass as _dataclass


# Compatibility shim: Python 3.9 dataclass has no "slots" parameter.
def dataclass(*args, **kwargs):
    if _sys.version_info < (3, 10):
        kwargs.pop("slots", None)
    return _dataclass(*args, **kwargs)
