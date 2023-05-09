"""
Test EIP-4844: Shard Blob Transactions (Excess Data Tests)
EIP: https://eips.ethereum.org/EIPS/eip-4844
"""
from typing import Dict, List, Optional

import pytest

from ethereum_test_forks import Cancun, Fork, Shanghai, fork_only, forks_from
from ethereum_test_tools import (
    Account,
    Block,
    BlockchainTestFiller,
    Environment,
    TestAddress,
    Transaction,
    to_address,
    to_hash_bytes,
)

REFERENCE_SPEC_GIT_PATH = "EIPS/eip-4844.md"
REFERENCE_SPEC_VERSION = "b33e063530f0a114635dd4f89d3cca90f8cac28f"

DATAHASH_GAS_COST = 3
MIN_DATA_GASPRICE = 1
DATA_GAS_PER_BLOB = 2**17
MAX_DATA_GAS_PER_BLOCK = 2**19
TARGET_DATA_GAS_PER_BLOCK = 2**18
MAX_BLOBS_PER_BLOCK = MAX_DATA_GAS_PER_BLOCK // DATA_GAS_PER_BLOB
TARGET_BLOBS_PER_BLOCK = TARGET_DATA_GAS_PER_BLOCK // DATA_GAS_PER_BLOB
DATA_GASPRICE_UPDATE_FRACTION = 2225652


def fake_exponential(factor: int, numerator: int, denominator: int) -> int:
    """
    Used to calculate the data gas cost.
    """
    i = 1
    output = 0
    numerator_accumulator = factor * denominator
    while numerator_accumulator > 0:
        output += numerator_accumulator
        numerator_accumulator = (numerator_accumulator * numerator) // (
            denominator * i
        )
        i += 1
    return output // denominator


def get_data_gasprice(excess_data_gas: int) -> int:
    """
    Calculate the data gas price from the excess.
    """
    return fake_exponential(
        MIN_DATA_GASPRICE,
        excess_data_gas,
        DATA_GASPRICE_UPDATE_FRACTION,
    )


@pytest.fixture
def destination_account() -> str:  # noqa: D103
    return to_address(0x100)


@pytest.fixture(autouse=True)
def tx_count() -> int:  # noqa: D103
    return 1


@pytest.fixture(autouse=True)
def blobs_per_tx() -> int:  # noqa: D103
    return 1


@pytest.fixture
def tx_value() -> int:  # noqa: D103
    return 1


@pytest.fixture
def tx_gas() -> int:  # noqa: D103
    return 21000


@pytest.fixture
def fee_per_gas() -> int:  # noqa: D103
    return 7


@pytest.fixture(autouse=True)
def parent_excess_blobs() -> Optional[int]:  # noqa: D103
    # Default to 10 blobs in the parent block, such that the data gas price is
    # 1.
    return 10


@pytest.fixture
def parent_excess_data_gas(  # noqa: D103
    parent_excess_blobs: Optional[int],
) -> Optional[int]:
    if parent_excess_blobs is None:
        return None
    return parent_excess_blobs * DATA_GAS_PER_BLOB


@pytest.fixture
def data_gasprice(  # noqa: D103
    parent_excess_data_gas: Optional[int],
) -> Optional[int]:
    if parent_excess_data_gas is None:
        return None
    return get_data_gasprice(excess_data_gas=parent_excess_data_gas)


@pytest.fixture
def tx_max_priority_fee_per_gas() -> int:  # noqa: D103
    return 0


@pytest.fixture
def tx_exact_cost(  # noqa: D103
    tx_gas: int,
    tx_value: int,
    fee_per_gas: int,
    tx_max_priority_fee_per_gas: int,
    blobs_per_tx: int,
    data_gasprice: Optional[int],
) -> int:
    if data_gasprice is None:
        data_gasprice = 1
    data_cost = data_gasprice * DATA_GAS_PER_BLOB * blobs_per_tx
    return (
        (tx_gas * (fee_per_gas + tx_max_priority_fee_per_gas))
        + tx_value
        + data_cost
    )


@pytest.fixture
def total_account_minimum_balance(  # noqa: D103
    tx_count: int,
    tx_exact_cost: int,
) -> int:
    return tx_count * tx_exact_cost


@pytest.fixture(autouse=True)
def max_fee_per_gas() -> Optional[int]:  # noqa: D103
    return None


@pytest.fixture(autouse=True)
def tx_max_data_gas_cost() -> Optional[int]:  # noqa: D103
    return None


@pytest.fixture
def max_fee_per_data_gas(  # noqa: D103
    data_gasprice: int,
    tx_max_data_gas_cost: Optional[int],
) -> int:
    return (
        tx_max_data_gas_cost
        if tx_max_data_gas_cost is not None
        else data_gasprice
    )


@pytest.fixture(autouse=True)
def txs(  # noqa: D103
    destination_account: str,
    tx_count: int,
    tx_gas: int,
    tx_value: int,
    fee_per_gas: int,
    max_fee_per_gas: Optional[int],
    max_fee_per_data_gas: int,
    tx_max_priority_fee_per_gas: int,
    blobs_per_tx: int,
    tx_error: str,
) -> List[Transaction]:
    if max_fee_per_gas is None:
        max_fee_per_gas = fee_per_gas
    return [
        Transaction(
            ty=3,
            nonce=tx_i,
            to=destination_account,
            value=tx_value,
            gas_limit=tx_gas,
            max_fee_per_gas=max_fee_per_gas,
            max_priority_fee_per_gas=tx_max_priority_fee_per_gas,
            max_fee_per_data_gas=max_fee_per_data_gas,
            access_list=[],
            blob_versioned_hashes=[
                to_hash_bytes(x) for x in range(blobs_per_tx)
            ],
            error=tx_error if tx_i == (tx_count - 1) else None,
        )
        for tx_i in range(tx_count)
    ]


@pytest.fixture
def account_balance_modifier() -> int:  # noqa: D103
    return 0


@pytest.fixture
def pre(  # noqa: D103
    total_account_minimum_balance: int,
    account_balance_modifier: int,
) -> Dict:
    return {
        TestAddress: Account(
            balance=total_account_minimum_balance + account_balance_modifier
        ),
    }


@pytest.fixture
def env(  # noqa: D103
    parent_excess_data_gas: Optional[int],
) -> Environment:
    return Environment(excess_data_gas=parent_excess_data_gas)


@pytest.fixture
def blocks(  # noqa: D103
    txs: List[Transaction],
    tx_error: str,
) -> List[Block]:
    return [
        Block(
            txs=txs,
            exception=tx_error,
        )
    ]


@pytest.mark.parametrize(
    "parent_excess_blobs,tx_max_data_gas_cost,tx_error",
    [
        # tx max_data_gas_cost of the transaction is not enough
        (
            12,  # data gas price is 2
            1,  # tx max_data_gas_cost is 1
            "insufficient max fee per data gas",
        ),
        # tx max_data_gas_cost of the transaction is zero, which is invalid
        (
            0,  # data gas price is 1
            0,  # tx max_data_gas_cost is 0
            "invalid max fee per data gas",
        ),
    ],
    ids=["insufficient_max_fee_per_data_gas", "invalid_max_fee_per_data_gas"],
)
@pytest.mark.parametrize("fork", forks_from(Cancun))
def test_invalid_tx_max_fee_per_data_gas(
    blockchain_test: BlockchainTestFiller,
    pre: Dict,
    env: Environment,
    blocks: List[Block],
    fork: Fork,
):
    """
    Reject blocks with invalid blob txs due to:
        -
        - tx max_fee_per_data_gas is not enough
        - tx max_fee_per_data_gas is zero
    """
    blockchain_test(
        pre=pre,
        post={},
        blocks=blocks,
        genesis_environment=env,
    )


@pytest.mark.parametrize(
    "max_fee_per_gas,tx_error",
    [
        # max data gas is ok, but max fee per gas is less than base fee per gas
        (
            6,
            "insufficient max fee per gas",
        ),
    ],
    ids=["insufficient_max_fee_per_gas"],
)
@pytest.mark.parametrize("fork", forks_from(Cancun))
def test_invalid_normal_gas(
    blockchain_test: BlockchainTestFiller,
    pre: Dict,
    env: Environment,
    blocks: List[Block],
    fork: Fork,
):
    """
    Reject blocks with invalid blob txs due to:
        -
        - tx max_fee_per_data_gas is not enough
        - tx max_fee_per_data_gas is zero
    """
    blockchain_test(
        pre=pre,
        post={},
        blocks=blocks,
        genesis_environment=env,
    )


@pytest.mark.parametrize(
    "tx_count,blobs_per_tx",
    [
        (MAX_BLOBS_PER_BLOCK + 1, 1),
        (1, MAX_BLOBS_PER_BLOCK + 1),
    ],
    ids=["too_many_blobs_in_block", "too_many_blobs_in_tx"],
)
@pytest.mark.parametrize("tx_error", ["invalid_blob_count"])
@pytest.mark.parametrize("fork", forks_from(Cancun))
def test_invalid_block_blob_count(
    blockchain_test: BlockchainTestFiller,
    pre: Dict,
    env: Environment,
    blocks: List[Block],
    fork: Fork,
):
    """
    Reject blocks where block blob count > MAX_BLOBS_PER_BLOCK, across all txs
    """
    blockchain_test(
        pre=pre,
        post={},
        blocks=blocks,
        genesis_environment=env,
    )


@pytest.mark.parametrize("tx_max_priority_fee_per_gas", [0, 8])
@pytest.mark.parametrize("tx_value", [0, 1])
@pytest.mark.parametrize("account_balance_modifier", [-1])
@pytest.mark.parametrize("tx_error", ["insufficient account balance"])
@pytest.mark.parametrize("fork", forks_from(Cancun))
def test_insufficient_balance_blob_tx(
    blockchain_test: BlockchainTestFiller,
    pre: Dict,
    env: Environment,
    blocks: List[Block],
    fork: Fork,
):
    """
    Reject blocks where user cannot afford the data gas specified (but
    max_fee_per_gas would be enough for current block)
    """
    blockchain_test(
        pre=pre,
        post={},
        blocks=blocks,
        genesis_environment=env,
    )


@pytest.mark.parametrize(
    "blobs_per_tx,tx_error",
    [(0, "zero_blob_tx"), (MAX_BLOBS_PER_BLOCK + 1, "too_many_blobs_tx")],
    ids=["too_few_blobs", "too_many_blobs"],
)
@pytest.mark.parametrize("fork", forks_from(Cancun))
def test_invalid_tx_blob_count(
    blockchain_test: BlockchainTestFiller,
    pre: Dict,
    env: Environment,
    blocks: List[Block],
    fork: Fork,
):
    """
    Reject blocks that include blob transactions with invalid blob counts:
    - blob count = 0 in type 3 transaction
    - blob count > MAX_BLOBS_PER_TX in type 3 transaction
    - blob count > MAX_BLOBS_PER_BLOCK in type 3 transaction
    """
    blockchain_test(
        pre=pre,
        post={},
        blocks=blocks,
        genesis_environment=env,
    )


@pytest.mark.parametrize("blobs_per_tx", [0, 1], ids=["no_blobs", "one_blob"])
@pytest.mark.parametrize("parent_excess_blobs", [None])
@pytest.mark.parametrize("tx_max_data_gas_cost", [1])
@pytest.mark.parametrize("tx_error", ["tx_type_3_not_allowed_yet"])
@pytest.mark.parametrize("fork", fork_only(Shanghai))
def test_blob_txs_pre_fork(
    blockchain_test: BlockchainTestFiller,
    pre: Dict,
    env: Environment,
    blocks: List[Block],
    fork: Fork,
):
    """
    Reject blocks with blobs before blobs fork
    """
    blockchain_test(
        pre=pre,
        post={},
        blocks=blocks,
        genesis_environment=env,
    )
