"""
Property based tests for embit_utils using Hypothesis.

Round-trip property:
    parse_derivation_path(get_standard_derivation_path(network, SINGLE_SIG, script_type))
    must always return the original network and script_type without raising.

Also pins the documented limitation: multisig paths (purpose=48h) raise NotImplementedError.
"""
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from seedsigner.helpers import embit_utils
from seedsigner.models.settings_definition import SettingsConstants as SC


SINGLE_SIG_SCRIPT_TYPES = [SC.NATIVE_SEGWIT, SC.NESTED_SEGWIT, SC.TAPROOT, SC.LEGACY_P2PKH]
NETWORKS = [SC.MAINNET, SC.TESTNET, SC.REGTEST]


@given(
    network=st.sampled_from(NETWORKS),
    script_type=st.sampled_from(SINGLE_SIG_SCRIPT_TYPES),
)
@settings(max_examples=50)
def test_parse_roundtrip_singlesig_standard_paths(network, script_type):
    """
    parse_derivation_path(get_standard_derivation_path(...)) must return the
    original script_type and network for all single sig combinations.
    Paths from get_standard_derivation_path have no trailing change/index,
    so clean_match is False. But script_type and network must still be correct.
    """
    path = embit_utils.get_standard_derivation_path(network, SC.SINGLE_SIG, script_type)
    result = embit_utils.parse_derivation_path(path)

    assert result["script_type"] == script_type

    if network == SC.MAINNET:
        assert result["network"] == SC.MAINNET
    else:
        # TESTNET and REGTEST both map to coin_type=1, parser returns both
        assert network in result["network"]

    # Standard paths without trailing change/index cannot be a clean_match
    assert result["clean_match"] is False
    assert result["is_change"] is None
    assert result["index"] is None


def test_parse_derivation_path_multisig_raises():
    """
    Pins the documented limitation: parse_derivation_path raises for multisig
    paths (purpose=48h). This is noted in the function docstring.
    If this ever gets implemented, this test should be updated accordingly.
    """
    multisig_paths = [
        embit_utils.get_standard_derivation_path(SC.MAINNET, SC.MULTISIG, SC.NATIVE_SEGWIT),
        embit_utils.get_standard_derivation_path(SC.MAINNET, SC.MULTISIG, SC.NESTED_SEGWIT),
        embit_utils.get_standard_derivation_path(SC.TESTNET, SC.MULTISIG, SC.NATIVE_SEGWIT),
    ]
    for path in multisig_paths:
        with pytest.raises(Exception, match="Not implemented"):
            embit_utils.parse_derivation_path(path)
