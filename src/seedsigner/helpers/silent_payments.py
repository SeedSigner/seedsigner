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


# =============================================================================
# BIP-375 PSBT Field Constants
# =============================================================================

# Global PSBT fields (PSBTv2)
PSBT_GLOBAL_SP_ECDH_SHARE = 0x07  # Key: 33-byte scan pubkey, Value: 33-byte ECDH share
PSBT_GLOBAL_SP_DLEQ = 0x08        # Key: 33-byte scan pubkey, Value: 64-byte DLEQ proof

# Per-input PSBT fields
PSBT_IN_SP_ECDH_SHARE = 0x1d      # Key: 33-byte scan pubkey, Value: 33-byte ECDH share
PSBT_IN_SP_DLEQ = 0x1e            # Key: 33-byte scan pubkey, Value: 64-byte DLEQ proof

# Per-output PSBT fields
PSBT_OUT_SP_V0_INFO = 0x09        # Key: none, Value: 66 bytes (33-byte scan + 33-byte spend)


# =============================================================================
# BIP-374 DLEQ Proof Verification
# =============================================================================

def verify_dleq_proof(
    A: bytes,
    B: bytes,
    C: bytes,
    proof: bytes,
    G: bytes = None
) -> bool:
    """
    Verify a BIP-374 DLEQ proof.

    Verifies that the same scalar 'a' was used to compute:
    - A = a * G (public key)
    - C = a * B (ECDH shared point)

    This proves the ECDH share was computed correctly without revealing 'a'.

    Args:
        A: 33-byte compressed public key (sum of input pubkeys, or single input pubkey)
        B: 33-byte compressed public key (recipient's B_scan)
        C: 33-byte compressed ECDH share point
        proof: 64-byte DLEQ proof (32-byte challenge e || 32-byte response s)
        G: Optional generator point (uses secp256k1 generator if None)

    Returns:
        True if proof is valid, False otherwise
    """
    try:
        # Parse proof components
        if len(proof) != 64:
            logger.debug(f"DLEQ proof wrong length: {len(proof)}")
            return False

        e = int.from_bytes(proof[:32], 'big')
        s = int.from_bytes(proof[32:], 'big')

        n = SECP256K1_ORDER

        # Reject if s >= curve order
        if s >= n:
            logger.debug("DLEQ proof: s >= curve order")
            return False

        # Parse the input points
        A_parsed = secp256k1.ec_pubkey_parse(A)
        B_parsed = secp256k1.ec_pubkey_parse(B)
        C_parsed = secp256k1.ec_pubkey_parse(C)

        # Get generator G
        if G is None:
            # Use secp256k1 generator - derive from privkey=1
            G_point = ec.PrivateKey(b'\x00' * 31 + b'\x01').get_public_key().sec()
            G_parsed = secp256k1.ec_pubkey_parse(G_point)
        else:
            G_parsed = secp256k1.ec_pubkey_parse(G)
            G_point = G

        # R1 = s*G - e*A
        # First compute s*G
        sG_parsed = secp256k1.ec_pubkey_parse(G_point)
        s_bytes = s.to_bytes(32, 'big')
        secp256k1.ec_pubkey_tweak_mul(sG_parsed, s_bytes)

        # Compute e*A (need to negate for subtraction)
        eA_parsed = secp256k1.ec_pubkey_parse(A)
        e_bytes = e.to_bytes(32, 'big')
        secp256k1.ec_pubkey_tweak_mul(eA_parsed, e_bytes)

        # Negate e*A to get -e*A
        secp256k1.ec_pubkey_negate(eA_parsed)

        # R1 = s*G + (-e*A)
        R1_parsed = secp256k1.ec_pubkey_combine(sG_parsed, eA_parsed)
        R1 = secp256k1.ec_pubkey_serialize(R1_parsed)

        # R2 = s*B - e*C
        # First compute s*B
        sB_parsed = secp256k1.ec_pubkey_parse(B)
        secp256k1.ec_pubkey_tweak_mul(sB_parsed, s_bytes)

        # Compute e*C
        eC_parsed = secp256k1.ec_pubkey_parse(C)
        secp256k1.ec_pubkey_tweak_mul(eC_parsed, e_bytes)

        # Negate e*C
        secp256k1.ec_pubkey_negate(eC_parsed)

        # R2 = s*B + (-e*C)
        R2_parsed = secp256k1.ec_pubkey_combine(sB_parsed, eC_parsed)
        R2 = secp256k1.ec_pubkey_serialize(R2_parsed)

        # Compute challenge hash
        # e' = hash_BIP0374/challenge(A || B || C || G || R1 || R2)
        challenge_data = A + B + C + G_point + R1 + R2
        e_computed = tagged_hash("BIP0374/challenge", challenge_data)
        e_computed_int = int.from_bytes(e_computed, 'big')

        # Verify e == e'
        if e != e_computed_int:
            logger.debug(f"DLEQ proof: challenge mismatch")
            return False

        logger.info("DLEQ proof verified successfully")
        return True

    except Exception as ex:
        logger.debug(f"DLEQ verification failed: {ex}")
        return False


# =============================================================================
# BIP-375 PSBT Parsing
# =============================================================================

def extract_sp_info_from_output(output_scope) -> Optional[Tuple[bytes, bytes]]:
    """
    Extract Silent Payment info from PSBT output's unknown fields.

    Looks for PSBT_OUT_SP_V0_INFO (0x09) field containing the
    scan and spend public keys.

    Args:
        output_scope: PSBT OutputScope object

    Returns:
        Tuple of (B_scan, B_spend) if found, None otherwise
    """
    if not hasattr(output_scope, 'unknown') or not output_scope.unknown:
        return None

    # Key format: type byte (0x09) with no additional key data
    for key, value in output_scope.unknown.items():
        # Key is bytes, first byte is type
        if len(key) >= 1 and key[0] == PSBT_OUT_SP_V0_INFO:
            # Value should be 66 bytes: 33-byte scan key + 33-byte spend key
            if len(value) == 66:
                B_scan = bytes(value[:33])
                B_spend = bytes(value[33:66])

                # Validate pubkey prefixes
                if B_scan[0] in (0x02, 0x03) and B_spend[0] in (0x02, 0x03):
                    logger.debug(f"Found SP info in output: B_scan={B_scan[:4].hex()}...")
                    return (B_scan, B_spend)

    return None


def extract_global_ecdh_share(psbt, B_scan: bytes) -> Optional[Tuple[bytes, bytes]]:
    """
    Extract global ECDH share and DLEQ proof for a given scan key.

    Args:
        psbt: PSBT object
        B_scan: 33-byte scan public key to look for

    Returns:
        Tuple of (ecdh_share, dleq_proof) if found, None otherwise
    """
    if not hasattr(psbt, 'unknown') or not psbt.unknown:
        return None

    ecdh_share = None
    dleq_proof = None

    for key, value in psbt.unknown.items():
        if len(key) < 1:
            continue

        key_type = key[0]
        key_data = key[1:] if len(key) > 1 else b''

        # Check for ECDH share with matching B_scan
        if key_type == PSBT_GLOBAL_SP_ECDH_SHARE:
            if key_data == B_scan and len(value) == 33:
                ecdh_share = bytes(value)
                logger.debug(f"Found global ECDH share: {ecdh_share[:4].hex()}...")

        # Check for DLEQ proof with matching B_scan
        elif key_type == PSBT_GLOBAL_SP_DLEQ:
            if key_data == B_scan and len(value) == 64:
                dleq_proof = bytes(value)
                logger.debug(f"Found global DLEQ proof")

    if ecdh_share and dleq_proof:
        return (ecdh_share, dleq_proof)

    return None


def extract_input_ecdh_shares(psbt, B_scan: bytes) -> List[Tuple[int, bytes, bytes]]:
    """
    Extract per-input ECDH shares and DLEQ proofs for a given scan key.

    Args:
        psbt: PSBT object
        B_scan: 33-byte scan public key to look for

    Returns:
        List of (input_index, ecdh_share, dleq_proof) tuples
    """
    result = []

    for i, inp in enumerate(psbt.inputs):
        if not hasattr(inp, 'unknown') or not inp.unknown:
            continue

        ecdh_share = None
        dleq_proof = None

        for key, value in inp.unknown.items():
            if len(key) < 1:
                continue

            key_type = key[0]
            key_data = key[1:] if len(key) > 1 else b''

            if key_type == PSBT_IN_SP_ECDH_SHARE:
                if key_data == B_scan and len(value) == 33:
                    ecdh_share = bytes(value)

            elif key_type == PSBT_IN_SP_DLEQ:
                if key_data == B_scan and len(value) == 64:
                    dleq_proof = bytes(value)

        if ecdh_share and dleq_proof:
            result.append((i, ecdh_share, dleq_proof))

    return result


def verify_sp_output_with_bip375(
    psbt,
    output_index: int,
    B_scan: bytes,
    B_spend: bytes,
    seed_fingerprint: str = None
) -> Optional[bytes]:
    """
    Verify a Silent Payment output using BIP-375 ECDH shares and DLEQ proofs.

    This verifies that the coordinator correctly computed the SP output
    by checking the DLEQ proof against the provided ECDH share.

    Args:
        psbt: PSBT object
        output_index: Index of the output to verify
        B_scan: 33-byte recipient scan public key
        B_spend: 33-byte recipient spend public key
        seed_fingerprint: Optional fingerprint to identify owned inputs

    Returns:
        Expected x-only output pubkey if verified, None if verification fails
    """
    from binascii import hexlify

    n = SECP256K1_ORDER

    # Try global ECDH share first
    global_share = extract_global_ecdh_share(psbt, B_scan)

    if global_share:
        ecdh_share, dleq_proof = global_share

        # Get sum of all eligible input pubkeys (A_n)
        input_pubkeys = []
        for inp in psbt.inputs:
            if not is_eligible_input(inp, seed_fingerprint):
                continue

            # Get pubkey from derivation
            if inp.taproot_bip32_derivations:
                for pub, (leaf_hashes, der) in inp.taproot_bip32_derivations.items():
                    pubkey = pub.sec()
                    # For Taproot, use even-Y version
                    if pubkey[0] == 0x03:
                        parsed = secp256k1.ec_pubkey_parse(pubkey)
                        negated = secp256k1.ec_pubkey_negate(parsed)
                        pubkey = secp256k1.ec_pubkey_serialize(negated)
                    input_pubkeys.append(pubkey)
                    break
            elif inp.bip32_derivations:
                for pub, der in inp.bip32_derivations.items():
                    input_pubkeys.append(pub.sec())
                    break

        if not input_pubkeys:
            logger.warning("No eligible input pubkeys found for BIP-375 verification")
            return None

        A_n = sum_public_keys(input_pubkeys)

        # Verify DLEQ proof
        if not verify_dleq_proof(A_n, B_scan, ecdh_share, dleq_proof):
            logger.warning("BIP-375 global DLEQ proof verification failed")
            return None

        # Compute expected output from verified ECDH share
        # Get smallest outpoint and input hash
        smallest_outpoint = get_smallest_outpoint(psbt.tx)
        input_hash = get_input_hash(smallest_outpoint, A_n)
        input_hash_scalar = int.from_bytes(input_hash, 'big') % n

        # The ECDH share is: C = a_n * B_scan
        # We need: shared_secret = input_hash * C = input_hash * a_n * B_scan
        C_parsed = secp256k1.ec_pubkey_parse(ecdh_share)
        input_hash_bytes = input_hash_scalar.to_bytes(32, 'big')
        secp256k1.ec_pubkey_tweak_mul(C_parsed, input_hash_bytes)
        shared_secret = secp256k1.ec_pubkey_serialize(C_parsed)

        # Calculate t_k
        t_k = get_shared_secret_hash(shared_secret, output_index)

        # P_k = B_spend + t_k * G
        B_spend_parsed = secp256k1.ec_pubkey_parse(B_spend)
        secp256k1.ec_pubkey_tweak_add(B_spend_parsed, t_k)
        expected_pubkey = secp256k1.ec_pubkey_serialize(B_spend_parsed)

        expected_xonly, _ = full_to_xonly_pubkey(expected_pubkey)
        logger.info(f"BIP-375 verification successful for output {output_index}")
        return expected_xonly

    # TODO: Handle per-input ECDH shares (aggregate them)
    # This is more complex - need to sum the per-input shares
    per_input_shares = extract_input_ecdh_shares(psbt, B_scan)
    if per_input_shares:
        logger.warning("Per-input ECDH shares not yet implemented - falling back")

    return None


def encode_silent_payment_address(B_scan: bytes, B_spend: bytes, network: str = "mainnet") -> str:
    """
    Encode scan and spend public keys into a BIP-352 Silent Payment address.

    Args:
        B_scan: 33-byte compressed scan public key
        B_spend: 33-byte compressed spend public key
        network: "mainnet" or "testnet"

    Returns:
        Bech32m encoded SP address (sp1... or tsp1...)
    """
    if len(B_scan) != 33 or len(B_spend) != 33:
        raise ValueError("Public keys must be 33 bytes")

    hrp = "sp" if network == "mainnet" else "tsp"

    # Payload: B_scan + B_spend (66 bytes)
    payload = B_scan + B_spend

    # Convert payload to 5-bit groups
    data_5bit = _convertbits(list(payload), 8, 5, True)
    if data_5bit is None:
        raise ValueError("Failed to convert to 5-bit groups")

    # Prepend version byte (0) as first 5-bit value
    # This is the witness version, encoded separately
    data_5bit = [0] + data_5bit

    # Add checksum
    values = _bech32_hrp_expand(hrp) + data_5bit
    polymod = _bech32_polymod(values + [0, 0, 0, 0, 0, 0]) ^ BECH32M_CONST
    checksum = [(polymod >> 5 * (5 - i)) & 31 for i in range(6)]

    # Encode to string
    return hrp + "1" + "".join(CHARSET[d] for d in data_5bit + checksum)


def has_bip375_sp_fields(psbt) -> bool:
    """
    Check if PSBT contains any BIP-375 Silent Payment fields.

    Args:
        psbt: PSBT object

    Returns:
        True if any BIP-375 SP fields are present
    """
    # Check global fields
    if hasattr(psbt, 'unknown') and psbt.unknown:
        for key in psbt.unknown.keys():
            if len(key) >= 1 and key[0] in (PSBT_GLOBAL_SP_ECDH_SHARE, PSBT_GLOBAL_SP_DLEQ):
                return True

    # Check output fields
    for out in psbt.outputs:
        if hasattr(out, 'unknown') and out.unknown:
            for key in out.unknown.keys():
                if len(key) >= 1 and key[0] == PSBT_OUT_SP_V0_INFO:
                    return True

    # Check input fields
    for inp in psbt.inputs:
        if hasattr(inp, 'unknown') and inp.unknown:
            for key in inp.unknown.keys():
                if len(key) >= 1 and key[0] in (PSBT_IN_SP_ECDH_SHARE, PSBT_IN_SP_DLEQ):
                    return True

    return False


# PSBTv2 Detection Constants
PSBT_GLOBAL_VERSION = 0xFB  # BIP-370 PSBT version field


def get_psbt_version(psbt) -> int:
    """
    Detect the PSBT version.

    PSBTv0: No version field (default)
    PSBTv2: Has PSBT_GLOBAL_VERSION (0xFB) field with value >= 2

    Args:
        psbt: PSBT object (embit)

    Returns:
        int: PSBT version (0 for v0/unknown, 2 for v2)
    """
    if not hasattr(psbt, 'unknown') or not psbt.unknown:
        return 0

    # Check for BIP-370 version field
    version_key = bytes([PSBT_GLOBAL_VERSION])
    if version_key in psbt.unknown:
        version_value = psbt.unknown[version_key]
        # Version is a 32-bit unsigned little-endian integer
        if len(version_value) >= 4:
            version = int.from_bytes(version_value[:4], 'little')
            return version

    return 0


def is_psbt_v2(psbt) -> bool:
    """
    Check if PSBT is version 2 (BIP-370).

    Args:
        psbt: PSBT object (embit)

    Returns:
        True if this is a PSBTv2
    """
    return get_psbt_version(psbt) >= 2
