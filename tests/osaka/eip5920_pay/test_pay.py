"""Tests for the Pay opcode."""


import pytest

from ethereum_test_tools import Account, Alloc
from ethereum_test_tools import Opcodes as Op
from ethereum_test_tools import StateTestFiller, Transaction

REFERENCE_SPEC_GIT_PATH = "EIPS/eip-5920.md"
REFERENCE_SPEC_VERSION = "4334df83395693dc3f629bb43c18320d9e22e8c9"

pytestmark = pytest.mark.valid_from("Osaka")


def test_pay(
    state_test: StateTestFiller,
    pre: Alloc,
):
    """Test the pay opcode updates the balance but does not execute any code."""
    # Deploy the contract.
    value_amount = 1
    recipient_contract = pre.deploy_contract(Op.SSTORE(0, 1) + Op.STOP)
    contract_address = pre.deploy_contract(Op.PAY(recipient_contract, value_amount) + Op.STOP)
    sender = pre.fund_eoa()

    tx = Transaction(
        to=contract_address,
        value=value_amount,
        sender=sender,
        gas_limit=100_000,
    )

    state_test(
        pre=pre,
        tx=tx,
        post={
            recipient_contract: Account(
                balance=value_amount,
                storage={},
            )
        },
    )
