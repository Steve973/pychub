from pathlib import Path

from .project_path_strategy_base import ProjectPathStrategy


class DefaultProjectPathStrategy(ProjectPathStrategy):
    """Fallback: scan all dicts for keys containing 'depend' (but don't recurse into values of those keys)."""

    name = "default"
    precedence = 1000

    @staticmethod
    def can_handle(data: dict) -> bool:
        return True

    @staticmethod
    def extract_paths(data: dict, project_root: Path) -> list[Path]:
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
