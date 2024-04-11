"""
Helper functions for the EIP-2537 BLS12-381 precompiles tests.
"""
import os
from typing import Annotated, List

import pytest
from pydantic import BaseModel, BeforeValidator, ConfigDict, RootModel, TypeAdapter
from pydantic.alias_generators import to_pascal


def current_python_script_directory() -> str:
    """
    Get the current Python script directory.
    """
    return os.path.dirname(os.path.realpath(__file__))


class TestVector(BaseModel):
    """
    Test vector for the BLS12-381 precompiles.
    """

    input: Annotated[bytes, BeforeValidator(bytes.fromhex)]
    expected: Annotated[bytes, BeforeValidator(bytes.fromhex)]
    gas: int
    name: str

    model_config = ConfigDict(alias_generator=to_pascal)

    def to_pytest_param(self):
        """
        Convert the test vector to a tuple that can be used as a parameter in a pytest test.
        """
        return pytest.param(self.input, self.expected, id=self.name)


class TestVectorList(RootModel):
    """
    List of test vectors for the BLS12-381 precompiles.
    """

    root: List[TestVector]


TestVectorListAdapter = TypeAdapter(TestVectorList)


def vectors_from_file(filename: str) -> List[pytest.param]:
    """
    Load test vectors from a file.
    """
    full_path = os.path.join(
        current_python_script_directory(),
        "vectors",
        filename,
    )
    with open(full_path, "rb") as f:
        return [v.to_pytest_param() for v in TestVectorListAdapter.validate_json(f.read()).root]
