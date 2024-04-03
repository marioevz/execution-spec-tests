"""
abstract: Test [EIP-3860: Limit and meter initcode](https://eips.ethereum.org/EIPS/eip-3860)
    Tests for  [EIP-3860: Limit and meter initcode](https://eips.ethereum.org/EIPS/eip-3860).

note: Tests ported from:
    - [ethereum/tests/pull/990](https://github.com/ethereum/tests/pull/990)
    - [ethereum/tests/pull/1012](https://github.com/ethereum/tests/pull/990)
"""

from typing import List, Mapping

import pytest

from ethereum_test_forks import Paris, Shanghai
from ethereum_test_tools import (
    Account,
    Environment,
    StateTestFiller,
    TestAddress,
    Transaction,
    ceiling_division,
    eip_2028_transaction_data_cost,
)
from ethereum_test_tools.vm import Opcodes as Op

REFERENCE_SPEC_GIT_PATH = "EIPS/eip-7623.md"
REFERENCE_SPEC_VERSION = "a285272475ae032ddcf97b9141414a0e4f3e9157"

ENABLE_FORK = Shanghai  # TODO: update
FORK_BEFORE = Paris
pytestmark = pytest.mark.valid_from(str(FORK_BEFORE))

"""
General constants used for testing purposes
"""

STANDARD_TOKEN_COST = 4
TOTAL_COST_FLOOR_PER_TOKEN = 17
MAX_INITCODE_SIZE = 49152
INITCODE_WORD_COST = 2
BASE_TRANSACTION_GAS = 21000
CREATE_CONTRACT_BASE_GAS = 32000
G_VERY_LOW = 3
G_HIGH = 10
G_JUMPDEST = 1

CALLEE_CONTRACT_ADDRESS = 0x100

"""
Helper functions
"""


def calculate_initcode_word_cost(calldata: bytes) -> int:
    """
    Calculates the added word cost on contract creation added by the
    length of the initcode based on the formula:
    INITCODE_WORD_COST * ceil(len(initcode) / 32)
    """
    return INITCODE_WORD_COST * ceiling_division(len(calldata), 32)


def tokens_in_calldata(calldata: bytes) -> int:  # noqa: D103
    non_zero_byte_length = len([byte for byte in calldata if byte != 0])
    return non_zero_byte_length * 4 + (len(calldata) - non_zero_byte_length)


def calculate_tx_gas_used(is_contract_creation: bool, calldata: bytes, evm_gas_used: int) -> int:
    """
    Calculates the gas used by a transaction before the EIP-7623
    """
    return (
        STANDARD_TOKEN_COST * tokens_in_calldata(calldata)
        + evm_gas_used
        + (is_contract_creation * (32000 + calculate_initcode_word_cost(calldata)))
    )


def calculate_total_floor_cost(calldata: bytes) -> int:
    """
    Calculates the total cost floor for a transaction before the EIP-7623
    """
    return TOTAL_COST_FLOOR_PER_TOKEN * tokens_in_calldata(calldata)


def calculate_tx_gas_used_eip_7623(
    is_contract_creation: bool, calldata: bytes, evm_gas_used: int
) -> int:
    """
    Calculates the gas used by a transaction after the EIP-7623
    """
    return max(
        calculate_tx_gas_used(is_contract_creation, calldata, evm_gas_used),
        calculate_total_floor_cost(calldata),
    )


def calculate_create_tx_intrinsic_cost(initcode: Initcode, eip_3860_active: bool) -> int:
    """
    Calculates the intrinsic gas cost of a transaction that contains initcode
    and creates a contract
    """
    cost = (
        BASE_TRANSACTION_GAS  # G_transaction
        + CREATE_CONTRACT_BASE_GAS  # G_transaction_create
        + eip_2028_transaction_data_cost(initcode)  # Transaction calldata cost
    )
    if eip_3860_active:
        cost += calculate_initcode_word_cost(len(initcode))
    return cost


"""
Fixtures
"""


@pytest.fixture
def eips() -> List[int]:  # noqa: D103
    return []  # [7623]


@pytest.fixture
def zero_byte_length() -> int:  # noqa: D103
    return 0


@pytest.fixture
def non_zero_byte_length() -> int:  # noqa: D103
    return 0


@pytest.fixture
def non_zero_byte() -> bytes:  # noqa: D103
    return b"\x01"


@pytest.fixture
def calldata(  # noqa: D103
    zero_byte_length: int,
    non_zero_byte: bytes,
    non_zero_byte_length: int,
) -> bytes:
    return b"\x00" * zero_byte_length + non_zero_byte * non_zero_byte_length


@pytest.fixture
def initcode() -> bytes:
    """
    By default, no contract is created therefore the initcode is empty.
    """
    return b""


@pytest.fixture
def tx_gas_limit() -> int:  # noqa: D103
    return 1_000_000


@pytest.fixture
def tx(calldata: bytes, initcode: bytes, tx_gas_limit: int) -> Transaction:  # noqa: D103
    return Transaction(
        to=None if (len(initcode) > 0) else CALLEE_CONTRACT_ADDRESS,
        data=calldata,
        gas_limit=tx_gas_limit,
    )


@pytest.fixture
def callee_code(evm_gas_used: int) -> bytes:  # noqa: D103
    """
    Attempt to produce a code that will use the given amount of gas.
    """

    gas_per_loop = (
        G_HIGH  # JUMPI
        + G_VERY_LOW  # PUSH(PC)
        + G_VERY_LOW * 2  # NOT(ISZERO)
        + G_VERY_LOW * 3  # SUB(SWAP, 1)
        + G_JUMPDEST
    )
    minimum_loop_gas = G_VERY_LOW + gas_per_loop
    if evm_gas_used < minimum_loop_gas:
        return b"\x01" * evm_gas_used
    loops = (evm_gas_used - G_VERY_LOW) // gas_per_loop
    remainder = (evm_gas_used - G_VERY_LOW) % gas_per_loop
    loop_code = (
        Op.PUSH32(loops)  # G_VERY_LOW
        + Op.JUMPDEST  # G_JUMPDEST
        + Op.JUMPI(len(Op.PUSH32(loops)), Op.NOT(Op.ISZERO(Op.SUB(Op.SWAP1, 1))))  # G_HIGH
    )
    return loop_code + Op.JUMPDEST * remainder + Op.STOP


@pytest.fixture
def pre(callee_code: bytes) -> Mapping:  # noqa: D103
    return {
        TestAddress: Account(balance=10**40),
        CALLEE_CONTRACT_ADDRESS: Account(code=callee_code),
    }


@pytest.fixture
def post() -> Mapping:  # noqa: D103
    return {}


@pytest.mark.parametrize(
    "calldata",
    [
        pytest.param(b""),
        pytest.param(b"\x00"),
    ],
)
def test_calldata_cost(
    state_test: StateTestFiller,
    pre: Mapping[str, Account],
    post: Mapping[str, Account],
    tx: Transaction,
) -> None:
    """
    Test the calldata cost increase.
    """
    state_test(
        env=Environment(),
        pre=pre,
        post=post,
        tx=tx,
    )


def calculate_min_calldata_length_to_reach_total_floor_cost(
    is_contract_creation: bool,
    evm_gas_used: int,
    fill_byte: bytes,
) -> int:
    """
    Calculates the minimum calldata length to reach the total cost floor, taking into account the
    EVM gas used, and whether the transaction is a contract creation.
    """
    calldata = b""
    while calculate_total_floor_cost(calldata) < calculate_tx_gas_used(
        is_contract_creation, calldata, evm_gas_used
    ):
        calldata += fill_byte
    return len(calldata)


def print_calculate_min_calldata_length_to_reach_total_floor_cost(
    is_contract_creation: bool,
    evm_gas_used: int,
    fill_byte: bytes,
) -> int:
    """
    Calculates the minimum calldata length to reach the total cost floor, taking into account the
    EVM gas used, and whether the transaction is a contract creation.

    Prints a description too.
    """
    min_calldata_length = calculate_min_calldata_length_to_reach_total_floor_cost(
        is_contract_creation, evm_gas_used, fill_byte
    )
    calldata = fill_byte * min_calldata_length
    print(
        f"""
        --- Conditions
        is_contract_creation: {is_contract_creation}
        evm_gas_used: {evm_gas_used}
        fill_byte: 0x{fill_byte.hex()}
        --- Result
        Minimum calldata length: {len(calldata)}
        floor cost: {calculate_total_floor_cost(calldata)}
        gas used: {calculate_tx_gas_used(is_contract_creation, calldata, evm_gas_used)}
        """
    )
    return min_calldata_length


def main():
    """
    Perform some calculations to determine the minimum calldata length to reach the total cost floor.
    """
    # Assuming evm_gas_used is 0, calldata filled with zero bytes, calculate the minimum calldata
    # length to reach the total cost floor.
    print_calculate_min_calldata_length_to_reach_total_floor_cost(
        is_contract_creation=True,
        evm_gas_used=0,
        fill_byte=b"\x00",
    )
    print_calculate_min_calldata_length_to_reach_total_floor_cost(
        is_contract_creation=True,
        evm_gas_used=100,
        fill_byte=b"\x00",
    )
    print_calculate_min_calldata_length_to_reach_total_floor_cost(
        is_contract_creation=False,
        evm_gas_used=0,
        fill_byte=b"\x00",
    )
    print_calculate_min_calldata_length_to_reach_total_floor_cost(
        is_contract_creation=False,
        evm_gas_used=100,
        fill_byte=b"\x00",
    )
    print_calculate_min_calldata_length_to_reach_total_floor_cost(
        is_contract_creation=False,
        evm_gas_used=104,
        fill_byte=b"\x00",
    )
    # Assuming evm_gas_used is 0, calldata filled with non-zero bytes, calculate the minimum
    # calldata length to reach the total cost floor.
    print_calculate_min_calldata_length_to_reach_total_floor_cost(
        is_contract_creation=True,
        evm_gas_used=0,
        fill_byte=b"\x01",
    )
    print_calculate_min_calldata_length_to_reach_total_floor_cost(
        is_contract_creation=True,
        evm_gas_used=100,
        fill_byte=b"\x01",
    )
    print_calculate_min_calldata_length_to_reach_total_floor_cost(
        is_contract_creation=False,
        evm_gas_used=0,
        fill_byte=b"\x01",
    )
    print_calculate_min_calldata_length_to_reach_total_floor_cost(
        is_contract_creation=False,
        evm_gas_used=100,
        fill_byte=b"\x01",
    )


if __name__ == "__main__":
    main()
