from __future__ import annotations

from dataclasses import field
from typing import Any, Dict, List, Mapping

from pychub.model.chubconfig_model import dataclass


@dataclass(slots=True, frozen=True)
class Scripts:
    pre: List[str] = field(default_factory=list)
    post: List[str] = field(default_factory=list)

    @staticmethod
    def from_mapping(m: Mapping[str, Any] | None) -> "Scripts":
        if not m:
            return Scripts()
        pre = [str(x) for x in (m.get("pre") or [])]
        post = [str(x) for x in (m.get("post") or [])]
        return Scripts(pre=pre, post=post)

    def to_mapping(self) -> Dict[str, List[str]]:
        return {"pre": list(self.pre), "post": list(self.post)}
