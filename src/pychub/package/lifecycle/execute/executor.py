from pathlib import Path

from pychub.model.build_event import audit, StageType
from pychub.package.lifecycle.execute.bundler import bundle_chub


@audit(StageType.EXECUTE)
def execute_build() -> Path:
    """
    Executes the build process and returns the path to the resulting bundle.

    The function is decorated with an audit check for the execution stage and is
    responsible for bundling the necessary resources or components. It returns the
    path to the bundle created during the build process.

    Returns:
        Path: The path to the bundled resource created during the build process.
    """
    return bundle_chub()
