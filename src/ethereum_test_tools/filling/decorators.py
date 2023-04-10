"""
Decorators for expanding filler definitions.
"""
from dataclasses import dataclass
from typing import Callable, List, Optional

from ethereum_test_forks import Fork, fork_only, forks_from, forks_from_until
from evm_block_builder import BlockBuilder
from evm_transition_tool import TransitionTool

from ..reference_spec.reference_spec import ReferenceSpec
from ..spec import TestSpec
from .fill import fill_test
from .types import DecoratedFillerBase, FillerReturnType

TESTS_PREFIX = "test_"
TESTS_PREFIX_LEN = len(TESTS_PREFIX)


@dataclass(kw_only=True)
class _DecoratedFiller(DecoratedFillerBase):
    """
    Decorated filler class implementation that is used by all decorators
    to return a fillable test.
    """

    name: str
    forks: List[Fork]
    test_spec: TestSpec
    eips: Optional[List[int]] = None
    module_path: Optional[List[str]] = None
    reference_spec: Optional[ReferenceSpec] = None

    def fill(
        self,
        t8n: TransitionTool,
        b11r: BlockBuilder,
        engine: str,
    ) -> FillerReturnType:
        """
        Fill test logic.
        """
        if not self.forks:
            return None
        return fill_test(
            self.name,
            t8n,
            b11r,
            self.test_spec,
            self.forks,
            engine,
            self.reference_spec,
            eips=self.eips,
        )


def _filler_decorator(
    forks: List[Fork], eips: Optional[List[int]] = None
) -> Callable[[TestSpec], DecoratedFillerBase]:
    """
    Decorator that takes a test generator and fills it for all specified forks.
    """

    def decorator(
        fn: TestSpec,
    ) -> DecoratedFillerBase:
        name = fn.__name__
        assert name.startswith(TESTS_PREFIX)

        return _DecoratedFiller(
            name=name[TESTS_PREFIX_LEN:],
            forks=forks,
            test_spec=fn,
            eips=eips,
        )

    return decorator


def test_from_until(
    fork_from: Fork,
    fork_until: Fork,
    eips: Optional[List[int]] = None,
) -> Callable[[TestSpec], DecoratedFillerBase]:
    """
    Decorator that takes a test generator and fills it for all forks after the
    specified fork.
    """
    return _filler_decorator(
        forks=forks_from_until(fork_from, fork_until), eips=eips
    )


def test_from(
    fork: Fork,
    eips: Optional[List[int]] = None,
) -> Callable[[TestSpec], DecoratedFillerBase]:
    """
    Decorator that takes a test generator and fills it for all forks after the
    specified fork.
    """
    return _filler_decorator(forks=forks_from(fork), eips=eips)


def test_only(
    fork: Fork,
    eips: Optional[List[int]] = None,
) -> Callable[[TestSpec], DecoratedFillerBase]:
    """
    Decorator that takes a test generator and fills it only for the specified
    fork.
    """
    return _filler_decorator(forks=fork_only(fork), eips=eips)
