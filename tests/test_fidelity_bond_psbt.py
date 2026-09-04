import pytest
from embit import bip32, ec, psbt, script, transaction
from embit.networks import NETWORKS
from embit.transaction import SIGHASH

from seedsigner.helpers import fidelity_bonds
from seedsigner.models.psbt_parser import (
    PSBTInputOwnershipClaimError,
    PSBTParser,
    PSBTSeedCannotSignError,
)
from seedsigner.models.seed import Seed
from seedsigner.models.settings_definition import SettingsConstants


MNEMONIC = "abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon about"


def make_bond_psbt(index=0, network=SettingsConstants.MAINNET):
    seed = Seed(MNEMONIC.split())
    embit_network = SettingsConstants.map_network_to_embit(network)
    root = bip32.HDKey.from_seed(seed.seed_bytes, version=NETWORKS[embit_network]["xprv"])
    path = bip32.parse_path(fidelity_bonds.derivation_path(index, network))
    pubkey = root.derive(path).to_public().key
    witness_script = fidelity_bonds.witness_script(
        fidelity_bonds.index_to_locktime(index),
        pubkey,
    )
    coin_type = 0 if network == SettingsConstants.MAINNET else 1
    destination = script.p2wpkh(root.derive(f"m/84'/{coin_type}'/0'/0/0").key)
    tx = transaction.Transaction(
        vin=[transaction.TransactionInput(b"\x11" * 32, 0, sequence=0xFFFFFFFE)],
        vout=[transaction.TransactionOutput(99_000, destination)],
        locktime=fidelity_bonds.index_to_locktime(index),
    )
    bond_psbt = psbt.PSBT(tx)
    bond_input = bond_psbt.inputs[0]
    bond_input.witness_utxo = transaction.TransactionOutput(
        100_000, script.p2wsh(witness_script)
    )
    bond_input.witness_script = witness_script
    bond_input.sighash_type = SIGHASH.ALL
    bond_input.bip32_derivations[pubkey] = psbt.DerivationPath(
        root.my_fingerprint, path
    )
    return seed, bond_psbt, pubkey


def test_parse_sign_and_trim_fidelity_bond_psbt():
    seed, bond_psbt, pubkey = make_bond_psbt()
    parser = PSBTParser(bond_psbt, seed, SettingsConstants.MAINNET)

    assert parser.policy["fidelity_bond"] is True
    assert parser.policy["locktime"] == 1577836800
    assert parser.input_amount == 100_000
    assert parser.spend_amount == 99_000
    assert parser.fee_amount == 1_000
    assert PSBTParser.has_matching_input_fingerprint(bond_psbt, seed)

    assert bond_psbt.sign_with(parser.root) == 1
    signature = bond_psbt.inputs[0].partial_sigs[pubkey]
    sighash = bond_psbt.sighash(0, sighash=SIGHASH.ALL)
    assert signature[-1] == SIGHASH.ALL
    assert pubkey.verify(ec.Signature.parse(signature[:-1]), sighash)

    trimmed = PSBTParser.trim(bond_psbt)
    serialized = psbt.PSBT.parse(trimmed.serialize())
    trimmed_input = serialized.inputs[0]
    assert trimmed_input.witness_utxo == bond_psbt.inputs[0].witness_utxo
    assert trimmed_input.witness_script == bond_psbt.inputs[0].witness_script
    assert trimmed_input.sighash_type == SIGHASH.ALL
    assert trimmed_input.partial_sigs[pubkey] == signature


def test_parse_signet_fidelity_bond_psbt():
    seed, bond_psbt, _ = make_bond_psbt(network=SettingsConstants.SIGNET)
    parser = PSBTParser(bond_psbt, seed, SettingsConstants.SIGNET)

    assert parser.policy["fidelity_bond"] is True
    assert parser.policy["locktime"] == 1577836800


def test_rejects_missing_witness_utxo():
    seed, bond_psbt, _ = make_bond_psbt()
    bond_psbt.inputs[0].witness_utxo = None
    with pytest.raises(ValueError, match="witness UTXO"):
        PSBTParser(bond_psbt, seed, SettingsConstants.MAINNET)


def test_rejects_wrong_witness_script_commitment():
    seed, bond_psbt, _ = make_bond_psbt()
    bond_psbt.inputs[0].witness_utxo.script_pubkey = script.p2wsh(
        script.Script(b"wrong")
    )
    with pytest.raises(ValueError, match="does not match the UTXO"):
        PSBTParser(bond_psbt, seed, SettingsConstants.MAINNET)


def test_rejects_non_all_sighash():
    seed, bond_psbt, _ = make_bond_psbt()
    bond_psbt.inputs[0].sighash_type = SIGHASH.NONE
    with pytest.raises(ValueError, match="SIGHASH_ALL"):
        PSBTParser(bond_psbt, seed, SettingsConstants.MAINNET)


def test_rejects_early_transaction_locktime():
    seed, bond_psbt, _ = make_bond_psbt()
    bond_psbt.locktime -= 1
    with pytest.raises(ValueError, match="locktime is too early"):
        PSBTParser(bond_psbt, seed, SettingsConstants.MAINNET)


def test_rejects_final_input_sequence():
    seed, bond_psbt, _ = make_bond_psbt()
    bond_psbt.inputs[0].sequence = 0xFFFFFFFF
    with pytest.raises(ValueError, match="sequence is final"):
        PSBTParser(bond_psbt, seed, SettingsConstants.MAINNET)


def test_rejects_non_bip46_derivation():
    seed, bond_psbt, pubkey = make_bond_psbt()
    derivation = bond_psbt.inputs[0].bip32_derivations.pop(pubkey)
    derivation.derivation = bip32.parse_path("m/84'/0'/0'/0/0")
    bond_psbt.inputs[0].bip32_derivations[pubkey] = derivation
    with pytest.raises(PSBTInputOwnershipClaimError):
        PSBTParser(bond_psbt, seed, SettingsConstants.MAINNET)


def test_rejects_wrong_fingerprint():
    seed, bond_psbt, pubkey = make_bond_psbt()
    derivation = bond_psbt.inputs[0].bip32_derivations[pubkey]
    bond_psbt.inputs[0].bip32_derivations[pubkey] = psbt.DerivationPath(
        b"\x12\x34\x56\x78",
        derivation.derivation,
    )
    with pytest.raises(PSBTSeedCannotSignError):
        PSBTParser(bond_psbt, seed, SettingsConstants.MAINNET)


def test_rejects_multiple_redemption_outputs():
    seed, bond_psbt, _ = make_bond_psbt()
    bond_psbt.outputs.append(
        psbt.OutputScope(vout=transaction.TransactionOutput(0, script.Script(b"\x6a")))
    )
    with pytest.raises(ValueError, match="one input and one output"):
        PSBTParser(bond_psbt, seed, SettingsConstants.MAINNET)
