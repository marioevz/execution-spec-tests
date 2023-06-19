"""
Test EIP-4844: Shard Blob Transactions (Excess Data Tests at Transition)
EIP: https://eips.ethereum.org/EIPS/eip-4844
"""
from typing import List, Mapping

import pytest

from ethereum_test_tools import (
    Account,
    Block,
    BlockchainTestFiller,
    Environment,
    Header,
    TestAddress,
    Transaction,
    add_kzg_version,
    to_address,
    to_hash_bytes,
)

from .utils import (
    BLOB_COMMITMENT_VERSION_KZG,
    MAX_BLOBS_PER_BLOCK,
    TARGET_BLOBS_PER_BLOCK,
    get_min_excess_data_blobs_for_data_gas_price,
)

REFERENCE_SPEC_GIT_PATH = "EIPS/eip-4844.md"
REFERENCE_SPEC_VERSION = "ac003985b9be74ff48bd897770e6d5f2e4318715"

# All tests run on the transition fork from Shanghai to Cancun
pytestmark = pytest.mark.valid_at_transition_to("Cancun")


# Timestamp of the fork
FORK_TIMESTAMP = 15_000


@pytest.fixture
def env() -> Environment:  # noqa: D103
    return Environment()


@pytest.fixture
def pre() -> Mapping[str, Account]:  # noqa: D103
    return {
        TestAddress: Account(balance=10**40),
    }


@pytest.fixture
def pre_fork_blocks():
    """
    Generates blocks to reach the fork.
    """
    return [Block(timestamp=t) for t in range(999, FORK_TIMESTAMP, 1_000)]


@pytest.fixture
def post_fork_block_count() -> int:
    """
    Amount of blocks to produce with the post-fork rules.
    """
    return get_min_excess_data_blobs_for_data_gas_price(2) // (
        MAX_BLOBS_PER_BLOCK - TARGET_BLOBS_PER_BLOCK
    )


@pytest.fixture
def blob_count_per_block() -> int:
    """
    Amount of blocks to produce with the post-fork rules.
    """
    return 4


@pytest.fixture
def destination_account() -> str:  # noqa: D103
    return to_address(0x100)


@pytest.fixture
def post_fork_blocks(
    destination_account: str,
    post_fork_block_count: int,
    blob_count_per_block: int,
):
    """
    Generates blocks past the fork.
    """
    return [
        Block(
            txs=[
                Transaction(
                    ty=3,
                    nonce=b,
                    to=destination_account,
                    value=1,
                    gas_limit=3000000,
                    max_fee_per_gas=1000000,
                    max_priority_fee_per_gas=10,
                    max_fee_per_data_gas=100,
                    access_list=[],
                    blob_versioned_hashes=add_kzg_version(
                        [to_hash_bytes(x) for x in range(blob_count_per_block)],
                        BLOB_COMMITMENT_VERSION_KZG,
                    ),
                )
                if blob_count_per_block > 0
                else Transaction(
                    ty=2,
                    nonce=b,
                    to=destination_account,
                    value=1,
                    gas_limit=3000000,
                    max_fee_per_gas=1000000,
                    max_priority_fee_per_gas=10,
                    access_list=[],
                )
            ],
        )
        for b in range(post_fork_block_count)
    ]


@pytest.fixture
def post(  # noqa: D103
    post_fork_block_count: int,
    destination_account: str,
) -> Mapping[str, Account]:
    return {
        destination_account: Account(balance=post_fork_block_count),
    }


def test_invalid_pre_fork_block_with_excess_data_gas(
    blockchain_test: BlockchainTestFiller,
    env: Environment,
    pre: Mapping[str, Account],
    pre_fork_blocks: List[Block],
):
    """
    Test block rejection when excess_data_gas field is present on a pre-fork
    block.
    """
    # Try to append a block on the previous fork with excess data gas field set
    blockchain_test(
        pre=pre,
        post={},
        blocks=pre_fork_blocks[:-1]
        + [
            Block(
                timestamp=(FORK_TIMESTAMP - 1),
                rlp_modifier=Header(excess_data_gas=0),
                exception="invalid ExcessDataGas",
            )
        ],
        genesis_environment=env,
        tag="invalid_pre_fork_excess_data_gas",
    )


def test_invalid_post_fork_block_without_excess_data_gas(
    blockchain_test: BlockchainTestFiller,
    env: Environment,
    pre: Mapping[str, Account],
    pre_fork_blocks: List[Block],
):
    """
    Test block rejection when excess_data_gas field is missing on a post-fork
    block.
    """
    # Try to append a post-fork block with excess data gas field removed
    blockchain_test(
        pre=pre,
        post={},
        blocks=pre_fork_blocks
        + [
            Block(
                timestamp=FORK_TIMESTAMP,
                rlp_modifier=Header(excess_data_gas=Header.REMOVE_FIELD),
                exception="missing ExcessDataGas",
            )
        ],
        genesis_environment=env,
        tag="excess_data_gas_missing_post_fork",
    )


@pytest.mark.parametrize(
    "post_fork_block_count,blob_count_per_block",
    [
        (
            get_min_excess_data_blobs_for_data_gas_price(2)
            // (MAX_BLOBS_PER_BLOCK - TARGET_BLOBS_PER_BLOCK)
            + 2,
            MAX_BLOBS_PER_BLOCK,
        ),
        (10, 0),
        (10, TARGET_BLOBS_PER_BLOCK),
    ],
    ids=["max_blobs", "no_blobs", "target_blobs"],
)
def test_fork_transition_excess_data_gas(
    blockchain_test: BlockchainTestFiller,
    env: Environment,
    pre: Mapping[str, Account],
    pre_fork_blocks: List[Block],
    post_fork_blocks: List[Block],
    post: Mapping[str, Account],
):
    """
    Test excess_data_gas calculation in the header when the fork is activated.
    """
    blockchain_test(
        pre=pre,
        post=post,
        blocks=pre_fork_blocks + post_fork_blocks,
        genesis_environment=env,
        tag="correct_initial_data_gas_calc",
    )