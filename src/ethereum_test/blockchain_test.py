"""
Blockchain test filler.
"""

import json
import tempfile
from dataclasses import dataclass
from typing import Any, Callable, Generator, List, Mapping, Tuple

from ethereum_test.fork import is_london
from evm_block_builder import BlockBuilder
from evm_transition_tool import TransitionTool

from .base_test import BaseTest, verify_post_alloc, verify_transactions
from .common import EmptyTrieRoot
from .types import (
    Account,
    Block,
    Environment,
    FixtureBlock,
    FixtureHeader,
    JSONEncoder,
)

default_base_fee = 1
"""
Default base_fee used in the genesis and block 1 for the BlockchainTests.
"""


@dataclass(kw_only=True)
class BlockchainTest(BaseTest):
    """
    Filler type that tests multiple blocks (valid or invalid) in a chain.
    """

    pre: Mapping[str, Account]
    post: Mapping[str, Account]
    blocks: List[Block]
    genesis_environment: Environment = Environment()

    def make_genesis(
        self,
        b11r: BlockBuilder,
        t8n: TransitionTool,
        fork: str,
    ) -> FixtureHeader:
        """
        Create a genesis block from the state test definition.
        """
        base_fee = self.genesis_environment.base_fee
        if is_london(fork) and base_fee is None:
            base_fee = default_base_fee
        elif not is_london(fork) and base_fee is not None:
            base_fee = None
        genesis = FixtureHeader(
            parent_hash="0x0000000000000000000000000000000000000000000000000000000000000000",  # noqa: E501
            ommers_hash="0x1dcc4de8dec75d7aab85b567b6ccd41ad312451b948a7413f0a142fd40d49347",  # noqa: E501
            coinbase="0x0000000000000000000000000000000000000000",
            state_root=t8n.calc_state_root(
                self.genesis_environment,
                json.loads(json.dumps(self.pre, cls=JSONEncoder)),
                fork,
            ),
            transactions_root=EmptyTrieRoot,
            receipt_root=EmptyTrieRoot,
            bloom="0x00000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000",  # noqa: E501
            difficulty=0x20000,
            number=0,
            gas_limit=self.genesis_environment.gas_limit,
            gas_used=0,
            timestamp=0,
            extra_data="0x00",
            mix_digest="0x0000000000000000000000000000000000000000000000000000000000000000",  # noqa: E501
            nonce="0x0000000000000000",
            base_fee=base_fee,
        )

        (_, h) = b11r.build(genesis.to_geth_dict(), "", [])
        genesis.hash = h

        return genesis

    def make_block(
        self,
        b11r: BlockBuilder,
        t8n: TransitionTool,
        fork: str,
        block: Block,
        previous_env: Environment,
        previous_alloc: Mapping[str, Any],
        previous_head: str,
        chain_id=1,
        reward=0,
    ) -> Tuple[FixtureBlock, Environment, Mapping[str, Any], str]:
        """
        Produces a block based on the previous environment and allocation.
        If the block is an invalid block, the environment and allocation
        returned are the same as passed as parameters.
        Raises exception on invalid test behavior.

        Returns
        -------
            FixtureBlock: Block to be appended to the fixture.
            Environment: Environment for the next block to produce.
                If the produced block is invalid, this is exactly the same
                environment as the one passed as parameter.
            Mapping[str, Any]: Allocation for the next block to produce.
                If the produced block is invalid, this is exactly the same
                allocation as the one passed as parameter.
            str: Hash of the head of the chain, only updated if the produced
                block is not invalid.

        """
        if block.rlp and block.exception is not None:
            raise Exception(
                "test correctness: post-state cannot be verified if the "
                + "block's rlp is supplied and the block is not supposed "
                + "to produce an exception"
            )

        if block.rlp is None:
            # This is the most common case, the RLP needs to be constructed
            # based on the transactions to be included in the block.
            # Set the environment according to the block to execute.
            env = block.set_environment(previous_env)

            with tempfile.NamedTemporaryFile() as txs_rlp_file:
                (next_alloc, result) = t8n.evaluate(
                    previous_alloc,
                    json.loads(
                        json.dumps(
                            block.txs,
                            cls=JSONEncoder,
                        )
                    )
                    if block.txs is not None
                    else [],
                    json.loads(json.dumps(env, cls=JSONEncoder)),
                    fork,
                    txsPath=txs_rlp_file.name,
                    chain_id=chain_id,
                    reward=reward,
                )
                txs_rlp = txs_rlp_file.read().decode().strip('"')

            rejected_txs = verify_transactions(block.txs, result)
            if len(rejected_txs) > 0:
                # TODO: This block is invalid because it contains intrinsically
                #       invalid transactions
                pass

            header = FixtureHeader.from_dict(
                result
                | {
                    "parentHash": env.parent_hash(),
                    "miner": env.coinbase,
                    "transactionsRoot": result.get("txRoot"),
                    "difficulty": result.get("currentDifficulty"),
                    "number": str(env.number),
                    "gasLimit": str(env.gas_limit),
                    "timestamp": str(env.timestamp),
                    "extraData": block.extra_data
                    if block.extra_data is not None
                    and len(block.extra_data) != 0
                    else "0x",
                    "sha3Uncles": "0x1dcc4de8dec75d7aab85b567b6ccd41ad312451b948a7413f0a142fd40d49347",  # noqa: E501
                    "mixHash": "0x0000000000000000000000000000000000000000000000000000000000000000",  # noqa: E501
                    "nonce": "0x0000000000000000",
                    "baseFeePerGas": result.get("currentBaseFee"),
                }
            )

            if block.rlp_modifier is not None:
                # Modify any parameter specified in the `rlp_modifier` after
                # transition tool processing.
                header = header.join(block.rlp_modifier)

            rlp, header.hash = b11r.build(
                header.to_geth_dict(), txs_rlp, [], None
            )

            if block.exception is None:
                # Return environment and allocation of the following block
                return (
                    FixtureBlock(
                        rlp=rlp,
                        block_header=header,
                    ),
                    env.apply_new_parent(header),
                    next_alloc,
                    header.hash,
                )
            else:
                return (
                    FixtureBlock(
                        rlp=rlp,
                        expected_exception=block.exception,
                    ),
                    previous_env,
                    previous_alloc,
                    previous_head,
                )
        else:
            return (
                FixtureBlock(
                    rlp=block.rlp,
                    expected_exception=block.exception,
                ),
                previous_env,
                previous_alloc,
                previous_head,
            )

    def make_blocks(
        self,
        b11r: BlockBuilder,
        t8n: TransitionTool,
        genesis: FixtureHeader,
        fork: str,
        chain_id=1,
        reward=0,
    ) -> Tuple[List[FixtureBlock], str]:
        """
        Create a block list from the blockchain test definition.
        Performs checks against the expected behavior of the test.
        Raises exception on invalid test behavior.
        """
        alloc: Mapping[str, Any] = json.loads(
            json.dumps(self.pre, cls=JSONEncoder)
        )
        env = Environment.from_parent_header(genesis)
        blocks: List[FixtureBlock] = []
        head = (
            genesis.hash
            if genesis.hash is not None
            else "0x0000000000000000000000000000000000000000000000000000000000000000"  # noqa: E501
        )
        for block in self.blocks:
            fixture_block, env, alloc, head = self.make_block(
                b11r=b11r,
                t8n=t8n,
                fork=fork,
                block=block,
                previous_env=env,
                previous_alloc=alloc,
                previous_head=head,
                chain_id=chain_id,
                reward=reward,
            )
            blocks.append(fixture_block)

        verify_post_alloc(self.post, alloc)

        return (blocks, head)


BlockchainTestSpec = Callable[[str], Generator[BlockchainTest, None, None]]
