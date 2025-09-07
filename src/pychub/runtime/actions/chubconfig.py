from __future__ import annotations

import sys
from pathlib import Path

from pychub.model.chubconfig_model import ChubConfig
from pychub.runtime.constants import CHUBCONFIG_FILENAME


def load_chubconfig(bundle_root: Path) -> ChubConfig | None:
    config_file = bundle_root / CHUBCONFIG_FILENAME
    if not config_file.exists():
        print(f"Warning: the .chubconfig file '{CHUBCONFIG_FILENAME}' does not exist", file=sys.stderr)
        return None
    try:
        return ChubConfig.from_file(config_file)
    except Exception as e:
        print(f"Warning: failed to parse {CHUBCONFIG_FILENAME}: {e}", file=sys.stderr)
        return None
