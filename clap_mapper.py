from typing import Callable

import numpy as np

from simfile_parsing.rows import GlobalTimedRow


class BaseClapMapper(Callable):
    @classmethod
    def __call__(cls, row: GlobalTimedRow) -> np.ndarray:
        return NotImplemented
