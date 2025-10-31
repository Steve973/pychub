from pathlib import Path

from pychub.model.build_event import audit
from pychub.model.buildplan_model import BuildPlan
from pychub.package.lifecycle.execute.bundler import bundle_chub


@audit("EXECUTE")
def execute_build(build_plan: BuildPlan) -> Path:
    return bundle_chub(plan=build_plan)
