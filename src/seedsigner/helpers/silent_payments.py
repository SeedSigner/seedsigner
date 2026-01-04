"""
BIP-352 Silent Payments - Send Verification Support

This module implements verification for the sending side of BIP-352 Silent Payments.


WHAT HAPPENS TODAY (WITHOUT THIS UPDATE)
========================================
Silent Payments already work with SeedSigner - the coordinator wallet does the math:

1. BlueWallet/Sparrow derives bc1p... from the sp1... address
2. Coordinator builds PSBT with that Taproot output
3. User scans PSBT into SeedSigner
4. SeedSigner shows: "Sending 0.01 BTC to bc1p7x9y2z..."
5. User thinks: "I have no idea if that bc1p address is correct"
6. User approves blindly, SeedSigner signs

The payment works fine. But the user has NO WAY to verify the bc1p... address
actually corresponds to their intended sp1... recipient.


THE RISK
========
A malicious or buggy coordinator could substitute a different bc1p... address:
- Compromised wallet software
- Man-in-the-middle attack modifying the PSBT
- Bug in the SP derivation code

The user would unknowingly sign a transaction sending funds to the wrong address.


WHAT THIS UPDATE ADDS
=====================
SeedSigner can now VERIFY the coordinator did the math correctly:

1. User scans sp1... address QR first (their source of truth)
2. Coordinator builds PSBT as normal
3. User scans PSBT into SeedSigner
4. SeedSigner independently re-derives what the output SHOULD be
5. SeedSigner verifies the PSBT output matches
6. SeedSigner shows: "Sending 0.01 BTC to sp1qq..." with verification checkmark
7. User thinks: "That's the address I intended to pay"
8. User approves with confidence, SeedSigner signs


WHY SEEDSIGNER CAN ONLY VERIFY, NOT GENERATE SP ADDRESSES
==========================================================
Unlike regular Bitcoin addresses (where m/84'/0'/0'/0/0 always produces the same
bc1q... address), Silent Payment output addresses are TRANSACTION-SPECIFIC.

The derived bc1p... address depends on:
1. The private keys of the UTXOs being spent
2. The outpoints (txid:vout) of those specific UTXOs

This means:
- Every transaction to the same sp1... address produces a DIFFERENT bc1p... output
- You cannot derive the output address until you know WHICH UTXOs you're spending
- Only a wallet with UTXO set knowledge can build the transaction

SeedSigner is stateless by design - it has:
- Your seed (private keys) ✓
- No blockchain data ✗
- No wallet state ✗
- No UTXO set ✗

Therefore the flow MUST be:
1. Coordinator wallet (with UTXO knowledge) selects inputs, derives SP output, builds PSBT
2. SeedSigner (with private keys) verifies the derivation was correct, then signs


Reference: https://github.com/bitcoin/bips/blob/master/bip-0352.mediawiki
"""

import logging
from hashlib import sha256
from typing import Tuple, List, Optional

from embit import ec
from embit.util import secp256k1

logger = logging.getLogger(__name__)


# Bech32m constants
BECH32M_CONST = 0x2bc830a3
CHARSET = "qpzry9x8gf2tvdw0s3jn54khce6mua7l"

# secp256k1 curve order
SECP256K1_ORDER = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141


def _bech32_polymod(values: List[int]) -> int:
    """Internal function for Bech32 checksum calculation."""
    GEN = [0x3b6a57b2, 0x26508e6d, 0x1ea119fa, 0x3d4233dd, 0x2a1462b3]
    chk = 1
    for v in values:
        top = chk >> 25
        chk = (chk & 0x1ffffff) << 5 ^ v
        for i in range(5):
            chk ^= GEN[i] if ((top >> i) & 1) else 0
    return chk


def _bech32_hrp_expand(hrp: str) -> List[int]:
    """Expand HRP for checksum calculation."""
    return [ord(x) >> 5 for x in hrp] + [0] + [ord(x) & 31 for x in hrp]


def _bech32m_verify_checksum(hrp: str, data: List[int]) -> bool:
    """Verify Bech32m checksum."""
    return _bech32_polymod(_bech32_hrp_expand(hrp) + data) == BECH32M_CONST


def _convertbits(data: List[int], frombits: int, tobits: int, pad: bool = True) -> Optional[List[int]]:
    """General power-of-2 base conversion."""
    acc = 0
    bits = 0
    ret = []
    maxv = (1 << tobits) - 1
    max_acc = (1 << (frombits + tobits - 1)) - 1
    for value in data:
        if value < 0 or (value >> frombits):
            return None
        acc = ((acc << frombits) | value) & max_acc
        bits += frombits
        while bits >= tobits:
            bits -= tobits
            ret.append((acc >> bits) & maxv)
    if pad:
        if bits:
            ret.append((acc << (tobits - bits)) & maxv)
    elif bits >= frombits or ((acc << (tobits - bits)) & maxv):
        return None
    return ret


def bech32m_decode(bech: str) -> Tuple[str, bytes]:
    """
    Decode a Bech32m string (SP address) into HRP and data.

    Args:
        bech: The Bech32m encoded string

    Returns:
        Tuple of (hrp, data_bytes)

    Raises:
        ValueError: If the address is invalid
    """
    bech = bech.lower()

    # Find separator
    pos = bech.rfind('1')
    if pos < 1 or pos + 7 > len(bech):
        raise ValueError("Invalid separator position")

    hrp = bech[:pos]
    data_part = bech[pos + 1:]

    # Decode data characters
    data = []
    for c in data_part:
        if c not in CHARSET:
            raise ValueError(f"Invalid character: {c}")
        data.append(CHARSET.index(c))

    # Verify checksum
    if not _bech32m_verify_checksum(hrp, data):
        raise ValueError("Invalid checksum")

    # Remove checksum (last 6 characters) and convert from 5-bit to 8-bit
    data = data[:-6]

    # First element is the witness version
    if len(data) == 0:
        raise ValueError("Empty data")

    version = data[0]

    # Convert remaining 5-bit groups to bytes
    decoded = _convertbits(data[1:], 5, 8, False)
    if decoded is None:
        raise ValueError("Invalid padding")

    return hrp, bytes([version] + decoded)


def parse_silent_payment_address(address: str) -> Tuple[bytes, bytes, str]:
    """
    Parse a BIP-352 Silent Payment address.

    Args:
        address: The SP address string (sp1... or tsp1...)

    Returns:
        Tuple of (B_scan, B_spend, network) where:
        - B_scan: 33-byte compressed public key for scanning
        - B_spend: 33-byte compressed public key for spending
        - network: "mainnet" or "testnet"

    Raises:
        ValueError: If address is invalid
    """
    hrp, data = bech32m_decode(address)

    if hrp == "sp":
        network = "mainnet"
    elif hrp == "tsp":
        network = "testnet"
    else:
        raise ValueError(f"Invalid HRP for SP address: {hrp}")

    # First byte is version (should be 0 for v0 SP addresses)
    if len(data) < 1:
        raise ValueError("Missing version byte")

    version = data[0]
    if version != 0:
        raise ValueError(f"Unsupported SP address version: {version}")

    payload = data[1:]

    if len(payload) != 66:
        raise ValueError(f"Invalid SP address data length: {len(payload)}, expected 66")

    B_scan = payload[:33]
    B_spend = payload[33:66]

    # Validate that both are valid compressed public keys
    if B_scan[0] not in (0x02, 0x03) or B_spend[0] not in (0x02, 0x03):
        raise ValueError("Invalid public key prefix in SP address")

    return bytes(B_scan), bytes(B_spend), network


def tagged_hash(tag: str, data: bytes) -> bytes:
    """
    Create a BIP-340 style tagged hash.

    tagged_hash(tag, data) = SHA256(SHA256(tag) || SHA256(tag) || data)

    Args:
        tag: The tag string (e.g., "BIP0352/Inputs")
        data: The data to hash

    Returns:
        32-byte hash
    """
    tag_hash = sha256(tag.encode()).digest()
    return sha256(tag_hash + tag_hash + data).digest()


def get_input_hash(smallest_outpoint: bytes, sum_input_pubkeys: bytes) -> bytes:
    """
    Calculate the input_hash per BIP-352.

    input_hash = hash_BIP0352/Inputs(smallest_outpoint || A)

    Args:
        smallest_outpoint: The lexicographically smallest outpoint (36 bytes: txid || vout)
        sum_input_pubkeys: The sum of all input public keys A (33 bytes compressed)

    Returns:
        32-byte hash
    """
    return tagged_hash("BIP0352/Inputs", smallest_outpoint + sum_input_pubkeys)


def get_shared_secret_hash(shared_secret: bytes, output_index: int) -> bytes:
    """
    Calculate t_k for output k.

    t_k = hash_BIP0352/SharedSecret(ser_P(ecdh_shared_secret) || ser_32(k))

    Args:
        shared_secret: 33-byte compressed point (ecdh_shared_secret)
        output_index: The output index k

    Returns:
        32-byte scalar t_k
    """
    k_bytes = output_index.to_bytes(4, 'big')
    return tagged_hash("BIP0352/SharedSecret", shared_secret + k_bytes)


def sum_public_keys(pubkeys: List[bytes]) -> bytes:
    """
    Sum multiple public keys into a single point.

    Args:
        pubkeys: List of 33-byte compressed public keys

    Returns:
        33-byte compressed public key representing the sum
    """
    if len(pubkeys) == 0:
        raise ValueError("Cannot sum empty list of public keys")

    if len(pubkeys) == 1:
        return pubkeys[0]

    # Parse all public keys to internal secp256k1 format
    parsed_keys = []
    for pk in pubkeys:
        parsed = secp256k1.ec_pubkey_parse(pk)
        parsed_keys.append(parsed)

    # Combine using secp256k1 (pass as *args)
    combined = secp256k1.ec_pubkey_combine(*parsed_keys)

    # Serialize back to compressed format
    return secp256k1.ec_pubkey_serialize(combined)


def compute_sp_output_pubkey(
    input_privkeys: List[Tuple[bytes, bool]],
    input_pubkeys: List[bytes],
    B_scan: bytes,
    B_spend: bytes,
    smallest_outpoint: bytes,
    output_index: int = 0
) -> bytes:
    """
    Compute the expected Silent Payment output public key.

    This is the core BIP-352 sending algorithm.

    Args:
        input_privkeys: List of (privkey_bytes, is_taproot) tuples
        input_pubkeys: List of 33-byte compressed public keys (corresponding to privkeys)
        B_scan: Recipient's scan public key (33 bytes)
        B_spend: Recipient's spend public key (33 bytes)
        smallest_outpoint: Lexicographically smallest outpoint (36 bytes)
        output_index: Output index k (default 0 for single output)

    Returns:
        33-byte compressed public key P_k for the output

    Raises:
        ValueError: If computation fails
    """
    if len(input_privkeys) != len(input_pubkeys):
        raise ValueError("Mismatched privkey/pubkey count")

    if len(input_privkeys) == 0:
        raise ValueError("No input keys provided")

    n = SECP256K1_ORDER

    # Step 1: Sum all private keys (with Taproot negation if needed)
    a_sum = 0
    adjusted_pubkeys = []

    for i, (privkey, is_taproot) in enumerate(input_privkeys):
        # Convert privkey bytes to integer
        a_i = int.from_bytes(privkey, 'big')
        pubkey = input_pubkeys[i]

        if is_taproot:
            # For Taproot inputs: negate privkey if pubkey Y is odd
            if pubkey[0] == 0x03:  # Odd Y
                a_i = n - a_i
                # Also need to use the negated pubkey (even Y)
                negated_parsed = secp256k1.ec_pubkey_parse(pubkey)
                negated = secp256k1.ec_pubkey_negate(negated_parsed)
                adjusted_pubkeys.append(secp256k1.ec_pubkey_serialize(negated))
            else:
                adjusted_pubkeys.append(pubkey)
        else:
            adjusted_pubkeys.append(pubkey)

        a_sum = (a_sum + a_i) % n

    if a_sum == 0:
        raise ValueError("Sum of private keys is zero")

    # Step 2: Calculate sum of input public keys A
    A = sum_public_keys(adjusted_pubkeys)

    # Step 3: Calculate input_hash
    input_hash = get_input_hash(smallest_outpoint, A)
    input_hash_scalar = int.from_bytes(input_hash, 'big') % n

    if input_hash_scalar == 0:
        raise ValueError("Input hash is zero")

    # Step 4: Compute a' = input_hash * a_sum
    a_prime = (input_hash_scalar * a_sum) % n

    # Step 5: ECDH: shared_secret = a' * B_scan
    a_prime_bytes = a_prime.to_bytes(32, 'big')
    B_scan_parsed = secp256k1.ec_pubkey_parse(B_scan)

    # Multiply B_scan by a' (modifies B_scan_parsed in-place, returns None)
    secp256k1.ec_pubkey_tweak_mul(B_scan_parsed, a_prime_bytes)
    shared_secret = secp256k1.ec_pubkey_serialize(B_scan_parsed)

    # Step 6: Calculate t_k
    t_k = get_shared_secret_hash(shared_secret, output_index)
    t_k_scalar = int.from_bytes(t_k, 'big') % n

    if t_k_scalar == 0:
        raise ValueError("t_k is zero")

    # Step 7: P_k = B_spend + t_k * G
    B_spend_parsed = secp256k1.ec_pubkey_parse(B_spend)

    # Add t_k * G to B_spend (modifies B_spend_parsed in-place, returns None)
    secp256k1.ec_pubkey_tweak_add(B_spend_parsed, t_k)

    return secp256k1.ec_pubkey_serialize(B_spend_parsed)


def get_smallest_outpoint(tx) -> bytes:
    """
    Get the lexicographically smallest outpoint from transaction inputs.

    Outpoint format: txid (32 bytes, little-endian) || vout (4 bytes, little-endian)

    Args:
        tx: embit Transaction object with vin attribute

    Returns:
        36-byte outpoint (smallest lexicographically)
    """
    outpoints = []
    for vin in tx.vin:
        # txid is already bytes (little-endian in embit)
        txid = vin.txid
        vout = vin.vout.to_bytes(4, 'little')
        outpoints.append(txid + vout)

    if not outpoints:
        raise ValueError("No inputs in transaction")

    return min(outpoints)


def is_eligible_input(psbt_input, fingerprint: str = None) -> bool:
    """
    Check if a PSBT input is eligible for Silent Payment computation.

    Per BIP-352, eligible inputs are:
    - P2PKH (single-sig)
    - P2WPKH (single-sig)
    - P2SH-P2WPKH (single-sig)
    - P2TR (key path spend only, single-sig)

    Excluded:
    - Multisig (any type)
    - P2TR script path spends

    Args:
        psbt_input: PSBT InputScope
        fingerprint: Optional fingerprint to match (hex string)

    Returns:
        True if input is eligible for SP computation
    """
    from binascii import hexlify

    # Check for Taproot
    if psbt_input.taproot_bip32_derivations:
        # Must be exactly one key (single-sig)
        if len(psbt_input.taproot_bip32_derivations) != 1:
            return False

        # Check for script path (has leaf hashes)
        for pub, (leaf_hashes, der) in psbt_input.taproot_bip32_derivations.items():
            if len(leaf_hashes) > 0:
                return False  # Script path spend, not eligible

            # If fingerprint specified, check it matches
            if fingerprint:
                if hexlify(der.fingerprint).decode() != fingerprint:
                    return False

        return True

    # Check for regular single-sig (P2PKH, P2WPKH, P2SH-P2WPKH)
    if psbt_input.bip32_derivations:
        # Must be exactly one key (single-sig)
        if len(psbt_input.bip32_derivations) != 1:
            return False

        # If fingerprint specified, check it matches
        if fingerprint:
            for pub, der in psbt_input.bip32_derivations.items():
                if hexlify(der.fingerprint).decode() != fingerprint:
                    return False

        return True

    return False


def xonly_to_full_pubkey(xonly: bytes, parity: int = 0) -> bytes:
    """
    Convert 32-byte x-only pubkey to 33-byte compressed pubkey.

    Args:
        xonly: 32-byte x-only public key
        parity: 0 for even Y (0x02 prefix), 1 for odd Y (0x03 prefix)

    Returns:
        33-byte compressed public key
    """
    prefix = 0x02 if parity == 0 else 0x03
    return bytes([prefix]) + xonly


def full_to_xonly_pubkey(full: bytes) -> Tuple[bytes, int]:
    """
    Convert 33-byte compressed pubkey to 32-byte x-only pubkey.

    Args:
        full: 33-byte compressed public key

    Returns:
        Tuple of (32-byte x-only pubkey, parity: 0=even, 1=odd)
    """
    if len(full) != 33:
        raise ValueError(f"Expected 33 bytes, got {len(full)}")

    parity = 0 if full[0] == 0x02 else 1
    return full[1:], parity
