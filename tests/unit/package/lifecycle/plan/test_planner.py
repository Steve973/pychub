
"""Unit tests for pychub.package.lifecycle.plan.planner module."""
from __future__ import annotations

from unittest.mock import patch

from pychub.package.context_vars import current_build_plan
from pychub.package.lifecycle.plan.planner import plan_build


def test_plan_build(tmp_path, mock_buildplan, mock_chubproject_factory):
    """Test that plan_build calls all resource staging functions and writes buildplan.json."""
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()
    
    chubproject = mock_chubproject_factory(
        name="test",
        version="1.0.0",
        wheels=["pkg1", "pkg2"],
        scripts={"pre": ["setup.sh"], "post": ["cleanup.sh"]},
        includes=["config.yaml"]
    )
    current_build_plan.set(mock_buildplan)
    mock_buildplan.project = chubproject
    strategies = []
    
    with patch("pychub.package.lifecycle.plan.planner.stage_wheels") as mock_stage:
        with patch("pychub.package.lifecycle.plan.planner.copy_pre_install_scripts") as mock_pre:
            with patch("pychub.package.lifecycle.plan.planner.copy_post_install_scripts") as mock_post:
                with patch("pychub.package.lifecycle.plan.planner.copy_included_files") as mock_inc:
                    with patch("pychub.package.lifecycle.plan.planner.copy_runtime_files") as mock_runtime:
                        result = plan_build(cache_dir, strategies)
    
    # Verify stage_wheels called correctly
    mock_stage.assert_called_once()
    args = mock_stage.call_args[0]
    assert isinstance(args[0], dict)
    assert args[1] == {"pkg1", "pkg2"}
    assert args[2] == strategies
    
    # Verify copy functions called with correct paths
    mock_pre.assert_called_once_with(cache_dir / "scripts" / "pre", ["setup.sh"])
    mock_post.assert_called_once_with(cache_dir / "scripts" / "post", ["cleanup.sh"])
    mock_inc.assert_called_once_with(cache_dir / "includes", ["config.yaml"])
    mock_runtime.assert_called_once_with(cache_dir / "runtime")
    
    # Verify buildplan.json created and returned
    assert result == cache_dir / "buildplan.json"
    assert result.exists()