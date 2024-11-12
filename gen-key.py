"""
Script to generate an Ethereum private key along with its address.
"""

import random

from ethereum_test_tools import EOA

eoa = EOA(key=random.randint(0, 2**256))
print(eoa.key)
print(eoa)
