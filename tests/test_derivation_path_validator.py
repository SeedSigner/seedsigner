import pytest

from embit.bip32 import parse_path

from seedsigner.models.derivation_path_validator import DerivationPathValidator
from seedsigner.models.settings_definition import SettingsConstants


STANDARD = DerivationPathValidator.STATUS__STANDARD
ANOTHER_NETWORK = DerivationPathValidator.STATUS__ANOTHER_NETWORK
ANOTHER_SCRIPT_TYPE = DerivationPathValidator.STATUS__ANOTHER_SCRIPT_TYPE
NONSTANDARD = DerivationPathValidator.STATUS__NONSTANDARD

# Each policy type's primary base path, written out here rather than read from the
# validator. Each test fills in {coin_type} and {account}. Legacy multisig's Caravan and
# Unchained layouts, and native segwit multisig's Unchained layout, have their own tests.
BASE_PATHS = {
    "p2pkh":       "m/44h/{coin_type}/{account}",
    "p2sh-p2wpkh": "m/49h/{coin_type}/{account}",
    "p2wpkh":      "m/84h/{coin_type}/{account}",
    "p2tr":        "m/86h/{coin_type}/{account}",
    "p2sh":        "m/45h",
    "p2sh-p2wsh":  "m/48h/{coin_type}/{account}/1h",
    "p2wsh":       "m/48h/{coin_type}/{account}/2h",
}

# Every policy type whose primary base path has coin type and account levels: all but
# legacy multisig, whose primary is bare m/45h
POLICY_TYPES_WITH_ACCOUNTS = [policy_type for policy_type in BASE_PATHS if policy_type != "p2sh"]

# Each network, the coin type its standard paths use, and the other network's coin type
NETWORKS = [
    (SettingsConstants.MAINNET, "0h", "1h"),
    (SettingsConstants.TESTNET, "1h", "0h"),
    (SettingsConstants.REGTEST, "1h", "0h"),
]

WHIRLPOOL_ACCOUNTS = ["2147483644h", "2147483645h", "2147483646h"]

# Where the account level sits in every base path that has one
ACCOUNT_LEVEL_INDEX = 2


def base_path(policy_type: str, coin_type: str = "0h", account: str = "0h") -> str:
    return BASE_PATHS[policy_type].format(coin_type=coin_type, account=account)


def branch_level_index(policy_type: str) -> int:
    """The "branch" comes right after the base path"""
    return len(parse_path(BASE_PATHS[policy_type].format(coin_type="0h", account="0h")))


def validate(derivation_path: str, policy_type: str, network: str = SettingsConstants.MAINNET, validator: DerivationPathValidator = None):
    if validator is None:
        validator = DerivationPathValidator()
    return validator.validate(parse_path(derivation_path), policy_type, network)



class TestDerivationPathValidator:

    def test__validate__accepts_a_standard_path_for_every_policy_type(self):
        """
        A standard full path is a registry base path, then the receive or change
        "branch", then a non-hardened "address_index".

        The result also reports the path split into those three parts.
        """
        for network, coin_type, other_coin_type in NETWORKS:
            for policy_type in BASE_PATHS:
                for branch, address_index in [(0, 0), (1, 5), (0, 2147483647)]:
                    derivation_path = f"{base_path(policy_type, coin_type)}/{branch}/{address_index}"
                    result = validate(derivation_path, policy_type, network)

                    assert result.status == STANDARD, derivation_path
                    assert result.is_standard
                    assert result.offending_level_index is None
                    assert result.derivation_path == parse_path(derivation_path)
                    assert result.base_path == parse_path(base_path(policy_type, coin_type))
                    assert result.branch == branch
                    assert result.address_index == address_index


    def test__validate__accepts_accounts_0_through_9(self):
        """
        Accounts 0 through 9 are standard for every policy type that has an account
        level. Account 10 and above are not.
        """
        for network, coin_type, other_coin_type in NETWORKS:
            for policy_type in POLICY_TYPES_WITH_ACCOUNTS:
                for account in ["0h", "9h"]:
                    result = validate(f"{base_path(policy_type, coin_type, account)}/0/5", policy_type, network)
                    assert result.status == STANDARD

                for account in ["10h", "11h", "100h", "2147483647h"]:
                    derivation_path = f"{base_path(policy_type, coin_type, account)}/0/5"
                    result = validate(derivation_path, policy_type, network)
                    assert result.status == NONSTANDARD, derivation_path
                    assert result.offending_level_index == ACCOUNT_LEVEL_INDEX
                    assert not result.is_standard


    def test__validate__requires_a_hardened_account(self):
        """
        The account level must be hardened. A non-hardened account is nonstandard even
        when its number is in range.
        """
        for policy_type in POLICY_TYPES_WITH_ACCOUNTS:
            result = validate(f"{base_path(policy_type, account='0')}/0/5", policy_type)
            assert result.status == NONSTANDARD
            assert result.offending_level_index == ACCOUNT_LEVEL_INDEX


    def test__validate__accepts_the_whirlpool_accounts_for_native_segwit_single_sig_only(self):
        """
        Sparrow's Whirlpool accounts (Badbank, Premix, and Postmix) are standard for
        native segwit single sig. The accounts just outside them are not, and neither are
        the Whirlpool accounts under any other policy type.
        """
        for network, coin_type, other_coin_type in NETWORKS:
            for account in WHIRLPOOL_ACCOUNTS:
                result = validate(f"{base_path('p2wpkh', coin_type, account)}/1/12345", "p2wpkh", network)
                assert result.status == STANDARD

            for account in ["2147483643h", "2147483647h"]:
                result = validate(f"{base_path('p2wpkh', coin_type, account)}/1/12345", "p2wpkh", network)
                assert result.status == NONSTANDARD
                assert result.offending_level_index == ACCOUNT_LEVEL_INDEX

            for policy_type in POLICY_TYPES_WITH_ACCOUNTS:
                if policy_type == "p2wpkh":
                    continue

                for account in WHIRLPOOL_ACCOUNTS:
                    derivation_path = f"{base_path(policy_type, coin_type, account)}/1/12345"
                    result = validate(derivation_path, policy_type, network)
                    assert result.status == NONSTANDARD, derivation_path
                    assert result.offending_level_index == ACCOUNT_LEVEL_INDEX


    def test__validate__requires_the_receive_or_change_branch_and_a_non_hardened_index(self):
        """
        Wallets only scan the receive (0) and change (1) "branches", at non-hardened
        address indices. Anything else on those two levels is nonstandard:
          * "branch" 2
          * a hardened "branch"
          * a hardened "address_index"

        Legacy multisig's layouts under m/45h are covered by their own tests below.
        """
        for network, coin_type, other_coin_type in NETWORKS:
            for policy_type in POLICY_TYPES_WITH_ACCOUNTS:
                branch_index = branch_level_index(policy_type)
                base = base_path(policy_type, coin_type)

                for suffix, offending_level_index in [
                        ("2/5", branch_index),
                        ("0h/5", branch_index),
                        ("1h/5", branch_index),
                        ("0/5h", branch_index + 1),
                        ("1/0h", branch_index + 1)]:
                    derivation_path = f"{base}/{suffix}"
                    result = validate(derivation_path, policy_type, network)
                    assert result.status == NONSTANDARD, derivation_path
                    assert result.offending_level_index == offending_level_index, derivation_path


    def test__validate__refuses_a_negative_address_index(self):
        """
        A psbt stores each level as an unsigned number, so it can't hold a negative index,
        but a path parsed from a string can. A negative "address_index" is nonstandard,
        pointing at that level.
        """
        validator = DerivationPathValidator()
        for network, coin_type, other_coin_type in NETWORKS:
            for policy_type in BASE_PATHS:
                derivation_path = parse_path(base_path(policy_type, coin_type)) + [0, -5]
                result = validator.validate(derivation_path, policy_type, network)
                assert result.status == NONSTANDARD, (policy_type, network)
                assert result.offending_level_index == len(derivation_path) - 1, (policy_type, network)


    def test__validate__refuses_extra_and_missing_levels(self):
        """
        A standard full path has exactly two levels after the base path. The offending
        level is reported as:
          * an extra level between the base path and the "branch" (e.g. /7777): that
            extra level, since it sits where the "branch" should be.
          * an extra level after the "address_index": the first level past the standard
            length.
          * a path that ends early: its last level.
        """
        for network, coin_type, other_coin_type in NETWORKS:
            for policy_type in BASE_PATHS:
                branch_index = branch_level_index(policy_type)
                base = base_path(policy_type, coin_type)

                for derivation_path, offending_level_index in [
                        (f"{base}/7777/0/5", branch_index),
                        (f"{base}/7777/1/0", branch_index),
                        (f"{base}/0/5/9", branch_index + 2),
                        (f"{base}/0", branch_index),
                        (base, branch_index - 1)]:
                    result = validate(derivation_path, policy_type, network)
                    assert result.status == NONSTANDARD, derivation_path
                    assert result.offending_level_index == offending_level_index, derivation_path

        # A base path that is missing one of its own levels
        result = validate("m/84h/0h/0/5", "p2wpkh")
        assert result.status == NONSTANDARD
        assert result.offending_level_index == ACCOUNT_LEVEL_INDEX

        result = validate("m/48h/0h/0h/0/5", "p2wsh")
        assert result.status == NONSTANDARD
        assert result.offending_level_index == 3


    def test__validate__reports_a_standard_path_for_the_other_network(self):
        """
        A path that would be standard for the input's own policy type if it had the other
        network's coin type is reported as another network. The coin type is the
        offending level, and the result names the network that coin type is for.
        """
        for network, coin_type, other_coin_type in NETWORKS:
            expected_network = SettingsConstants.MAINNET if other_coin_type == "0h" else SettingsConstants.TESTNET

            for policy_type in POLICY_TYPES_WITH_ACCOUNTS:
                derivation_path = f"{base_path(policy_type, other_coin_type)}/0/5"
                result = validate(derivation_path, policy_type, network)

                assert result.status == ANOTHER_NETWORK, derivation_path
                assert result.offending_level_index == 1
                assert result.indicated_network == expected_network
                assert result.indicated_policy_type is None
                assert result.base_path is None

            # A Whirlpool Postmix path from the other network
            result = validate(f"{base_path('p2wpkh', other_coin_type, '2147483646h')}/1/12345", "p2wpkh", network)
            assert result.status == ANOTHER_NETWORK
            assert result.indicated_network == expected_network


    def test__validate__reports_another_network_only_when_that_is_the_only_problem(self):
        """
        A path at the other network's coin type that has any other problem as well is
        nonstandard, not another network. The offending level is still the coin type: the
        first level that differs from the input's own standard path.
        """
        for derivation_path in ["m/84h/1h/0h/7777/0/5", "m/84h/1h/10h/0/5", "m/84h/1h/0h/2/5"]:
            result = validate(derivation_path, "p2wpkh", SettingsConstants.MAINNET)
            assert result.status == NONSTANDARD, derivation_path
            assert result.offending_level_index == 1
            assert result.indicated_network is None

        for network in [SettingsConstants.TESTNET, SettingsConstants.REGTEST]:
            result = validate("m/48h/0h/0h/2h/7777/1/0", "p2wsh", network)
            assert result.status == NONSTANDARD
            assert result.offending_level_index == 1


    def test__validate__reports_a_standard_path_for_another_script_type(self):
        """
        A path that is standard for a different policy type is reported as another
        script type. The result names that policy type. The offending level is the first
        level that differs from the input's own standard path: the purpose, or BIP-48's
        script type level.
        """
        # (input policy type, path, the policy type it is standard for, offending level)
        cases = [
            ("p2wpkh", "m/44h/{coin_type}/0h/0/5", "p2pkh", 0),
            ("p2wpkh", "m/49h/{coin_type}/0h/0/5", "p2sh-p2wpkh", 0),
            ("p2wpkh", "m/86h/{coin_type}/0h/0/5", "p2tr", 0),
            ("p2wpkh", "m/45h/0/5", "p2sh", 0),
            ("p2wpkh", "m/48h/{coin_type}/0h/2h/0/5", "p2wsh", 0),
            ("p2wsh", "m/48h/{coin_type}/0h/1h/0/5", "p2sh-p2wsh", 3),
            ("p2wsh", "m/84h/{coin_type}/0h/0/5", "p2wpkh", 0),
            ("p2sh-p2wsh", "m/48h/{coin_type}/0h/2h/1/0", "p2wsh", 3),
            ("p2sh", "m/48h/{coin_type}/0h/2h/1/0", "p2wsh", 0),
            ("p2sh", "m/48h/{coin_type}/0h/1h/0/5", "p2sh-p2wsh", 0),
            ("p2tr", "m/84h/{coin_type}/2147483646h/1/0", "p2wpkh", 0),
        ]
        for network, coin_type, other_coin_type in NETWORKS:
            for policy_type, derivation_path, indicated_policy_type, offending_level_index in cases:
                derivation_path = derivation_path.format(coin_type=coin_type)
                result = validate(derivation_path, policy_type, network)

                assert result.status == ANOTHER_SCRIPT_TYPE, derivation_path
                assert result.indicated_policy_type == indicated_policy_type
                assert result.offending_level_index == offending_level_index
                assert result.indicated_network is None
                assert result.base_path is None


    def test__validate__reports_another_script_type_only_when_that_is_the_only_problem(self):
        """
        A path for another policy type that has any other problem as well is
        nonstandard, not another script type.
        """
        for derivation_path in ["m/49h/0h/0h/7777/0/5", "m/49h/0h/0h/2/5", "m/49h/0h/10h/0/5"]:
            result = validate(derivation_path, "p2wpkh")
            assert result.status == NONSTANDARD, derivation_path
            assert result.offending_level_index == 0
            assert result.indicated_policy_type is None


    def test__validate__a_path_for_another_script_type_on_the_other_network_is_nonstandard(self):
        """
        A path that would be standard only with both a different network and a
        different policy type is nonstandard.
        """
        result = validate("m/49h/1h/0h/0/5", "p2wpkh", SettingsConstants.MAINNET)
        assert result.status == NONSTANDARD
        assert result.offending_level_index == 0

        result = validate("m/48h/0h/0h/1h/0/5", "p2wsh", SettingsConstants.TESTNET)
        assert result.status == NONSTANDARD
        assert result.offending_level_index == 1


    def test__validate__refuses_an_unknown_purpose_or_coin_type(self):
        """
        A purpose with no registry entry is nonstandard, as is a coin type that is
        neither 0h nor 1h (or isn't hardened).
        """
        for derivation_path, offending_level_index in [
                ("m/85h/0h/0h/0/5", 0),
                ("m/84/0h/0h/0/5", 0),
                ("m/84h/2h/0h/0/5", 1),
                ("m/84h/0/0h/0/5", 1),
                ("m/48h/2h/0h/2h/0/5", 1),
                ("m/48h/0h/0h/3h/0/5", 3)]:
            policy_type = "p2wsh" if derivation_path.startswith("m/48h") else "p2wpkh"
            result = validate(derivation_path, policy_type)
            assert result.status == NONSTANDARD, derivation_path
            assert result.offending_level_index == offending_level_index, derivation_path


    def test__validate__accepts_bare_m45h_for_legacy_multisig_only(self):
        """
        Bare m/45h puts the "branch" and "address_index" directly beneath the purpose.
        It is standard for legacy multisig only. Inputs of other policy types at a bare
        m/45h path report it as another script type, at the purpose.
        """
        for network, coin_type, other_coin_type in NETWORKS:
            for derivation_path, branch in [("m/45h/0/5", 0), ("m/45h/1/5", 1)]:
                result = validate(derivation_path, "p2sh", network)
                assert result.status == STANDARD
                assert result.base_path == parse_path("m/45h")
                assert result.branch == branch
                assert result.address_index == 5

                for policy_type in ["p2wsh", "p2sh-p2wsh", "p2wpkh"]:
                    result = validate(derivation_path, policy_type, network)
                    assert result.status == ANOTHER_SCRIPT_TYPE, policy_type
                    assert result.indicated_policy_type == "p2sh"
                    assert result.offending_level_index == 0


    def test__validate__refuses_bare_m45h_paths_off_the_receive_or_change_branch(self):
        """
        Bare m/45h follows the same "branch" and "address_index" rules as every other
        base path.

        A hardened "branch" that equals the network's coin type also begins Caravan's
        layout, which matches one level more. So it is reported where Caravan's layout
        stops matching: the next level, which Caravan expects to be a hardened account.
        """
        # (path, offending level on mainnet, offending level on testnet and regtest)
        cases = [
            ("m/45h/2/5", 1, 1),
            ("m/45h/0/5h", 2, 2),
            ("m/45h/1/0h", 2, 2),
            ("m/45h/0h/5", 2, 1),
            ("m/45h/1h/5", 1, 2),
        ]
        for network, coin_type, other_coin_type in NETWORKS:
            for derivation_path, mainnet_offending_level_index, testnet_offending_level_index in cases:
                result = validate(derivation_path, "p2sh", network)
                assert result.status == NONSTANDARD, derivation_path

                if network == SettingsConstants.MAINNET:
                    assert result.offending_level_index == mainnet_offending_level_index, derivation_path
                else:
                    assert result.offending_level_index == testnet_offending_level_index, derivation_path


    def test__validate__legacy_multisig_has_no_cosigner_index_level(self):
        """
        A true BIP-45 path, with a cosigner index level between m/45h and the "branch",
        is nonstandard.
        """
        for network, coin_type, other_coin_type in NETWORKS:
            for derivation_path, offending_level_index in [
                    ("m/45h/0/0/5", 3),
                    ("m/45h/0/1/5", 3),
                    ("m/45h/2/1/5", 1)]:
                result = validate(derivation_path, "p2sh", network)
                assert result.status == NONSTANDARD, derivation_path
                assert result.offending_level_index == offending_level_index


    def test__validate__accepts_caravans_legacy_multisig_layout(self):
        """
        Caravan's legacy multisig base path is m/45h/coin_type/account, with an account
        from 0 through 9.
        """
        for derivation_path in ["m/45h/0h/0h/0/5", "m/45h/0h/0h/1/5", "m/45h/0h/9h/0/5"]:
            result = validate(derivation_path, "p2sh", SettingsConstants.MAINNET)
            assert result.status == STANDARD, derivation_path
            assert result.base_path == parse_path(derivation_path)[:3]

        for network in [SettingsConstants.TESTNET, SettingsConstants.REGTEST]:
            result = validate("m/45h/1h/0h/0/5", "p2sh", network)
            assert result.status == STANDARD
            assert result.base_path == parse_path("m/45h/1h/0h")
            assert result.branch == 0
            assert result.address_index == 5


    def test__validate__refuses_caravan_paths_outside_its_layout(self):
        """
        Caravan's layout follows the same rules as the other base paths with an account
        level. Each of these is nonstandard:
          * an account above 9, or one that isn't hardened
          * the Whirlpool accounts, which are for native segwit single sig only
          * "branch" 2
          * a hardened "address_index"
        """
        cases = [
            ("m/45h/{coin_type}/10h/0/5", 2),
            ("m/45h/{coin_type}/2147483644h/0/5", 2),
            ("m/45h/{coin_type}/2147483645h/0/5", 2),
            ("m/45h/{coin_type}/2147483646h/0/5", 2),
            ("m/45h/{coin_type}/0/0/5", 2),
            ("m/45h/{coin_type}/0h/2/5", 3),
            ("m/45h/{coin_type}/0h/0/5h", 4),
        ]
        for network, coin_type, other_coin_type in NETWORKS:
            for derivation_path, offending_level_index in cases:
                derivation_path = derivation_path.format(coin_type=coin_type)
                result = validate(derivation_path, "p2sh", network)
                assert result.status == NONSTANDARD, derivation_path
                assert result.offending_level_index == offending_level_index, derivation_path


    def test__validate__reports_a_caravan_path_from_the_other_network(self):
        """
        Caravan's layout has a coin type level, so a Caravan path with the other
        network's coin type is reported as another network.
        """
        for network, coin_type, other_coin_type in NETWORKS:
            expected_network = SettingsConstants.MAINNET if other_coin_type == "0h" else SettingsConstants.TESTNET

            result = validate(f"m/45h/{other_coin_type}/0h/0/5", "p2sh", network)
            assert result.status == ANOTHER_NETWORK
            assert result.offending_level_index == 1
            assert result.indicated_network == expected_network


    def test__validate__reports_a_caravan_path_as_legacy_multisig_for_other_policy_types(self):
        """
        Caravan's layout is standard for legacy multisig only. Inputs of other policy
        types at a Caravan path report it as another script type, at the purpose.
        """
        for network, coin_type, other_coin_type in NETWORKS:
            for policy_type in ["p2wsh", "p2sh-p2wsh", "p2wpkh"]:
                result = validate(f"m/45h/{coin_type}/0h/0/5", policy_type, network)
                assert result.status == ANOTHER_SCRIPT_TYPE, policy_type
                assert result.indicated_policy_type == "p2sh"
                assert result.offending_level_index == 0


    def test__validate__accepts_unchained_vault_paths_for_legacy_and_native_segwit_multisig(self):
        """
        Unchained derives each vault's key at m/45h/0/0/N, with a vault index N from 0
        through 9. Its legacy and native segwit vaults use the same keys, so the layout
        is standard for both. It has no coin type level, so it is the same on every
        network.

        Each vault is its own base path.
        """
        for network, coin_type, other_coin_type in NETWORKS:
            for policy_type in ["p2sh", "p2wsh"]:
                for derivation_path, vault_index, branch, address_index in [
                        ("m/45h/0/0/0/0/5", 0, 0, 5),
                        ("m/45h/0/0/9/1/5", 9, 1, 5),
                        ("m/45h/0/0/3/0/0", 3, 0, 0)]:
                    result = validate(derivation_path, policy_type, network)
                    assert result.status == STANDARD, derivation_path
                    assert result.base_path == parse_path(f"m/45h/0/0/{vault_index}")
                    assert result.branch == branch
                    assert result.address_index == address_index


    def test__validate__refuses_unchained_paths_outside_its_layout(self):
        """
        Each of these breaks Unchained's vault layout, so it is nonstandard.

        Legacy multisig has three layouts under m/45h, so its offending level is where
        the closest of them stops matching. That can differ from native segwit
        multisig, whose only layout under m/45h is Unchained's:
          * m/45h/1/0/0/0/5 reads as bare m/45h, then an extra level.
          * Unchained's other layout, m/45h/0h/account/N/{0,1}/i, reads as Caravan's
            layout, then an extra level.
        """
        # (path, offending level for legacy multisig, offending level for native segwit
        # multisig)
        cases = [
            ("m/45h/0/0/10/0/5", 3, 3),             # vault index above 9
            ("m/45h/0/0/0h/0/5", 3, 3),             # hardened vault index
            ("m/45h/1/0/0/0/5", 3, 1),              # nonzero second level
            ("m/45h/0/1/0/0/5", 3, 2),              # nonzero third level
            ("m/45h/0/0/0/2/5", 4, 4),              # "branch" 2
            ("m/45h/0/0/0/0/5h", 5, 5),             # hardened "address_index"
            ("m/45h/0/0/0/0/5/9", 6, 6),            # extra level
            ("m/45h/0/0/0/0", 4, 4),                # ends early
            ("m/45h/{coin_type}/0h/0/0/5", 5, 1),   # Unchained's other layout
        ]
        for network, coin_type, other_coin_type in NETWORKS:
            for derivation_path, p2sh_offending_level_index, p2wsh_offending_level_index in cases:
                derivation_path = derivation_path.format(coin_type=coin_type)

                result = validate(derivation_path, "p2sh", network)
                assert result.status == NONSTANDARD, derivation_path
                assert result.offending_level_index == p2sh_offending_level_index, derivation_path

                result = validate(derivation_path, "p2wsh", network)
                assert result.status == NONSTANDARD, derivation_path
                assert result.offending_level_index == p2wsh_offending_level_index, derivation_path


    def test__validate__an_unchained_vault_path_is_nonstandard_for_other_policy_types(self):
        """
        Unchained's vault layout is standard for both legacy and native segwit
        multisig, so for any other policy type there is no one script type to name. It
        is nonstandard, at the purpose.
        """
        for network, coin_type, other_coin_type in NETWORKS:
            for policy_type in ["p2sh-p2wsh", "p2wpkh", "p2sh-p2wpkh", "p2pkh", "p2tr"]:
                result = validate("m/45h/0/0/0/0/5", policy_type, network)
                assert result.status == NONSTANDARD, policy_type
                assert result.offending_level_index == 0
                assert result.indicated_policy_type is None


    def test__validate__a_native_segwit_multisig_path_at_m45h_highlights_the_closest_layout(self):
        """
        For native segwit multisig, Unchained's layout begins with m/45h, so a broken
        m/45h path is reported where that layout stops matching, not at the purpose.
        """
        for derivation_path, offending_level_index in [
                ("m/45h/0h/5", 1),
                ("m/45h/0h/0h/7777/0/5", 1),
                ("m/45h/0/0/5", 3)]:
            result = validate(derivation_path, "p2wsh")
            assert result.status == NONSTANDARD, derivation_path
            assert result.offending_level_index == offending_level_index, derivation_path


    def test__validate__electrum_seed_paths_are_nonstandard(self):
        """
        Electrum seeds derive at m/0h, which has no registry entry.
        """
        for derivation_path in ["m/0h/0/5", "m/0h/1/5"]:
            result = validate(derivation_path, "p2wpkh")
            assert result.status == NONSTANDARD
            assert result.offending_level_index == 0


    def test__validate__the_empty_path_is_nonstandard(self):
        """
        The empty path is the master key itself. It is nonstandard, with no level to
        point at.
        """
        result = DerivationPathValidator().validate([], "p2wpkh", SettingsConstants.MAINNET)
        assert result.status == NONSTANDARD
        assert result.offending_level_index is None


    def test__validate__follows_its_own_accounts_and_registry(self):
        """
        A validator built with different allowed accounts or a different registry judges
        paths by those instead of the standard ones.
        """
        # More accounts for one policy type. A policy type left out allows no account.
        validator = DerivationPathValidator(allowed_accounts={"p2wpkh": range(20)})
        assert validate("m/84h/0h/15h/0/5", "p2wpkh", validator=validator).status == STANDARD
        assert validate("m/84h/0h/2147483646h/0/5", "p2wpkh", validator=validator).status == NONSTANDARD

        result = validate("m/86h/0h/0h/0/5", "p2tr", validator=validator)
        assert result.status == NONSTANDARD
        assert result.offending_level_index == ACCOUNT_LEVEL_INDEX

        # A registry with native segwit single sig only. Nested segwit's path is no longer
        # another script type, and a policy type with no entry is nonstandard from its
        # purpose on.
        validator = DerivationPathValidator(
            registry={"p2wpkh": DerivationPathValidator.STANDARD_REGISTRY["p2wpkh"]},
        )
        assert validate("m/84h/0h/0h/0/5", "p2wpkh", validator=validator).status == STANDARD

        result = validate("m/49h/0h/0h/0/5", "p2wpkh", validator=validator)
        assert result.status == NONSTANDARD
        assert result.offending_level_index == 0

        result = validate("m/86h/0h/0h/0/5", "p2tr", validator=validator)
        assert result.status == NONSTANDARD
        assert result.offending_level_index == 0

        # But a policy type with no entry can still be told that its path is standard for
        # a policy type that has one.
        result = validate("m/84h/0h/0h/0/5", "p2tr", validator=validator)
        assert result.status == ANOTHER_SCRIPT_TYPE
        assert result.indicated_policy_type == "p2wpkh"


    def test__validate__raises_for_an_unknown_network(self):
        with pytest.raises(ValueError):
            validate("m/84h/0h/0h/0/5", "p2wpkh", network="X")


    def test__build_base_path__fills_in_the_coin_type_and_account(self):
        """
        build_base_path() returns each policy type's primary base path: bare m/45h for
        legacy multisig and BIP-48 for native segwit multisig, never their other layouts.
        """
        validator = DerivationPathValidator()
        for network, coin_type, other_coin_type in NETWORKS:
            for policy_type in BASE_PATHS:
                assert validator.build_base_path(policy_type, network) == parse_path(base_path(policy_type, coin_type))
                assert validator.build_base_path(policy_type, network, account=3) == parse_path(base_path(policy_type, coin_type, "3h"))

        # The network is checked even for a base path that has no coin type level
        with pytest.raises(ValueError):
            validator.build_base_path("p2sh", "X")


    def test__build_base_path__raises_for_an_account_that_cant_be_hardened(self):
        """
        An account has to be 0 through 2^31 - 1 to make a hardened level. Anything else
        raises ValueError, even for a base path with no account level.
        """
        validator = DerivationPathValidator()
        assert validator.build_base_path("p2wpkh", SettingsConstants.MAINNET, account=2**31 - 1)[ACCOUNT_LEVEL_INDEX] == 2**32 - 1

        for account in (-1, 2**31):
            for policy_type in ("p2wpkh", "p2sh"):
                with pytest.raises(ValueError):
                    validator.build_base_path(policy_type, SettingsConstants.MAINNET, account=account)
