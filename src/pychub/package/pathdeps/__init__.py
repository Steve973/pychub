from typing import List
from .base import PathDepStrategy
from .poetry import PoetryPathDepStrategy
from .hatch import HatchPathDepStrategy
from .pdm import PdmPathDepStrategy

def load_strategies() -> List[PathDepStrategy]:
    return [
        PoetryPathDepStrategy(),
        HatchPathDepStrategy(),
        PdmPathDepStrategy(),
    ]
