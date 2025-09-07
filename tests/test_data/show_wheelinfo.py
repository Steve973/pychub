import json
from email.parser import Parser
from pathlib import Path

from pychub.model.wheelinfo_model import WheelInfo, ExtrasInfo  # adjust import paths


def parse_metadata_text_to_dict(text: str) -> dict:
    msg = Parser().parsestr(text)
    def many(name): return [v.strip() for v in (msg.get_all(name) or []) if v and v.strip()]
    meta = {
        "name": msg.get("Name"),
        "version": msg.get("Version"),
        "requires_python": msg.get("Requires-Python"),
        "provides_extra": many("Provides-Extra"),
        "requires_dist": many("Requires-Dist"),
    }
    return {k: v for k, v in meta.items() if v is not None}

def main():
    txt = Path(__file__).with_name("wheel_metadata.txt").read_text(encoding="utf-8")
    meta = parse_metadata_text_to_dict(txt)

    wi = WheelInfo(
        filename=f"{meta.get('name','pkg')}.whl",
        name=meta.get("name","pkg"),
        version=meta.get("version","0"),
        size=0,
        sha256="",
        tags=[],
        requires_python=meta.get("requires_python"),
        deps=[],                   # base deps not tied to extras (optional)
        source=None,
        meta=dict(meta),           # raw normalized metadata for reference
        wheel={},
        extras=ExtrasInfo.from_metadata(meta),
    )

    print(json.dumps(wi.to_mapping(), indent=2, sort_keys=True))

if __name__ == "__main__":
    main()
