from pathlib import Path, PureWindowsPath

# pick the platform's concrete Path class (PosixPath on Linux, WindowsPath on Win)
BasePath = type(Path())

class CoercingPath(BasePath):
    """Accept 'C:\\foo\\bar' on POSIX by parsing as Windows then rematerializing."""
    def __new__(cls, *args, **kwargs):
        if args and isinstance(args[0], str) and "\\" in args[0]:
            parts = PureWindowsPath(args[0]).parts
            return super().__new__(cls, *parts)
        return super().__new__(cls, *args, **kwargs)
