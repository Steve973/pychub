# rt_options_processor.py

COMMANDS = [
    "dry-run",
    "exec",
    "help",
    "info",
    "list",
    "no-post-scripts",
    "no-pre-scripts",
    "no-scripts",
    "quiet",
    "run [ENTRYPOINT]",
    "show-scripts",
    "show-compatibility"
    "unpack [DIR]",
    "venv DIR",
    "version",
    "verbose"
]

COMPATIBLE_OPTIONS = {
    "dry-run": [
        "exec",
        "no-post-scripts",
        "no-pre-scripts",
        "no-scripts",
        "quiet",
        "run",
        "unpack",
        "venv",
        "verbose"
    ],
    "exec": [
        "dry-run",
        "no-post-scripts",
        "no-pre-scripts",
        "no-scripts",
        "quiet",
        "run",
        "verbose"
    ],
    "help": [
        "quiet",
        "verbose"
    ],
    "info": [
        "list",
        "quiet",
        "show-compatibility",
        "show-scripts",
        "version",
        "verbose"
    ],
    "list": [
        "info",
        "quiet",
        "show-compatibility",
        "show-scripts",
        "verbose",
        "version"
    ],
    "no-post-scripts": [
        "dry-run",
        "exec",
        "no-pre-scripts",
        "no-scripts",
        "quiet",
        "run",
        "venv",
        "verbose"
    ],
    "no-pre-scripts": [
        "dry-run",
        "exec",
        "no-post-scripts",
        "no-scripts",
        "quiet",
        "run",
        "venv",
        "verbose"
    ],
    "no-scripts": [
        "dry-run",
        "exec",
        "no-post-scripts",
        "no-pre-scripts",
        "quiet",
        "run",
        "venv",
        "verbose"
    ],
    "quiet": [
        "dry-run",
        "exec",
        "help",
        "info",
        "list",
        "no-post-scripts",
        "no-pre-scripts",
        "no-scripts",
        "run",
        "show-scripts",
        "show-compatibility",
        "unpack",
        "venv",
        "verbose",
        "version"
    ],
    "run": [
        "dry-run",
        "exec",
        "no-post-scripts",
        "no-pre-scripts",
        "no-scripts",
        "quiet",
        "venv",
        "verbose"
    ],
    "show-compatibility": [
        "info",
        "list",
        "quiet",
        "show-scripts",
        "verbose",
        "version"
    ],
    "show-scripts": [
        "info",
        "quiet",
        "list",
        "show-compatibility",
        "verbose",
        "version"
    ],
    "unpack": [
        "dry-run",
        "quiet",
        "verbose"
    ],
    "venv": [
        "dry-run",
        "no-post-scripts",
        "no-pre-scripts",
        "no-scripts",
        "quiet",
        "run",
        "verbose"
    ],
    "verbose": [
        "dry-run",
        "exec",
        "help",
        "info",
        "list",
        "no-post-scripts",
        "no-pre-scripts",
        "no-scripts",
        "quiet",
        "run",
        "show-scripts",
        "show-compatibility",
        "unpack",
        "venv",
        "version"
    ],
    "version": [
        "info",
        "list",
        "quiet",
        "show-compatibility",
        "show-scripts",
        "verbose"
    ]
}

INCOMPATIBLE_OPTIONS = {
    "dry-run": [
        "help",
        "info",
        "list",
        "show-compatibility",
        "show-scripts",
        "version"
    ],
    "exec": [
        "help",
        "info",
        "list",
        "show-compatibility",
        "show-scripts",
        "unpack",
        "venv",
        "version"
    ],
    "help": [
        "dry-run",
        "exec",
        "info",
        "list",
        "no-post-scripts",
        "no-pre-scripts",
        "no-scripts",
        "run",
        "show-compatibility",
        "show-scripts",
        "unpack",
        "venv",
        "version"
    ],
    "info": [
        "dry-run",
        "exec",
        "help",
        "no-post-scripts",
        "no-pre-scripts",
        "no-scripts",
        "run",
        "unpack",
        "venv"
    ],
    "list": [
        "dry-run",
        "exec",
        "help",
        "no-post-scripts",
        "no-pre-scripts",
        "no-scripts",
        "run",
        "unpack",
        "venv"
    ],
    "no-post-scripts": [
        "help",
        "info",
        "list",
        "show-compatibility",
        "show-scripts",
        "unpack",
        "version"
    ],
    "no-pre-scripts": [
        "help",
        "info",
        "list",
        "show-compatibility",
        "show-scripts",
        "unpack",
        "version"
    ],
    "no-scripts": [
        "help",
        "info",
        "list",
        "show-compatibility",
        "show-scripts",
        "unpack",
        "version"
    ],
    "quiet": [],
    "run": [
        "help",
        "info",
        "list",
        "show-compatibility",
        "show-scripts",
        "unpack",
        "version"
    ],
    "show-scripts": [
        "dry-run",
        "exec",
        "help",
        "no-post-scripts",
        "no-pre-scripts",
        "no-scripts",
        "run",
        "unpack",
        "venv"
    ],
    "show-compatibility": [
        "dry-run",
        "exec",
        "help",
        "no-post-scripts",
        "no-pre-scripts",
        "no-scripts",
        "run",
        "unpack",
        "venv"
    ],
    "unpack": [
        "exec",
        "help",
        "info",
        "list",
        "no-post-scripts",
        "no-pre-scripts",
        "no-scripts",
        "run",
        "show-compatibility",
        "show-scripts",
        "venv",
        "version"
    ],
    "venv": [
        "exec",
        "help",
        "info",
        "list",
        "show-compatibility",
        "show-scripts",
        "unpack",
        "version"
    ],
    "verbose": [],
    "version": [
        "dry-run",
        "exec",
        "help",
        "no-post-scripts",
        "no-pre-scripts",
        "no-scripts",
        "run",
        "unpack",
        "venv"
    ]
}
# ---------- central validation + implications ----------

from argparse import Namespace

# Single source of truth for option keys (no COMMANDS parsing needed)
_OPT_KEYS = set(COMPATIBLE_OPTIONS) | set(INCOMPATIBLE_OPTIONS)

def _active_options(args: Namespace):
    active = set()
    for dest, val in vars(args).items():
        if dest.startswith("_"):
            continue
        opt = dest.replace("_", "-")
        if opt not in _OPT_KEYS:
            continue
        if isinstance(val, bool):
            if val:
                active.add(opt)
        else:
            if val is not None:
                active.add(opt)  # includes "", DIR strings, etc.
    return active

def _apply_implications(args: Namespace):
    # why: enforce implied flags per docs/matrix in one place
    if getattr(args, "no_scripts", False):
        args.no_pre_scripts = True
        args.no_post_scripts = True
    if getattr(args, "exec", False):
        args.no_scripts = True
        args.no_pre_scripts = True
        args.no_post_scripts = True
    if getattr(args, "quiet", False):
        args.verbose = False  # quiet wins

def validate_and_imply(args: Namespace):
    _apply_implications(args)
    active = _active_options(args)
    errors = []
    for opt in active:
        for bad in INCOMPATIBLE_OPTIONS.get(opt, []):
            if bad in active:
                errors.append(f"--{opt} is incompatible with --{bad}")
    if errors:
        raise ValueError(", ".join(errors))
    return args
