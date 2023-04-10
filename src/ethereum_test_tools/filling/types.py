"""
Base types used to specify fillers
"""
from abc import ABC, abstractmethod
from typing import Callable, List, Mapping, Optional

from ethereum_test_forks import Fork
from evm_block_builder import BlockBuilder
from evm_transition_tool import TransitionTool

from ..common import Fixture
from ..reference_spec.reference_spec import ReferenceSpec

FillerReturnType = Mapping[str, Fixture] | None
DecoratedFillerType = Callable[
    [TransitionTool, BlockBuilder, str, ReferenceSpec | None], FillerReturnType
]


class DecoratedFillerBase(ABC):
    """
    Decorated filler class that must provide all metadata about the
    filler, and also must contain filling logic.
    """

    name: str
    forks: List[Fork]
    eips: Optional[List[int]]
    module_path: Optional[List[str]]
    reference_spec: Optional[ReferenceSpec]

    @abstractmethod
    def fill(
        self,
        t8n: TransitionTool,
        b11r: BlockBuilder,
        engine: str,
    ) -> FillerReturnType:
        """
        Fill test logic.
        """
        pass
