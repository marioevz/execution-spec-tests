"""
Test EIP-4844: Shard Blob Transactions (Point Evaulation Precompile)
EIP: https://eips.ethereum.org/EIPS/eip-4844
"""
import glob
import os
from dataclasses import dataclass
from hashlib import sha256
from typing import List

import yaml

from ethereum_test_forks import Fork, ShardingFork
from ethereum_test_tools import (
    Account,
    Block,
    BlockchainTest,
    TestAddress,
    Transaction,
    test_from,
    to_address,
)
from ethereum_test_tools.vm.opcode import Opcodes as Op

# REFERENCE_SPEC_GIT_PATH = "EIPS/eip-4844.md"
# REFERENCE_SPEC_VERSION = "b33e063530f0a114635dd4f89d3cca90f8cac28f"

POINT_EVALUATION_PRECOMPILE_ADDRESS = 0x14
POINT_EVALUATION_PRECOMPILE_GAS = 50000
BLOB_COMMITMENT_VERSION_KZG = b"\x01"

BLS_MODULUS = (
    0x73EDA753299D7D483339D80809A1D80553BDA402FFFE5BFEFFFFFFFF00000001
)
BLS_MODULUS_BYTES = BLS_MODULUS.to_bytes(32, "big")
FIELD_ELEMENTS_PER_BLOB = 4096
FIELD_ELEMENTS_PER_BLOB_BYTES = FIELD_ELEMENTS_PER_BLOB.to_bytes(32, "big")


def kzg_to_versioned_hash(
    kzg_commitment: bytes | int,  # 48 bytes
    blob_commitment_version_kzg: bytes | int = BLOB_COMMITMENT_VERSION_KZG,
) -> bytes:
    if isinstance(kzg_commitment, int):
        kzg_commitment = kzg_commitment.to_bytes(48, "big")
    if isinstance(blob_commitment_version_kzg, int):
        blob_commitment_version_kzg = blob_commitment_version_kzg.to_bytes(
            1, "big"
        )
    return blob_commitment_version_kzg + sha256(kzg_commitment).digest()[1:]


def format_point_evaluation_precompile_input(
    versioned_hash: bytes | int,  # 32 bytes
    z: bytes | int,  # 32 bytes
    y: bytes | int,  # 32 bytes
    kzg_commitment: bytes | int,  # 48 bytes
    kzg_proof: bytes | int,  # 48 bytes
) -> bytes:
    """
    Format the input for the point evaluation precompile.
    """
    if isinstance(versioned_hash, int):
        versioned_hash = versioned_hash.to_bytes(32, "big")
    if isinstance(z, int):
        z = z.to_bytes(32, "big")
    if isinstance(y, int):
        y = y.to_bytes(32, "big")
    if isinstance(kzg_commitment, int):
        kzg_commitment = kzg_commitment.to_bytes(48, "big")
    if isinstance(kzg_proof, int):
        kzg_proof = kzg_proof.to_bytes(48, "big")

    return versioned_hash + z + y + kzg_commitment + kzg_proof


@dataclass(kw_only=True)
class KZGPointEvaluation:
    """
    KZG Point Evaluation.
    """

    name: str = ""
    z: bytes | int
    y: bytes | int
    kzg_commitment: bytes | int
    kzg_proof: bytes | int
    versioned_hash: bytes | int | None = None
    correct: bool

    def get_precompile_input(self) -> bytes:
        """
        Get the input for the point evaluation precompile.
        """
        return format_point_evaluation_precompile_input(
            self.versioned_hash
            if self.versioned_hash is not None
            else kzg_to_versioned_hash(self.kzg_commitment),
            self.z,
            self.y,
            self.kzg_commitment,
            self.kzg_proof,
        )

    def generate_blockchain_test(self) -> BlockchainTest:
        """
        Generate BlockchainTest.
        """

        precompile_caller_code = Op.CALLDATACOPY(0, 0, Op.CALLDATASIZE)
        precompile_caller_code += Op.SSTORE(
            0,
            Op.CALL(
                Op.GAS,
                POINT_EVALUATION_PRECOMPILE_ADDRESS,
                0x00,
                0x00,
                Op.CALLDATASIZE,
                0x00,
                0x40,
            ),
        )  # Store the result of the precompile call in storage slot 0
        precompile_caller_code += Op.SSTORE(1, Op.MLOAD(0x00))
        precompile_caller_code += Op.SSTORE(2, Op.MLOAD(0x20))

        precompile_caller_address = to_address(0x100)

        pre = {
            TestAddress: Account(
                nonce=0,
                balance=0x10**18,
            ),
            precompile_caller_address: Account(
                nonce=0,
                code=precompile_caller_code,
            ),
        }

        tx = Transaction(
            ty=2,
            nonce=0,
            data=self.get_precompile_input(),
            to=precompile_caller_address,
            value=0,
            gas_limit=POINT_EVALUATION_PRECOMPILE_GAS * 10,
            max_fee_per_gas=7,
            max_priority_fee_per_gas=0,
        )

        post = (
            {
                precompile_caller_address: Account(
                    storage={
                        0: 1,
                        1: FIELD_ELEMENTS_PER_BLOB,
                        2: BLS_MODULUS,
                    },
                ),
            }
            if self.correct
            else {
                precompile_caller_address: Account(
                    storage={
                        0: 0,
                        1: 0,
                        2: 0,
                    },
                ),
            }
        )

        return BlockchainTest(
            tag=self.name,
            pre=pre,
            post=post,
            blocks=[Block(txs=[tx])],
        )

    @classmethod
    def from_dict(cls, data: dict) -> "KZGPointEvaluation":
        """
        Create a KZGPointEvaluation from a dictionary.
        """
        if "input" not in data:
            raise ValueError("Missing 'input' key in data")
        if "output" not in data:
            raise ValueError("Missing 'output' key in data")
        if isinstance(data["output"], bool):
            correct = data["output"]
        else:
            correct = False
        input = data["input"]
        if "commitment" not in input or not isinstance(
            input["commitment"], str
        ):
            raise ValueError("Missing 'commitment' key in data['input']")
        commitment = bytes.fromhex(input["commitment"][2:])
        if "proof" not in input or not isinstance(input["proof"], str):
            raise ValueError("Missing 'proof' key in data['input']")
        proof = bytes.fromhex(input["proof"][2:])
        if "z" not in input or not isinstance(input["z"], str):
            raise ValueError("Missing 'z' key in data['input']")
        z = bytes.fromhex(input["z"][2:])
        if "y" not in input or not isinstance(input["y"], str):
            raise ValueError("Missing 'y' key in data['input']")
        y = bytes.fromhex(input["y"][2:])

        return cls(
            z=z,
            y=y,
            kzg_commitment=commitment,
            kzg_proof=proof,
            correct=correct,
        )

    @classmethod
    def from_yml_file(cls, file_path: str) -> "KZGPointEvaluation":
        """
        Create a KZGPointEvaluation from a YAML file.
        """
        with open(file_path, "r") as f:
            parent_dir_name = os.path.basename(os.path.dirname(file_path))
            kzg = cls.from_dict(yaml.safe_load(f))
            kzg.name = parent_dir_name
            return kzg


def load_kzg_point_evaluation_from_dir(
    dir_path: str,
) -> list[KZGPointEvaluation]:
    """
    Load KZG Point Evaluations from a directory.
    """
    files = glob.glob(os.path.join(dir_path, "*.yaml"))
    return [KZGPointEvaluation.from_yml_file(file) for file in files]


def current_python_script_directory() -> str:
    """
    Get the current Python script directory.
    """
    return os.path.dirname(os.path.realpath(__file__))


# @test_from(fork=ShardingFork)
def test_point_eval_precompile_gas_usage(_: Fork):
    """
    Test Precompile Gas Usage.
    """


@test_from(fork=ShardingFork)
def test_point_eval_precompile(_: Fork):
    """
    Tests for the Point Evaluation Precompile.
    Verify p(z) = y given commitment that corresponds to the polynomial p(x)
    and a KZG proof.
    Also verify that the provided commitment matches the provided
    versioned_hash.
    """

    test_cases: List[KZGPointEvaluation] = [
        KZGPointEvaluation(
            name="out_of_bounds_z",
            z=BLS_MODULUS,
            y=0,
            kzg_commitment=0,
            kzg_proof=0,
            correct=False,
        ),
        KZGPointEvaluation(
            name="out_of_bounds_y",
            z=0,
            y=BLS_MODULUS,
            kzg_commitment=0,
            kzg_proof=0,
            correct=False,
        ),
        KZGPointEvaluation(
            name="correct_proof_1",
            z=0x623CE31CF9759A5C8DAF3A357992F9F3DD7F9339D8998BC8E68373E54F00B75E,
            y=0x0000000000000000000000000000000000000000000000000000000000000000,
            kzg_commitment=0xC00000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000,
            kzg_proof=0xC00000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000,
            correct=True,
        ),
        KZGPointEvaluation(
            name="correct_proof_1_incorrect_versioned_hash_version_0x00",
            z=0x623CE31CF9759A5C8DAF3A357992F9F3DD7F9339D8998BC8E68373E54F00B75E,
            y=0x0000000000000000000000000000000000000000000000000000000000000000,
            kzg_commitment=0xC00000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000,
            kzg_proof=0xC00000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000,
            versioned_hash=kzg_to_versioned_hash(
                0xC00000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000,
                0x00,
            ),
            correct=False,
        ),
        KZGPointEvaluation(
            name="correct_proof_1_incorrect_versioned_hash_version_0x02",
            z=0x623CE31CF9759A5C8DAF3A357992F9F3DD7F9339D8998BC8E68373E54F00B75E,
            y=0x0000000000000000000000000000000000000000000000000000000000000000,
            kzg_commitment=0xC00000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000,
            kzg_proof=0xC00000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000,
            versioned_hash=kzg_to_versioned_hash(
                0xC00000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000,
                0x02,
            ),
            correct=False,
        ),
        KZGPointEvaluation(
            name="correct_proof_1_incorrect_versioned_hash_version_0xff",
            z=0x623CE31CF9759A5C8DAF3A357992F9F3DD7F9339D8998BC8E68373E54F00B75E,
            y=0x0000000000000000000000000000000000000000000000000000000000000000,
            kzg_commitment=0xC00000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000,
            kzg_proof=0xC00000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000,
            versioned_hash=kzg_to_versioned_hash(
                0xC00000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000,
                0xFF,
            ),
            correct=False,
        ),
    ]

    # Rest are loaded from the YAML files
    kzg_loaded_tests = load_kzg_point_evaluation_from_dir(
        current_python_script_directory() + "/verify_kzg_proof/small/*/"
    )
    assert len(kzg_loaded_tests) > 0

    test_cases += kzg_loaded_tests

    for test_case in test_cases:
        yield test_case.generate_blockchain_test()
