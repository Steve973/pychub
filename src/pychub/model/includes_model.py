from __future__ import annotations

from typing import Any, Dict, Mapping, Optional

from pychub.model.chubconfig_model import dataclass


@dataclass(slots=True)
class IncludeSpec:
    src: str
    dest: Optional[str] = None

    @staticmethod
    def parse(item: str | Mapping[str, Any]) -> "IncludeSpec":
        if isinstance(item, str):
            if "::" in item:
                s, d = item.split("::", 1)
                return IncludeSpec(src=s.strip(), dest=(d.strip() or None))
            return IncludeSpec(src=item.strip())
        src = str(item.get("src", "")).strip()
        if not src:
            raise ValueError("include entry missing 'src'")
        dest_raw = item.get("dest")
        dest = None if dest_raw in (None, "") else str(dest_raw)
        return IncludeSpec(src=src, dest=dest)

    def as_string(self) -> str:
        return f"{self.src}::{self.dest}" if self.dest else self.src

    def to_mapping(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {"src": self.src}
        if self.dest:
            d["dest"] = self.dest
        return d
