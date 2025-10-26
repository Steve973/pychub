import sys as _sys
from dataclasses import dataclass as _dataclass
from functools import wraps


@wraps(_dataclass())
def dataclass(*args, **kwargs):
    if _sys.version_info < (3, 10):
        kwargs.pop("slots", None)
        kwargs.pop("kw_only", None)
    return _dataclass(*args, **kwargs)
