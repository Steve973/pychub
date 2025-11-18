from __future__ import annotations

import sys
import zipfile
from pathlib import Path

import pytest
from appdirs import user_cache_dir

from pychub.model.buildplan_model import BuildPlan
from pychub.package.context_vars import current_build_plan
from pychub.package.lifecycle.plan.dep_resolution.wheeldeps.local_resolution_strategy import LocalResolutionStrategy
from tests.integration.utils.build_helpers import build_test_wheel


def _assert_chub_valid(chub_path: Path) -> None:
    """Quick structural sanity check for produced .chub archive."""
    assert chub_path.is_file(), f"Missing chub: {chub_path}"
    with zipfile.ZipFile(chub_path) as zf:
        names = set(zf.namelist())
        for must in (".chubconfig", "__main__.py", "runtime/", "libs/"):
            assert any(n == must or n.startswith(must) for n in names), (
                f"Archive missing '{must}'"
            )
        text = zf.read(".chubconfig").decode("utf-8", "replace")
        assert "name:" in text and "version:" in text, "bad chubconfig"
        assert "targets:" in text, "no compatibility section"


@pytest.fixture(scope="session")
def built_wheel(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Build test_proj wheel once per session and cache the path."""
    proj_dir = Path(__file__).parents[3] / "test_proj"
    wheel = build_test_wheel(proj_dir)
    # copy into temp to avoid polluting repo dist
    tmp = tmp_path_factory.mktemp("wheel")
    target = tmp / wheel.name
    target.write_bytes(wheel.read_bytes())
    return target


def test_build_chub_via_project(tmp_path: Path, built_wheel: Path):
    """Direct internal path: ChubProject → build_chub()."""
    from pychub.model.chubproject_model import ChubProject

    out = tmp_path / "out" / "project-built.chub"
    cli_args = {
        "wheel": [str(built_wheel)],
        "chub": str(out),
        "verbose": True,
        "project_path": str(tmp_path),
    }
    project = ChubProject.from_cli_args(cli_args)
    chub_path = build_chub(project)
    _assert_chub_valid(chub_path)


def test_build_chub_via_cli_process_options(tmp_path: Path, built_wheel: Path, monkeypatch):
    """User-facing path: create_arg_parser() → process_options()."""
    from pychub.package.main import main

    out = tmp_path / "cli" / "cli-built.chub"
    argv = [
        "pychub",
        "--wheel", str(built_wheel),
        "--chub", str(out),
        "--project-path", str(tmp_path),
        "--verbose",
    ]
    monkeypatch.setattr(sys, "argv", argv)

    main()
    _assert_chub_valid(out)


def test_parse_cli_to_chubproject(tmp_path, built_wheel, monkeypatch):
    from pychub.package.lifecycle.init.initializer import parse_cli
    from pychub.package.lifecycle.init.initializer import process_options

    out = tmp_path / "cli" / "cli-built.chub"
    argv = [
        "pychub",
        "--wheel", str(built_wheel),
        "--chub", str(out),
        "--project-path", str(tmp_path),
        "--verbose",
    ]
    monkeypatch.setattr(sys, "argv", argv)
    plan = BuildPlan()
    current_build_plan.set(plan)

    args, other_args = parse_cli()
    chubproject = process_options(args, other_args)

    assert args.wheel == [str(built_wheel)]
    assert str(args.chub) == str(out)
    assert args.project_path == str(tmp_path)
    assert args.verbose == True
    assert chubproject.wheels == [str(built_wheel)]
    assert chubproject.chub == str(out)
    assert chubproject.project_path == str(tmp_path)
    assert chubproject.verbose == True


def test_init_project_from_cli(tmp_path, built_wheel, monkeypatch):
    from pychub.package.lifecycle.init.initializer import init_project

    out = tmp_path / "cli" / "cli-built.chub"
    argv = [
        "pychub",
        "--wheel", str(built_wheel),
        "--chub", str(out),
        "--project-path", str(tmp_path),
        "--verbose",
    ]
    monkeypatch.setattr(sys, "argv", argv)
    plan = BuildPlan()
    current_build_plan.set(plan)

    project_cache_path, must_exit = init_project()

    assert str(project_cache_path) == f"{user_cache_dir("pychub")}/{plan.project_hash}"
    assert must_exit == False


def test_build_chub_via_cli_init_project(tmp_path, built_wheel, monkeypatch):
    from pychub.package.lifecycle.init.initializer import init_project
    from pychub.package.lifecycle.plan.planner import plan_build
    from pychub.package.lifecycle.execute.executor import execute_build

    out = tmp_path / "cli" / "cli-built.chub"
    argv = [
        "pychub",
        "--wheel", str(built_wheel),
        "--chub", str(out),
        "--project-path", str(tmp_path),
        "--verbose",
    ]
    monkeypatch.setattr(sys, "argv", argv)
    plan = BuildPlan()
    current_build_plan.set(plan)

    cache_path, must_exit = init_project()
    plan_build(cache_path, [LocalResolutionStrategy()])
    chub_file_path = execute_build()

    assert chub_file_path == out
