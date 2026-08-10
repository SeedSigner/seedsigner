from binascii import unhexlify

from embit import bip32, ec, script
from embit.psbt import DerivationPath
from embit.silent_payments import SilentPaymentsPSBT, SilentPaymentData, sp
from embit.silent_payments.psbt import SPInputScope, SPOutputScope
from embit.transaction import Transaction, TransactionInput, TransactionOutput

from seedsigner.models.seed import Seed

# Recipient SP keys borrowed from embit's BIP-375 test vectors.
SCAN_HEX = "027a487fc19fb769877b8742d6ea18118f3c4e72b1ea8c6de602a7ad4a41dbe068"
SPEND_HEX = "0361e1b1e9de5e42cb2007f7ca54b9e0d57ed13938fad56d3f19e57513a8fce039"
SCAN_PUB = ec.PublicKey.parse(unhexlify(SCAN_HEX))
SPEND_PUB = ec.PublicKey.parse(unhexlify(SPEND_HEX))

# A fixed, valid external destination pubkey (not owned by any test seed).
EXTERNAL_PUB = ec.PrivateKey(bytes([0x09] * 32)).get_public_key()


def _root(seed: Seed) -> bip32.HDKey:
    # Mainnet master key; matches PSBTParser._set_root for SettingsConstants.MAINNET.
    return bip32.HDKey.from_seed(seed.seed_bytes)


def _sp_input(script_pubkey, value: int, txid_byte: int) -> SPInputScope:
    inp = SPInputScope()
    inp.txid = bytes([txid_byte] * 32)
    inp.vout = 0
    inp.sequence = 0xFFFFFFFE
    inp.witness_utxo = TransactionOutput(value=value, script_pubkey=script_pubkey)
    return inp


def _sp_output(value: int, script_pubkey=None, sp_data=None) -> SPOutputScope:
    out = SPOutputScope()
    out.value = value
    out.script_pubkey = script_pubkey
    out.sp_data = sp_data
    return out


def build_sp_send_psbt(seed: Seed, value: int = 100_000, output_script_resolved: bool = False):
    """PSBTv2: one P2WPKH input owned by `seed`, one SP output (paying to an
    sp address). Signing contributes ECDH shares + DLEQ proofs (BIP-375).

    A real coordinator hands the signer an *unresolved* SP output (only sp_data; no
    PSBT_OUT_SCRIPT) — the script is derived from the inputs' ECDH shares at signing
    time; the default models that realistic arrival state. Pass
    ``output_script_resolved=True`` for a placeholder p2tr script instead -- embit now
    verifies any declared PSBT_OUT_SCRIPT against the derivation at signing time, so
    the placeholder only parses cleanly, it does not sign cleanly."""
    root = _root(seed)
    # Simplified fixture path [0, 0]; real BIP-352 spend derivation is m/352h/0h/0h/0/0.
    # The signer follows whatever derivation the PSBT carries, so [0,0] is sufficient here.
    pub = root.derive([0, 0]).get_public_key()

    psbt = SilentPaymentsPSBT.create_v2()

    inp = _sp_input(script.p2wpkh(pub), value, 0xAA)
    inp.bip32_derivations[pub] = DerivationPath(root.my_fingerprint, [0, 0])
    psbt.add_input(inp)

    # None models a real coordinator's unresolved SP output (script derived at
    # signing time); the placeholder is only for tests that need a resolved
    # PSBT_OUT_SCRIPT without actually signing.
    placeholder = script.Script(b"\x51\x20" + bytes(32)) if output_script_resolved else None
    psbt.add_output(_sp_output(value - 1_000, placeholder, SilentPaymentData(SCAN_PUB, SPEND_PUB)))

    return psbt


def build_sp_send_psbt_ineligible_input(value: int = 100_000):
    """PSBTv2: one SP output but a bare P2WSH multisig input -- not one of the
    BIP-352-eligible types (P2PKH, P2WPKH, P2SH-P2WPKH, P2TR). No derivation info is
    attached since this PSBT is never meant to be signed; it only exercises routing
    when SP input eligibility is checked before a full PSBT review."""
    psbt = SilentPaymentsPSBT.create_v2()

    redeem_script = script.Script(bytes([0x51, 0x21]) + bytes(33) + bytes([0x51, 0xae]))
    psbt.add_input(_sp_input(script.p2wsh(redeem_script), value, 0xAA))

    psbt.add_output(_sp_output(value - 1_000, None, SilentPaymentData(SCAN_PUB, SPEND_PUB)))

    return psbt


def build_sp_send_psbt_realistic(seed: Seed, value: int = 100_000,
                                  output_script_resolved: bool = False):
    """Sparrow-realistic PSBTv2: BIP-84 derivation (m/84'/0'/0'/0/0), includes
    both non_witness_utxo and witness_utxo, a change P2WPKH output, and
    sighash_type set to SIGHASH_ALL (0x01)."""
    root = _root(seed)
    deriv_path = [0x80000054, 0x80000000, 0x80000000, 0, 0]
    pub = root.derive(deriv_path).get_public_key()

    change_deriv = [0x80000054, 0x80000000, 0x80000000, 1, 0]
    change_pub = root.derive(change_deriv).get_public_key()

    psbt = SilentPaymentsPSBT.create_v2()

    inp = _sp_input(script.p2wpkh(pub), value, 0xCC)
    inp.bip32_derivations[pub] = DerivationPath(root.my_fingerprint, deriv_path)
    inp.sighash_type = 0x01  # SIGHASH_ALL
    inp.non_witness_utxo = Transaction(
        version=2,
        locktime=0,
        vin=[TransactionInput(bytes([0x00] * 32), 0)],
        vout=[TransactionOutput(value=value, script_pubkey=script.p2wpkh(pub))]
    )
    psbt.add_input(inp)

    placeholder = script.Script(b"\x51\x20" + bytes(32)) if output_script_resolved else None
    psbt.add_output(_sp_output(value - 5_000, placeholder, SilentPaymentData(SCAN_PUB, SPEND_PUB)))

    change_out = _sp_output(4_000, script.p2wpkh(change_pub))
    change_out.bip32_derivations[change_pub] = DerivationPath(root.my_fingerprint, change_deriv)
    psbt.add_output(change_out)

    return psbt


def build_sp_change_psbt(seed: Seed, value: int = 100_000):
    """Sparrow-style "external recipient + SP change": seed-owned P2WPKH input, an
    external P2WPKH recipient, and an SP output back to the seed's *own* SP address
    (m=0 change label). The SP output should land as change, not a recipient."""
    root = _root(seed)
    deriv_path = [0x80000054, 0x80000000, 0x80000000, 0, 0]
    pub = root.derive(deriv_path).get_public_key()

    # The seed's own BIP-352 keys, and the m=0 (change) label-tweaked spend key.
    scan_priv, spend_pub = seed.get_bip352_scan_spend_keys()
    change_spend = sp.apply_label(spend_pub, scan_priv, 0)

    psbt = SilentPaymentsPSBT.create_v2()

    inp = _sp_input(script.p2wpkh(pub), value, 0xDE)
    inp.bip32_derivations[pub] = DerivationPath(root.my_fingerprint, deriv_path)
    psbt.add_input(inp)

    # External recipient (ordinary address, not owned by the seed).
    psbt.add_output(_sp_output(value - 10_000, script.p2wpkh(EXTERNAL_PUB)))

    # SP change back to the seed's own SP address (m=0 change label).
    change = _sp_output(9_000, None, SilentPaymentData(scan_priv.get_public_key(), change_spend))
    change.sp_label = 0  # m=0 is reserved for change; classify_sp_output reads this.
    psbt.add_output(change)

    return psbt


def build_sp_send_psbt_taproot_input(seed: Seed, value: int = 100_000):
    """PSBTv2: one seed-owned BIP-86-style P2TR input, one SP output.
    The combination that regressed in krux: embit finalizes taproot key-path
    inputs at signing time, but a BIP-375 Signer must export unfinalized.
    No sighash_type is set (taproot signs with SIGHASH.DEFAULT)."""
    root = _root(seed)
    # Simplified fixture path [0, 0]; see build_sp_send_psbt.
    pub = root.derive([0, 0]).get_public_key()

    psbt = SilentPaymentsPSBT.create_v2()

    inp = _sp_input(script.p2tr(pub), value, 0xAB)
    inp.taproot_bip32_derivations[pub] = ([], DerivationPath(root.my_fingerprint, [0, 0]))
    psbt.add_input(inp)

    psbt.add_output(_sp_output(value - 1_000, None, SilentPaymentData(SCAN_PUB, SPEND_PUB)))

    return psbt


def build_sp_spend_psbt(seed: Seed, tweak: bytes = bytes([0x11] * 32),
                        value: int = 100_000):
    """PSBTv2: one P2TR input that is a *received* SP output (carries sp_tweak +
    sp_spend_bip32_derivations), one ordinary external P2WPKH destination.
    Signing produces a taproot key signature (BIP-376). No SP outputs => pure-spend."""
    root = _root(seed)
    # Simplified fixture path [0, 0]; see build_sp_send_psbt.
    child = root.derive([0, 0])
    spend_pub = child.get_public_key()
    output_xonly = child.key.sp_spend_tweak(tweak).xonly()

    psbt = SilentPaymentsPSBT.create_v2()

    inp = _sp_input(script.Script(b"\x51\x20" + output_xonly), value, 0xCD)
    inp.sp_tweak = tweak
    inp.sp_spend_bip32_derivations[spend_pub.sec()] = DerivationPath(root.my_fingerprint, [0, 0])
    psbt.add_input(inp)

    psbt.add_output(_sp_output(value - 5_000, script.p2wpkh(EXTERNAL_PUB)))

    return psbt
