"""
Base objects used to define transition forks.
"""

from inspect import signature
from typing import Callable, ClassVar, List

from .base_fork import BaseFork, Fork

ALWAYS_TRANSITIONED_BLOCK_NUMBER = 10_000
ALWAYS_TRANSITIONED_BLOCK_TIMESTAMP = 10_000_000


def base_fork_abstract_methods() -> List[str]:
    """
    Returns a list of all abstract methods that must be implemented by a fork.
    """
    return list(getattr(BaseFork, "__abstractmethods__"))


class TransitionFork(BaseFork):
    """
    Base class for transition forks.
    """

    _transitions_from: ClassVar[Fork]
    _transitions_to: ClassVar[Fork]
    _at_block: ClassVar[int]
    _at_timestamp: ClassVar[int]

    def __init_subclass__(
        cls,
        *,
        at_block: int = 0,
        at_timestamp: int = 0,
        **kwargs,
    ) -> None:
        """
        Initializes transition fork with the appropriate methods.
        """
        super().__init_subclass__(**kwargs)
        # TODO: This depends on the order in which the subclass inherits the base classes, which
        # is not ideal.
        to_fork = cls.__bases__[1]
        from_fork = to_fork.__bases__[0]

        cls._transitions_from = from_fork
        cls._transitions_to = to_fork
        cls._at_block = at_block
        cls._at_timestamp = at_timestamp

        def make_transition_method(
            base_method: Callable,
            from_fork_method: Callable,
            to_fork_method: Callable,
        ):
            base_method_parameters = signature(base_method).parameters

            def transition_method(
                cls,
                block_number: int = ALWAYS_TRANSITIONED_BLOCK_NUMBER,
                timestamp: int = ALWAYS_TRANSITIONED_BLOCK_TIMESTAMP,
            ):
                kwargs = {}
                if "block_number" in base_method_parameters:
                    kwargs["block_number"] = block_number
                if "timestamp" in base_method_parameters:
                    kwargs["timestamp"] = timestamp

                if getattr(base_method, "__prefer_transition_to_method__", False):
                    return to_fork_method(**kwargs)
                return (
                    to_fork_method(**kwargs)
                    if block_number >= at_block and timestamp >= at_timestamp
                    else from_fork_method(**kwargs)
                )

            return classmethod(transition_method)

        for method_name in base_fork_abstract_methods():
            setattr(
                cls,
                method_name,
                make_transition_method(
                    getattr(BaseFork, method_name),
                    getattr(from_fork, method_name),
                    getattr(to_fork, method_name),
                ),
            )

    @classmethod
    def transitions_to(cls) -> Fork:
        """
        Returns the fork where the transition ends.
        """
        return cls._transitions_to

    @classmethod
    def transitions_from(cls) -> Fork:
        """
        Returns the fork where the transition starts.
        """
        return cls._transitions_from

    @classmethod
    def fork_at(cls, block_number: int = 0, timestamp: int = 0) -> Fork:
        """
        Returns the fork where the transition starts.
        """
        return (
            cls._transitions_to
            if block_number >= cls._at_block and timestamp >= cls._at_timestamp
            else cls._transitions_from
        )
