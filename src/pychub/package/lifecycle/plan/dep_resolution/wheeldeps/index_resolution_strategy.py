import subprocess
import sys
from pathlib import Path

import requests
from packaging.requirements import Requirement
from packaging.version import Version, InvalidVersion

from pychub.package.lifecycle.plan.dep_resolution.wheeldeps.wheel_resolution_strategy_base import \
    WheelResolutionStrategy


class IndexResolutionStrategy(WheelResolutionStrategy):
    """Resolve all wheel variants of a dependency from a PyPI-style index."""

    name = "index"
    precedence = 70

    @staticmethod
    def fetch_all_wheel_variant_urls(
            requirement: str,
            index_url: str = "https://pypi.org/pypi") -> list[str]:
        """Fetch all wheel variant URLs for a given requirement from an index URL.

        This static method retrieves a list of URLs for the wheel variant distributions
        of a specified Python package requirement. It optionally allows the use of a
        custom index URL, with a default set to the PyPI primary URL. The method parses
        the requirement, fetches the package metadata from the index, and matches compatible
        releases based on the given version specifier.

        Args:
            requirement (str): The Python package requirement in PEP 508 format. This
                includes an optional version specifier to filter compatible distributions.
            index_url (str, optional): The base URL of the package index from which to
                fetch metadata. Defaults to "https://pypi.org/pypi".

        Returns:
            list[str]: A list of URLs corresponding to the wheel distributions (.whl) of
                the specified package and release versions compatible with the requirement.

        Raises:
            ValueError: If the provided requirement string cannot be parsed.
            RuntimeError: If fetching metadata from the index fails or if no matching
                wheel distributions are found for the requirement.
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
        wheel_urls: list[str] = []
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
        """Check if a version string matches a given requirement.

        The method determines whether the provided version string satisfies the
        specifier requirements defined by the given `Requirement`. If the version
        string cannot be parsed into a `Version` object or does not meet the
        requirements, the method will return False.

        Args:
            ver_str (str): The version string to validate.
            req (Requirement): The requirement containing the specifier to validate
                against.

        Returns:
            bool: True if the version string satisfies the requirement or has no
            specifier. False if the version string is invalid or does not satisfy
            the requirement.
        """
        try:
            ver = Version(ver_str)
        except InvalidVersion:
            return False
        return not req.specifier or req.specifier.contains(ver, prereleases=True)

    def resolve(self, dependency: str, output_dir: Path) -> list[Path]:
        """
        Resolves and downloads all wheel (.whl) variants for a given dependency into the specified
        output directory using pip. It compares the state of the output directory before and after
        the download to identify newly downloaded wheels.

        Args:
            dependency (str): The name of the dependency for which wheel variants are to be downloaded.
            output_dir (Path): The directory where the wheel files will be downloaded.

        Returns:
            list[Path]: A sorted list of Paths to the newly downloaded wheel files.

        Raises:
            RuntimeError: If the `pip download` command fails or no wheel files are downloaded.
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
