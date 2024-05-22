"""
Fork rules for clients ran within hive, starting from the Merge fork as
we are executing blocks using the Engine API.
"""

# TODO: 1) Can we programmatically generate this?
# TODO: 2) Can we generate a single ruleset for both rlp and engine_api simulators.
client_fork_ruleset = {
    "Merge": {
        "HIVE_FORK_HOMESTEAD": 0,
        "HIVE_FORK_TANGERINE": 0,
        "HIVE_FORK_SPURIOUS": 0,
        "HIVE_FORK_BYZANTIUM": 0,
        "HIVE_FORK_CONSTANTINOPLE": 0,
        "HIVE_FORK_PETERSBURG": 0,
        "HIVE_FORK_ISTANBUL": 0,
        "HIVE_FORK_BERLIN": 0,
        "HIVE_FORK_LONDON": 0,
        "HIVE_FORK_MERGE": 0,
        "HIVE_TERMINAL_TOTAL_DIFFICULTY": 0,
    },
    "Shanghai": {
        "HIVE_FORK_HOMESTEAD": 0,
        "HIVE_FORK_TANGERINE": 0,
        "HIVE_FORK_SPURIOUS": 0,
        "HIVE_FORK_BYZANTIUM": 0,
        "HIVE_FORK_CONSTANTINOPLE": 0,
        "HIVE_FORK_PETERSBURG": 0,
        "HIVE_FORK_ISTANBUL": 0,
        "HIVE_FORK_BERLIN": 0,
        "HIVE_FORK_LONDON": 0,
        "HIVE_FORK_MERGE": 0,
        "HIVE_TERMINAL_TOTAL_DIFFICULTY": 0,
        "HIVE_SHANGHAI_TIMESTAMP": 0,
    },
    "MergeToShanghaiAtTime15k": {
        "HIVE_FORK_HOMESTEAD": 0,
        "HIVE_FORK_TANGERINE": 0,
        "HIVE_FORK_SPURIOUS": 0,
        "HIVE_FORK_BYZANTIUM": 0,
        "HIVE_FORK_CONSTANTINOPLE": 0,
        "HIVE_FORK_PETERSBURG": 0,
        "HIVE_FORK_ISTANBUL": 0,
        "HIVE_FORK_BERLIN": 0,
        "HIVE_FORK_LONDON": 0,
        "HIVE_FORK_MERGE": 0,
        "HIVE_TERMINAL_TOTAL_DIFFICULTY": 0,
        "HIVE_SHANGHAI_TIMESTAMP": 15000,
    },
    "Cancun": {
        "HIVE_FORK_HOMESTEAD": 0,
        "HIVE_FORK_TANGERINE": 0,
        "HIVE_FORK_SPURIOUS": 0,
        "HIVE_FORK_BYZANTIUM": 0,
        "HIVE_FORK_CONSTANTINOPLE": 0,
        "HIVE_FORK_PETERSBURG": 0,
        "HIVE_FORK_ISTANBUL": 0,
        "HIVE_FORK_BERLIN": 0,
        "HIVE_FORK_LONDON": 0,
        "HIVE_FORK_MERGE": 0,
        "HIVE_TERMINAL_TOTAL_DIFFICULTY": 0,
        "HIVE_SHANGHAI_TIMESTAMP": 0,
        "HIVE_CANCUN_TIMESTAMP": 0,
    },
    "ShanghaiToCancunAtTime15k": {
        "HIVE_FORK_HOMESTEAD": 0,
        "HIVE_FORK_TANGERINE": 0,
        "HIVE_FORK_SPURIOUS": 0,
        "HIVE_FORK_BYZANTIUM": 0,
        "HIVE_FORK_CONSTANTINOPLE": 0,
        "HIVE_FORK_PETERSBURG": 0,
        "HIVE_FORK_ISTANBUL": 0,
        "HIVE_FORK_BERLIN": 0,
        "HIVE_FORK_LONDON": 0,
        "HIVE_FORK_MERGE": 0,
        "HIVE_TERMINAL_TOTAL_DIFFICULTY": 0,
        "HIVE_SHANGHAI_TIMESTAMP": 0,
        "HIVE_CANCUN_TIMESTAMP": 15000,
    },
}
