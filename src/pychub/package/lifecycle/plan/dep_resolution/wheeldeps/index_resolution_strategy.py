import subprocess
import sys
from pathlib import Path
from typing import List

import requests
from packaging.requirements import Requirement
from packaging.version import Version, InvalidVersion

from pychub.package.lifecycle.plan.dep_resolution.wheeldeps.wheel_resolution_strategy_base import WheelResolutionStrategy


class IndexResolutionStrategy(WheelResolutionStrategy):
    """Resolve all wheel variants of a dependency from a PyPI-style index."""
    name = "index"

    @staticmethod
    def fetch_all_wheel_variant_urls(
        requirement: str,
        index_url: str = "https://pypi.org/pypi") -> List[str]:
        """
        Given a requirement (e.g. 'torch==2.2.0'), fetch all matching wheel URLs
        from the specified index. If no version constraint is given, fetch the latest release.
        """
        try:
            req = Requirement(requirement)
        except Exception as e:
            raise ValueError(f"Could not parse requirement '{requirement}': {e}")

        pkg_name = req.name
        try:
            resp = requests.get(f"{index_url}/{pkg_name}/json", timeout=10)
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            raise RuntimeError(f"Failed to fetch metadata for {pkg_name}: {e}")

        # Decide which releases to include
        if not req.specifier:
            # No version constraint → just latest
            latest_ver = data.get("info", {}).get("version")
            releases = {latest_ver: data["releases"].get(latest_ver, [])} if latest_ver else {}
        else:
            releases = {
                ver: files
                for ver, files in data.get("releases", {}).items()
                if IndexResolutionStrategy._version_matches(ver, req)
            }

        # Collect all wheel URLs across those releases
        wheel_urls: List[str] = []
        for ver, files in releases.items():
            for f in files:
                fn = f.get("filename", "")
                if fn.endswith(".whl"):
                    url = f.get("url")
                    if url:
                        wheel_urls.append(url)

        if not wheel_urls:
            raise RuntimeError(f"No wheel variants found for {requirement}")
        return wheel_urls

    @staticmethod
    def _version_matches(ver_str: str, req: Requirement) -> bool:
        try:
            ver = Version(ver_str)
        except InvalidVersion:
            return False
        return not req.specifier or req.specifier.contains(ver, prereleases=True)

    def resolve(self, dependency: str, output_dir: Path) -> List[Path]:
        """
        Download all available wheel variants for a given dependency into output_dir.
        Returns a list of downloaded .whl Paths.
        """
        output_dir.mkdir(parents=True, exist_ok=True)
        before = set(output_dir.glob("*.whl"))

        wheel_urls = self.fetch_all_wheel_variant_urls(dependency)

        # Use pip download to fetch all of them directly by URL
        cmd = [
            sys.executable, "-m", "pip", "download",
            "--only-binary", ":all:",
            "--no-deps",
            "-d", str(output_dir),
        ] + wheel_urls

        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError(f"pip download failed for {dependency}:\n{result.stderr}")

        after = set(output_dir.glob("*.whl"))
        new_wheels = sorted(after - before)
        if not new_wheels:
            raise RuntimeError(f"No wheels downloaded for {dependency}")

        return [p.resolve() for p in new_wheels]
