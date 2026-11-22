from dataclasses import dataclass
from embit.bip32 import HARDENED_INDEX
from typing import List

from seedsigner.models.settings_definition import SettingsConstants



@dataclass(frozen=True)
class DerivationPathValidationResult:
    """
    What DerivationPathValidator.validate() found for one derivation path. See
    DerivationPathValidator for what each status means.
    """
    status: str
    policy_type: str
    derivation_path: List[int]

    # Where the path stops matching the policy type's standard path, as an index into
    # derivation_path. None for a standard path.
    offending_level_index: int = None

    # STATUS__ANOTHER_NETWORK only: the network the path's coin type is for
    # (SettingsConstants.MAINNET or TESTNET).
    indicated_network: str = None

    # STATUS__ANOTHER_SCRIPT_TYPE only: the policy type this is a standard path for.
    indicated_policy_type: str = None

    # STATUS__STANDARD only: the path split into its base path (the wallet), "branch",
    # and "address_index".
    base_path: List[int] = None
    branch: int = None
    address_index: int = None


    @property
    def is_standard(self) -> bool:
        return self.status == DerivationPathValidator.STATUS__STANDARD



class DerivationPathValidator:
    """
    Decides whether a derivation path is "standard": a path that a wallet following the
    standard derivation BIPs (BIP-44, BIP-49, BIP-84, BIP-86, BIP-48, etc.) derives and
    scans when the seed is restored.

    A standard full path is a registry base path followed by exactly two non-hardened
    levels:
        [base path] / "branch" / "address_index"

    The "branch" must be receive (0) or change (1). The base path must match one of the
    registry entries for the path's policy type (its script type, plus single sig or
    multisig), using:
      * the network's coin type: 0h for mainnet, 1h for every test network.
      * an allowed account: 0 through 9 for every policy type, plus the Whirlpool
        accounts for native segwit single sig.
      * for Unchained's vaults, a vault index from 0 through 9.

    The account range is our own line, not a rule of BIP-32. It is drawn where wallet
    discovery commonly stops: Sparrow, for example, scans accounts 0-9 (plus its
    Whirlpool accounts) when it restores a wallet.

    A path that isn't standard is sorted further, so the user can be told what is off:
      * another network: a standard path for the same policy type, but with the other
        network's coin type.
      * another script type: a standard path for a different policy type.
      * nonstandard: anything else.

    Only an exact match counts as another network or another script type. A path with
    any other problem as well is just nonstandard, and so is a path that is standard
    for more than one other policy type. That way a reported mismatch always names the
    one network or policy type whose standard path this really is.

    The network is passed on each call rather than stored on the validator. That way a
    validator can never check paths against a different network than the one its
    caller is using.
    """
    STATUS__STANDARD = "standard"
    STATUS__ANOTHER_NETWORK = "another_network"
    STATUS__ANOTHER_SCRIPT_TYPE = "another_script_type"
    STATUS__NONSTANDARD = "nonstandard"

    # The coin type level of a standard path. Every test network (testnet, regtest,
    # signet, testnet4) uses coin type 1, so the coin type alone can't tell them apart.
    COIN_TYPE__MAINNET = 0 + HARDENED_INDEX
    COIN_TYPE__TESTNET = 1 + HARDENED_INDEX

    # Stand-ins for the registry levels that vary. Every other level in a registry entry
    # is a fixed index, hardened or not.
    LEVEL__COIN_TYPE = "coin_type"
    LEVEL__ACCOUNT = "account"
    LEVEL__VAULT_INDEX = "vault_index"

    # Each policy type's standard base paths, one item per level. The first entry is the
    # policy type's primary base path: build_base_path() returns it, and the offending
    # level for another script type is measured against it. The others are accepted but
    # never built.
    STANDARD_REGISTRY = {
        "p2pkh":       [(44 + HARDENED_INDEX, LEVEL__COIN_TYPE, LEVEL__ACCOUNT)],  # BIP-44
        "p2sh-p2wpkh": [(49 + HARDENED_INDEX, LEVEL__COIN_TYPE, LEVEL__ACCOUNT)],  # BIP-49
        "p2wpkh":      [(84 + HARDENED_INDEX, LEVEL__COIN_TYPE, LEVEL__ACCOUNT)],  # BIP-84
        "p2tr":        [(86 + HARDENED_INDEX, LEVEL__COIN_TYPE, LEVEL__ACCOUNT)],  # BIP-86

        "p2sh": [
            # Bare m/45h, as SeedSigner, Sparrow, and Coldcard use it. A true BIP-45 path
            # adds a cosigner index level, so it is nonstandard here.
            (45 + HARDENED_INDEX,),

            # Caravan
            (45 + HARDENED_INDEX, LEVEL__COIN_TYPE, LEVEL__ACCOUNT),

            # Unchained vaults
            (45 + HARDENED_INDEX, 0, 0, LEVEL__VAULT_INDEX),
        ],

        # BIP-48 ends the base path with a script type level: 1h for nested segwit, 2h
        # for native segwit.
        "p2sh-p2wsh": [(48 + HARDENED_INDEX, LEVEL__COIN_TYPE, LEVEL__ACCOUNT, 1 + HARDENED_INDEX)],
        "p2wsh": [
            (48 + HARDENED_INDEX, LEVEL__COIN_TYPE, LEVEL__ACCOUNT, 2 + HARDENED_INDEX),

            # Unchained vaults
            (45 + HARDENED_INDEX, 0, 0, LEVEL__VAULT_INDEX),
        ],
    }

    # TODO: Add BIP-352 silent payment paths once SeedSigner supports spending silent
    # payments. Their keys sit at m/352h/coin_type/account/0h/0 (spend) and .../1h/0
    # (scan), a hardened "branch" rather than 0 or 1, so a registry entry will need to
    # define its own levels after the base path.

    STANDARD_ACCOUNTS = range(10)

    # Sparrow's Whirlpool accounts: Badbank, Premix, and Postmix. Sparrow scans them
    # when it restores a wallet, and people are still spending Postmix coins since
    # Whirlpool shut down in 2024. As in Sparrow, they are standard for native segwit
    # single sig only.
    WHIRLPOOL_ACCOUNTS = (2147483644, 2147483645, 2147483646)

    # The account numbers (not hardened) each policy type's account level may use
    STANDARD_ALLOWED_ACCOUNTS = {
        "p2pkh":       STANDARD_ACCOUNTS,
        "p2sh-p2wpkh": STANDARD_ACCOUNTS,
        "p2wpkh":      tuple(STANDARD_ACCOUNTS) + WHIRLPOOL_ACCOUNTS,
        "p2tr":        STANDARD_ACCOUNTS,
        "p2sh":        STANDARD_ACCOUNTS,
        "p2sh-p2wsh":  STANDARD_ACCOUNTS,
        "p2wsh":       STANDARD_ACCOUNTS,
    }

    # Unchained's per-vault index (its "product key")
    UNCHAINED_VAULT_INDICES = range(10)


    def __init__(self, registry: dict = None, allowed_accounts: dict = None):
        """
        Defaults to the standard registry and accounts. A flow that needs a different
        policy can pass its own:
          * registry: maps each policy type to its base paths, primary first, in the same
            form as STANDARD_REGISTRY.
          * allowed_accounts: maps each policy type to the account numbers (not
            hardened) it allows. A policy type with no entry allows no account.
        """
        if registry is None:
            registry = DerivationPathValidator.STANDARD_REGISTRY
        if allowed_accounts is None:
            allowed_accounts = DerivationPathValidator.STANDARD_ALLOWED_ACCOUNTS

        self.registry = registry
        self.allowed_accounts = allowed_accounts


    @staticmethod
    def get_coin_type(network: str) -> int:
        """
        Returns the coin type level that standard paths use on network. Raises
        ValueError for an unrecognized network.
        """
        if network == SettingsConstants.MAINNET:
            return DerivationPathValidator.COIN_TYPE__MAINNET

        if network in (SettingsConstants.TESTNET, SettingsConstants.REGTEST):
            return DerivationPathValidator.COIN_TYPE__TESTNET

        raise ValueError(f"Unexpected network: {network}")


    def build_base_path(self, policy_type: str, network: str, account: int = 0) -> List[int]:
        """
        Returns policy_type's primary base path on network, at the given account number
        (not hardened). A base path with no account level, such as legacy multisig's
        m/45h, ignores account.
        """
        # Checked even when the base path has no coin type level, so an unrecognized
        # network is never silently accepted.
        coin_type = DerivationPathValidator.get_coin_type(network)

        base_path = []
        for level in self.registry[policy_type][0]:
            if level == DerivationPathValidator.LEVEL__COIN_TYPE:
                base_path.append(coin_type)
            elif level == DerivationPathValidator.LEVEL__ACCOUNT:
                base_path.append(account + HARDENED_INDEX)
            else:
                base_path.append(level)
        return base_path


    def validate(self, derivation_path: List[int], policy_type: str, network: str) -> DerivationPathValidationResult:
        """
        Checks derivation_path against policy_type's standard paths on network, in this
        order:
          1. standard: a standard full path for policy_type.
          2. another network: a standard full path for policy_type, but at the other
             network's coin type.
          3. another script type: a standard full path for exactly one other policy
             type.
          4. nonstandard: anything else.

        A result that isn't standard points at its offending level:
          * another network: the coin type.
          * another script type: the first level that differs from policy_type's primary
            base path, which is the purpose or BIP-48's script type level.
          * nonstandard: where the closest of policy_type's base paths, the one that
            matches the most leading levels, stops matching.

        policy_type is an embit policy type, e.g. "p2wpkh" or "p2sh-p2wsh". Whatever the
        path, a result is returned rather than raised. Raises ValueError only for an
        unrecognized network.
        """
        derivation_path = list(derivation_path)
        coin_type = DerivationPathValidator.get_coin_type(network)
        base_paths = self.registry.get(policy_type, [])

        if not derivation_path:
            # The master key itself, which no wallet spends from. There is no level to
            # point at.
            return DerivationPathValidationResult(
                status=DerivationPathValidator.STATUS__NONSTANDARD,
                policy_type=policy_type,
                derivation_path=derivation_path,
            )

        matching_base_path = self._find_matching_base_path(derivation_path, policy_type, coin_type)
        if matching_base_path is not None:
            base_path_length = len(matching_base_path)
            return DerivationPathValidationResult(
                status=DerivationPathValidator.STATUS__STANDARD,
                policy_type=policy_type,
                derivation_path=derivation_path,
                base_path=derivation_path[:base_path_length],
                branch=derivation_path[base_path_length],
                address_index=derivation_path[base_path_length + 1],
            )

        if coin_type == DerivationPathValidator.COIN_TYPE__MAINNET:
            other_coin_type = DerivationPathValidator.COIN_TYPE__TESTNET
            other_network = SettingsConstants.TESTNET
        else:
            other_coin_type = DerivationPathValidator.COIN_TYPE__MAINNET
            other_network = SettingsConstants.MAINNET

        for base_path_levels in base_paths:
            if DerivationPathValidator.LEVEL__COIN_TYPE not in base_path_levels:
                # A base path without a coin type is the same on every network
                continue

            if self._find_offending_level_index(derivation_path, base_path_levels, policy_type, other_coin_type) is None:
                return DerivationPathValidationResult(
                    status=DerivationPathValidator.STATUS__ANOTHER_NETWORK,
                    policy_type=policy_type,
                    derivation_path=derivation_path,
                    offending_level_index=base_path_levels.index(DerivationPathValidator.LEVEL__COIN_TYPE),
                    indicated_network=other_network,
                )

        # The Unchained vault layout is standard for both legacy and native segwit
        # multisig. A path that is standard for more than one other policy type has no one
        # script type to name, so it is nonstandard.
        other_policy_types = [
            other_policy_type for other_policy_type in self.registry
            if other_policy_type != policy_type and self._find_matching_base_path(derivation_path, other_policy_type, coin_type) is not None
        ]
        if len(other_policy_types) == 1:
            if base_paths:
                offending_level_index = self._find_offending_level_index(derivation_path, base_paths[0], policy_type, coin_type)
            else:
                # There is no standard path to compare against, so the mismatch starts at
                # the purpose.
                offending_level_index = 0

            return DerivationPathValidationResult(
                status=DerivationPathValidator.STATUS__ANOTHER_SCRIPT_TYPE,
                policy_type=policy_type,
                derivation_path=derivation_path,
                offending_level_index=offending_level_index,
                indicated_policy_type=other_policy_types[0],
            )

        # The base path that matches the most leading levels has the largest offending
        # level. With no base paths at all, the mismatch starts at the purpose.
        offending_level_index = max(
            [self._find_offending_level_index(derivation_path, base_path_levels, policy_type, coin_type) for base_path_levels in base_paths],
            default=0,
        )
        return DerivationPathValidationResult(
            status=DerivationPathValidator.STATUS__NONSTANDARD,
            policy_type=policy_type,
            derivation_path=derivation_path,
            offending_level_index=offending_level_index,
        )


    def _find_matching_base_path(self, derivation_path: List[int], policy_type: str, coin_type: int) -> tuple | None:
        """
        Returns the first of policy_type's base paths that derivation_path is a standard
        full path for at coin_type, or None if there is none.
        """
        for base_path_levels in self.registry.get(policy_type, []):
            if self._find_offending_level_index(derivation_path, base_path_levels, policy_type, coin_type) is None:
                return base_path_levels
        return None


    def _find_offending_level_index(self, derivation_path: List[int], base_path_levels: tuple, policy_type: str, coin_type: int) -> int | None:
        """
        Compares derivation_path, level by level, with a standard full path on one of
        policy_type's base paths at coin_type. Returns None if they match exactly.
        Otherwise returns the index of the first level that doesn't match:
          * a level with the wrong value: a fixed level, the coin type, account, or vault
            index, the "branch", or the "address_index".
          * if every level matches but the path is too long: the first level past the
            standard length.
          * if every level matches but the path ends early: its last level.

        Expects a path with at least one level.
        """
        branch_index = len(base_path_levels)
        address_index_index = branch_index + 1

        for index, level in enumerate(derivation_path):
            if index < branch_index:
                expected_level = base_path_levels[index]
                if expected_level == DerivationPathValidator.LEVEL__COIN_TYPE:
                    is_match = level == coin_type

                elif expected_level == DerivationPathValidator.LEVEL__ACCOUNT:
                    # The account level must be hardened
                    is_match = level >= HARDENED_INDEX and level - HARDENED_INDEX in self.allowed_accounts.get(policy_type, ())

                elif expected_level == DerivationPathValidator.LEVEL__VAULT_INDEX:
                    # The vault index is not hardened
                    is_match = level in DerivationPathValidator.UNCHAINED_VAULT_INDICES

                else:
                    is_match = level == expected_level

            elif index == branch_index:
                # Wallets only scan the receive (0) and change (1) branches
                is_match = level in (0, 1)

            elif index == address_index_index:
                is_match = level < HARDENED_INDEX

            else:
                # Every level up to here matched, but the path keeps going
                return index

            if not is_match:
                return index

        if len(derivation_path) <= address_index_index:
            # Every level present matched, but the path ends early
            return len(derivation_path) - 1

        return None
