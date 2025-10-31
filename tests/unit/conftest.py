"""Fixtures for initializer unit tests."""
import json
from unittest.mock import Mock, MagicMock

import pytest

from pychub.model.buildplan_model import BuildPlan
from pychub.model.chubproject_model import ChubProject


@pytest.fixture
def mock_chubproject_class(mock_chubproject_factory):
    """Mock the ChubProject class with all its static/class methods."""
    mock_class = MagicMock()

    # Static factory methods - use the factory to create proper instances
    mock_class.from_mapping = MagicMock(side_effect=lambda m: mock_chubproject_factory(**m) if m else mock_chubproject_factory())
    mock_class.from_toml_document = MagicMock(side_effect=lambda *args, **kwargs: mock_chubproject_factory())
    mock_class.from_cli_args = MagicMock(side_effect=lambda *args, **kwargs: mock_chubproject_factory())

    # Static merge methods
    mock_class.merge_from_cli_args = MagicMock(side_effect=lambda existing, args: mock_chubproject_factory())
    mock_class.override_from_cli_args = MagicMock(side_effect=lambda existing, args: mock_chubproject_factory())

    # Static helper methods
    mock_class._select_package_table = MagicMock(return_value={})
    mock_class.determine_table_path = MagicMock(return_value="tool.pychub.package")
    mock_class._comma_split_maybe = MagicMock(return_value=[])
    mock_class._flatten = MagicMock(return_value=[])
    mock_class._dedup = MagicMock(return_value=[])
    mock_class._dedup_includes = MagicMock(return_value=[])

    # File I/O methods
    mock_class.load_file = MagicMock(side_effect=lambda path: mock_chubproject_factory())
    mock_class.save_file = MagicMock(return_value="valid_chubproject.toml")

    return mock_class


@pytest.fixture
def mock_chubproject_factory():
    """Factory that creates mock ChubProject instances with customizable params.

    Usage:
        def test_something(mock_chubproject_factory):
            proj = mock_chubproject_factory(name="custom", version="2.0.0")
            assert proj.name == "custom"
    """

    def _make_mock(
            name="test-project",
            version="1.0.0",
            project_path=None,
            wheels=None,
            chub=None,
            entrypoint="test:main",
            entrypoint_args=None,
            includes=None,
            include_chubs=None,
            verbose=False,
            metadata=None,
            scripts=None):
        mock = MagicMock()
        mock.__class__ = ChubProject
        mock.name = name
        mock.version = version
        mock.project_path = project_path
        mock.wheels = wheels if wheels is not None else []
        mock.chub = chub
        mock.entrypoint = entrypoint
        mock.entrypoint_args = entrypoint_args if entrypoint_args is not None else []
        mock.includes = includes if includes is not None else []
        mock.include_chubs = include_chubs if include_chubs is not None else []
        mock.verbose = verbose
        mock.metadata = metadata if metadata is not None else {}

        # Handle scripts - can be a Mock or dict
        if scripts is None:
            mock.scripts = MagicMock(pre=[], post=[])
        elif isinstance(scripts, dict):
            mock.scripts = MagicMock(pre=scripts.get("pre", []), post=scripts.get("post", []))
        else:
            mock.scripts = scripts

        mapping = {
            "name": name,
            "version": version,
            "project_path": project_path,
            "wheels": mock.wheels,
            "chub": chub,
            "entrypoint": entrypoint,
            "entrypoint_args": mock.entrypoint_args,
            "includes": mock.includes,
            "include_chubs": mock.include_chubs,
            "verbose": verbose,
            "metadata": mock.metadata,
            "scripts": {"pre": mock.scripts.pre, "post": mock.scripts.post}
        }
        mock.to_mapping.return_value = mapping

        mock.from_mapping.return_value = mock

        # to_json should serialize the full mapping
        mock.to_json.return_value = json.dumps(mapping, sort_keys=True, ensure_ascii=False, indent=2)

        mock.get_wheel_name_version.return_value = (name, version)

        mock.save_file.return_value = None

        return mock

    return _make_mock


@pytest.fixture
def mock_buildplan():
    """Create a mock BuildPlan."""
    mock = Mock()
    mock.__class__ = BuildPlan
    mock.project = None
    mock.project_hash = ""
    mock.staging_dir = None
    mock.wheels_dir = "wheels"
    mock.audit_log = []
    mapping = {
        "project": mock.project,
        "project_hash": mock.project_hash,
        "staging_dir": mock.staging_dir,
        "wheels_dir": mock.wheels_dir,
        "audit_log": mock.audit_log
    }
    mock.to_mapping.return_value = mapping
    mock.to_json.return_value = json.dumps(mapping, sort_keys=True, ensure_ascii=False, indent=2)
    return mock


@pytest.fixture
def mock_chubproject():
    """Create a mock ChubProject that doesn't do validation or I/O."""
    mock = Mock()
    mock.__class__ = ChubProject
    mock.name = "test-project"
    mock.version = "1.0.0"
    mock.entrypoint = "test:main"
    mock.wheels = []
    mock.includes = []
    mock.scripts = Mock(pre=[], post=[])
    mock.metadata = {}
    mock.to_json.return_value = '{"name": "test-project", "version": "1.0.0"}'
    mock.to_mapping.return_value = {"name": "test-project", "version": "1.0.0"}
    return mock


@pytest.fixture
def fake_dist_wheels(monkeypatch, tmp_path):
    # Make two fake wheel paths
    dist = tmp_path / "dist"
    dist.mkdir()
    files = [
        dist / "extra-0.0.0-py3-none-any.whl",
        dist / "pychub-1.0.0-py3-none-any.whl",
        dist / "pkg-1.0.0-py3-none-any.whl",
    ]
    for f in files:
        f.touch()

    # Only patch the chubproject_model module's use of glob
    def _fake_glob(pattern: str):
        # your code uses glob.glob(os.path.join(cwd, "dist", "*.whl"))
        if pattern.endswith("dist/*.whl"):
            return [str(p) for p in sorted(files)]
        return []

    # monkeypatch.setattr(
    #     "pychub.model.chubproject_model.glob.glob",
    #     _fake_glob,
    #     raising=True)