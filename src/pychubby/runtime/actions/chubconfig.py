import yaml
import sys
from pathlib import Path

from pychubby.runtime.constants import CHUBCONFIG_FILENAME


def load_chubconfig(bundle_root: Path) -> list[dict]:
    config_file = bundle_root / CHUBCONFIG_FILENAME
    if not config_file.exists():
        return []
    try:
        with config_file.open("r", encoding="utf-8") as f:
            return list(yaml.safe_load_all(f))
    except Exception as e:
        print(f"Warning: failed to parse {CHUBCONFIG_FILENAME}: {e}", file=sys.stderr)
        return []
