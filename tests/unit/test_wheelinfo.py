from __future__ import annotations

import json
import re
from email.parser import Parser
from importlib import resources
from typing import Any, Dict, List, Mapping

import pytest

from pychubby.model.wheelinfo_model import WheelInfo, ExtrasInfo


# ---------- helpers (test-local) ----------

EXTRA_RE = re.compile(r"""extra\s*==\s*['"]([^'"]+)['"]""")

def parse_metadata_text_to_dict(text: str) -> Dict[str, Any]:
    """Turn RFC822 METADATA text into the dict shape your code expects."""
    msg = Parser().parsestr(text)

    def many(name: str) -> List[str]:
        vals = msg.get_all(name) or []
        return [v.strip() for v in vals if v and v.strip()]

    meta: Dict[str, Any] = {
        "name": msg.get("Name"),
        "version": msg.get("Version"),
        "requires_python": msg.get("Requires-Python"),
        "provides_extra": many("Provides-Extra"),
        "requires_dist": many("Requires-Dist"),
    }
    # drop Nones
    return {k: v for k, v in meta.items() if v is not None}

def expected_extras_from_text(text: str) -> Dict[str, List[str]]:
    """
    Compute the expected {extra: [spec,...]} mapping directly from raw METADATA text,
    by reading Requires-Dist lines and extracting the 'extra == "..."' markers.
    """
    expected: Dict[str, List[str]] = {}
    for line in text.splitlines():
        if not line.startswith("Requires-Dist:"):
            continue
        body = line.split(":", 1)[1].strip()
        if ";" in body:
            spec, marker = body.split(";", 1)
            m = EXTRA_RE.search(marker)
            if m:
                extra = m.group(1)
                expected.setdefault(extra, [])
                spec = spec.strip()
                if spec not in expected[extra]:
                    expected[extra].append(spec)
    # Ensure declared extras exist even if no gated deps
    for line in text.splitlines():
        if line.startswith("Provides-Extra:"):
            name = line.split(":", 1)[1].strip()
            expected.setdefault(name, [])
    return expected


# ---------- fixtures ----------

@pytest.fixture(scope="module")
def metadata_text() -> str:
    """
    Load tests data: test_data/wheel_metadata.txt
    (Make sure test_data is a package with that file included.)
    """
    with resources.files("tests.test_data").joinpath("wheel_metadata.txt").open("r", encoding="utf-8") as f:
        return f.read()

@pytest.fixture(scope="module")
def metadata_dict(metadata_text: str) -> Dict[str, Any]:
    return parse_metadata_text_to_dict(metadata_text)


# ---------- tests ----------

def test_extrasinfo_groups_match_metadata_markers(metadata_text: str, metadata_dict: Mapping[str, Any]):
    # What ExtrasInfo computes from METADATA
    extras = ExtrasInfo.from_metadata(metadata_dict).to_mapping()

    # What we expect by regexing the raw lines
    expected = expected_extras_from_text(metadata_text)

    # Must have the same extra names
    assert set(extras.keys()) == set(expected.keys())

    # And each list of specs should match exactly (order doesn’t strictly matter, but we preserved it)
    for name, specs in expected.items():
        assert extras.get(name, []) == specs


def test_wheelinfo_includes_extras(metadata_dict: Mapping[str, Any]):
    """
    Build a minimal WheelInfo using the parsed METADATA, then ensure extras are present
    and survive a to_mapping() round-trip.
    """
    # Build ExtrasInfo from METADATA
    extras = ExtrasInfo.from_metadata(metadata_dict)

    # Minimal WheelInfo (fill required fields; you can adapt if your signature differs)
    wi = WheelInfo(
        filename=(metadata_dict.get("name") or "pkg") + ".whl",
        name=metadata_dict.get("name") or "pkg",
        version=metadata_dict.get("version") or "0",
        size=0,
        sha256="",
        tags=[],
        requires_python=metadata_dict.get("requires_python"),
        deps=[],                  # base deps not under extras are outside this test’s scope
        source=None,
        meta=dict(metadata_dict),
        wheel={},
        extras=extras)

    # Has extras
    assert wi.extras.to_mapping()  # non-empty dict or {} if the fixture has none

    # Round-trip via to_mapping preserves extras
    mapping = wi.to_mapping()
    assert "extras" in mapping
    assert isinstance(mapping["extras"], dict)
    # spot check: extras in mapping match the constructed ExtrasInfo
    assert mapping["extras"] == wi.extras.to_mapping()


def test_wheelinfo_matches_testdata(metadata_dict: Mapping[str, Any]):
    wi = WheelInfo(
        filename=f"{metadata_dict.get('name','pkg')}.whl",
        name=metadata_dict.get("name") or "pkg",
        version=metadata_dict.get("version") or "0",
        size=0,
        sha256="",
        tags=[],
        requires_python=metadata_dict.get("requires_python"),
        deps=[],  # you can parse base deps too if you want
        source=None,
        meta=dict(metadata_dict),
        wheel={},
        extras=ExtrasInfo.from_metadata(metadata_dict))
    current = wi.to_mapping()

    testdata_path = resources.files("tests.test_data").joinpath("wheelinfo.json")
    if not testdata_path.is_file():
        pytest.skip("Test data file wheelinfo.json missing")

    testdata = json.loads(testdata_path.read_text(encoding="utf-8"))

    assert current == testdata
