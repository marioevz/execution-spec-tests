"""
List of all transition fork definitions.
"""

from ..transition_base_fork import TransitionFork
from .forks import Cancun, London, Shanghai


# Transition Forks
class BerlinToLondonAt5(
    TransitionFork,
    London,
    at_block=5,
):
    """
    Berlin to London transition at Block 5
    """

    pass


class ParisToShanghaiAtTime15k(
    TransitionFork,
    Shanghai,
    at_timestamp=15_000,
    blockchain_test_network_name="ParisToShanghaiAtTime15k",
):
    """
    Paris to Shanghai transition at Timestamp 15k
    """

    pass


class ShanghaiToCancunAtTime15k(
    TransitionFork,
    Cancun,
    at_timestamp=15_000,
):
    """
    Shanghai to Cancun transition at Timestamp 15k
    """

    pass
