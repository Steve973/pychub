from pathlib import Path
from typing import List

from pychub.package.lifecycle.plan.dep_resolution.pathdeps import PathDepStrategy


class DefaultPathDepStrategy(PathDepStrategy):
    """Fallback: scan all dicts for keys matching *depend* (but don't recurse into values of those keys)."""

    @staticmethod
    def label() -> str:
        return "Default"

    @staticmethod
    def can_handle(data: dict) -> bool:
        return True

    @staticmethod
    def extract_paths(data: dict, project_root: Path) -> List[Path]:
        out = []

        def _extract_from_deps(deps_section):
            if isinstance(deps_section, dict):
                for lib_spec in deps_section.values():
                    if isinstance(lib_spec, dict) and "path" in lib_spec:
                        out.append((project_root / lib_spec["path"]).resolve())
                    elif isinstance(lib_spec, list):
                        for item in lib_spec:
                            if isinstance(item, dict) and "path" in item:
                                out.append((project_root / item["path"]).resolve())
            elif isinstance(deps_section, list):
                for item in deps_section:
                    if isinstance(item, dict) and "path" in item:
                        out.append((project_root / item["path"]).resolve())

        def _scan_all(obj):
            if not isinstance(obj, dict):
                return
            for key, value in obj.items():
                if isinstance(key, str) and "depend" in key.lower():
                    _extract_from_deps(value)
                    # Do NOT recurse into value (don't go inside dependencies)
                elif isinstance(value, dict):
                    _scan_all(value)

        _scan_all(data)
        return out
