import pytest
from binascii import a2b_base64
from hypothesis import given, settings, HealthCheck
from hypothesis import strategies as st
from embit.psbt import PSBT

from seedsigner.models.psbt_parser import PSBTParser
from seedsigner.models.settings_definition import SettingsConstants

from psbt_testing_util import PSBTTestData, create_output


# Fixed seed — same as existing tests
SEED = PSBTTestData.seed

SINGLESIG_INPUTS = st.sampled_from([
    PSBTTestData.SINGLE_SIG_NATIVE_SEGWIT_1_INPUT,
    PSBTTestData.SINGLE_SIG_NESTED_SEGWIT_1_INPUT,
    PSBTTestData.SINGLE_SIG_TAPROOT_1_INPUT,
    PSBTTestData.SINGLE_SIG_LEGACY_P2PKH_1_INPUT,
])

SINGLESIG_CHANGE = st.sampled_from([
    PSBTTestData.SINGLE_SIG_NATIVE_SEGWIT_CHANGE,
    PSBTTestData.SINGLE_SIG_NESTED_SEGWIT_CHANGE,
    PSBTTestData.SINGLE_SIG_TAPROOT_CHANGE,
    PSBTTestData.SINGLE_SIG_LEGACY_P2PKH_CHANGE,
])

EXTERNAL_OUTPUTS = st.sampled_from(PSBTTestData.ALL_EXTERNAL_OUTPUTS)


@settings(suppress_health_check=[], max_examples=10)
@given(input_b64=SINGLESIG_INPUTS)
def test_existing_fixtures_pass_hypothesis_health_checks(input_b64):
    """
    Expected Outcome #1: Existing PSBT fixtures pass Hypothesis health checks
    with zero failures. No health checks are suppressed here intentionally.
    """
    psbt: PSBT = PSBT.parse(a2b_base64(input_b64))
    input_amount = sum(inp.utxo.value for inp in psbt.inputs)
    assert input_amount > 0


@given(
    input_b64=SINGLESIG_INPUTS,
    change_hex=SINGLESIG_CHANGE,
    recipient_hex=EXTERNAL_OUTPUTS,
    fee=st.integers(min_value=1_000, max_value=50_000),
)
@settings(suppress_health_check=[HealthCheck.too_slow], max_examples=50)
def test_singlesig_conservation_of_value(input_b64, change_hex, recipient_hex, fee):
    """
    Expected Outcome #3: Property: spend + change + fee == input_amount
    for any valid combination of single-sig input, change output, and recipient.
    Covers p2wpkh, p2sh-p2wpkh, p2tr, p2pkh.
    """
    psbt: PSBT = PSBT.parse(a2b_base64(input_b64))
    input_amount = sum(inp.utxo.value for inp in psbt.inputs)

    if fee >= input_amount - 1_000:
        return

    recipient_amount = (input_amount - fee) // 2
    change_amount = input_amount - recipient_amount - fee

    psbt.outputs.clear()
    psbt.outputs.append(create_output(recipient_hex, recipient_amount))
    psbt.outputs.append(create_output(change_hex, change_amount))

    parser = PSBTParser(p=psbt, seed=SEED, network=SettingsConstants.REGTEST)

    assert parser.input_amount == parser.spend_amount + parser.change_amount + parser.fee_amount