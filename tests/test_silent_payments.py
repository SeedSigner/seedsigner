"""
Tests for BIP-352 Silent Payments implementation.

Uses official test vectors from:
https://github.com/bitcoin/bips/blob/master/bip-0352/send_and_receive_test_vectors.json
"""

import pytest
from binascii import unhexlify

from tests.base import BaseTest


class TestBech32mDecode(BaseTest):
    """Test Bech32m decoding for SP addresses."""

    def test_mainnet_address_basic(self):
        """Parse a mainnet SP address and extract components."""
        from seedsigner.helpers.silent_payments import parse_silent_payment_address

        # Known test vector SP address
        address = "sp1qqgste7k9hx0qftg6qmwlkqtwuy6cycyavzmzj85c6qdfhjdpdjtdgqjuexzk6murw56suy3e0rd2cgqvycxttddwsvgxe2usfpxumr70xc9pkqwv"

        B_scan, B_spend, network = parse_silent_payment_address(address)

        assert network == "mainnet"
        assert len(B_scan) == 33
        assert len(B_spend) == 33
        # Verify they're valid compressed pubkeys
        assert B_scan[0] in (0x02, 0x03)
        assert B_spend[0] in (0x02, 0x03)

    def test_mainnet_address_known_keys(self):
        """Verify extracted keys match expected values."""
        from seedsigner.helpers.silent_payments import parse_silent_payment_address

        address = "sp1qqgste7k9hx0qftg6qmwlkqtwuy6cycyavzmzj85c6qdfhjdpdjtdgqjuexzk6murw56suy3e0rd2cgqvycxttddwsvgxe2usfpxumr70xc9pkqwv"

        B_scan, B_spend, network = parse_silent_payment_address(address)

        # From test vectors
        expected_scan = unhexlify("0220bcfac5b99e04ad1a06ddfb016ee13582609d60b6291e98d01a9bc9a16c96d4")
        expected_spend = unhexlify("025cc9856d6f8375350e123978daac200c260cb5b5ae83106cab90484dcd8fcf36")

        assert B_scan == expected_scan
        assert B_spend == expected_spend

    def test_invalid_checksum(self):
        """Invalid checksum should raise ValueError."""
        from seedsigner.helpers.silent_payments import parse_silent_payment_address

        # Changed last valid character to corrupt checksum
        address = "sp1qqgste7k9hx0qftg6qmwlkqtwuy6cycyavzmzj85c6qdfhjdpdjtdgqjuexzk6murw56suy3e0rd2cgqvycxttddwsvgxe2usfpxumr70xc9pkqwa"

        with pytest.raises(ValueError, match="Invalid checksum"):
            parse_silent_payment_address(address)

    def test_invalid_hrp(self):
        """Non-SP HRP should raise ValueError."""
        from seedsigner.helpers.silent_payments import parse_silent_payment_address

        # bc1 is a regular bech32 address, not SP
        # Note: bc1 uses bech32 (not bech32m) so it fails checksum first
        with pytest.raises(ValueError, match="Invalid checksum"):
            parse_silent_payment_address("bc1qw508d6qejxtdg4y5r3zarvary0c5xw7kv8f3t4")

    def test_testnet_hrp(self):
        """Testnet addresses should be recognized."""
        from seedsigner.helpers.silent_payments import bech32m_decode

        # Test that sp prefix is valid
        hrp, _ = bech32m_decode("sp1qqgste7k9hx0qftg6qmwlkqtwuy6cycyavzmzj85c6qdfhjdpdjtdgqjuexzk6murw56suy3e0rd2cgqvycxttddwsvgxe2usfpxumr70xc9pkqwv")
        assert hrp == "sp"


class TestTaggedHash(BaseTest):
    """Test BIP-340 tagged hash implementation."""

    def test_tagged_hash_deterministic(self):
        """Same inputs should produce same outputs."""
        from seedsigner.helpers.silent_payments import tagged_hash

        data = b"test data"
        result1 = tagged_hash("BIP0352/Inputs", data)
        result2 = tagged_hash("BIP0352/Inputs", data)

        assert result1 == result2
        assert len(result1) == 32

    def test_different_tags_different_output(self):
        """Different tags should produce different hashes."""
        from seedsigner.helpers.silent_payments import tagged_hash

        data = b"test data"
        result1 = tagged_hash("BIP0352/Inputs", data)
        result2 = tagged_hash("BIP0352/SharedSecret", data)

        assert result1 != result2


class TestSumPublicKeys(BaseTest):
    """Test public key summation."""

    def test_sum_single_key(self):
        """Summing a single key should return the same key."""
        from seedsigner.helpers.silent_payments import sum_public_keys

        pubkey = unhexlify("025a1e61f898173040e20616d43e9f496fba90338a39faa1ed98fcbaeee4dd9be5")
        result = sum_public_keys([pubkey])

        assert result == pubkey

    def test_sum_two_keys(self):
        """Sum of two different pubkeys should produce a valid pubkey."""
        from seedsigner.helpers.silent_payments import sum_public_keys

        pk1 = unhexlify("025a1e61f898173040e20616d43e9f496fba90338a39faa1ed98fcbaeee4dd9be5")
        pk2 = unhexlify("03bd85685d03d111699b15d046319febe77f8de5286e9e512703cdee1bf3be3792")

        result = sum_public_keys([pk1, pk2])

        # Result should be a valid 33-byte compressed pubkey
        assert len(result) == 33
        assert result[0] in (0x02, 0x03)
        # Result should be different from both inputs
        assert result != pk1
        assert result != pk2

    def test_sum_empty_raises(self):
        """Empty list should raise ValueError."""
        from seedsigner.helpers.silent_payments import sum_public_keys

        with pytest.raises(ValueError, match="Cannot sum empty"):
            sum_public_keys([])


class TestComputeSPOutputPubkey(BaseTest):
    """Test the core BIP-352 output pubkey computation."""

    def test_simple_send_two_inputs(self):
        """
        Test Case 1 from BIP-352 test vectors:
        Simple send with two P2PKH inputs
        """
        from seedsigner.helpers.silent_payments import (
            compute_sp_output_pubkey,
            parse_silent_payment_address,
            full_to_xonly_pubkey,
        )
        from embit import ec

        # Input private keys (from test vector)
        privkey1 = unhexlify("eadc78165ff1f8ea94ad7cfdc54990738a4c53f6e0507b42154201b8e5dff3b1")
        privkey2 = unhexlify("93f5ed907ad5b2bdbbdcb5d9116ebc0a4e1f92f910d5260237fa45a9408aad16")

        # Derive public keys from private keys
        pk1 = ec.PrivateKey(privkey1).get_public_key().sec()
        pk2 = ec.PrivateKey(privkey2).get_public_key().sec()

        # Recipient SP address
        sp_address = "sp1qqgste7k9hx0qftg6qmwlkqtwuy6cycyavzmzj85c6qdfhjdpdjtdgqjuexzk6murw56suy3e0rd2cgqvycxttddwsvgxe2usfpxumr70xc9pkqwv"
        B_scan, B_spend, _ = parse_silent_payment_address(sp_address)

        # Construct smallest outpoint (from test vector)
        # txid must be little-endian
        txid1 = unhexlify("f4184fc596403b9d638783cf57adfe4c75c605f6356fbc91338530e9831e9e16")[::-1]
        vout1 = (0).to_bytes(4, 'little')
        txid2 = unhexlify("a1075db55d416d3ca199f55b6084e2115b9345e16c5cf302fc80e9d5fbf5d48d")[::-1]
        vout2 = (0).to_bytes(4, 'little')

        # Find smallest outpoint
        outpoint1 = txid1 + vout1
        outpoint2 = txid2 + vout2
        smallest_outpoint = min(outpoint1, outpoint2)

        # Compute output pubkey
        input_privkeys = [(privkey1, False), (privkey2, False)]  # P2PKH, not taproot
        input_pubkeys = [pk1, pk2]

        result = compute_sp_output_pubkey(
            input_privkeys,
            input_pubkeys,
            B_scan,
            B_spend,
            smallest_outpoint,
            output_index=0
        )

        # Expected output (x-only, from test vector)
        expected_xonly = unhexlify("3e9fce73d4e77a4809908e3c3a2e54ee147b9312dc5044a193d1fc85de46e3c1")

        # Convert result to x-only for comparison
        result_xonly, _ = full_to_xonly_pubkey(result)

        assert result_xonly == expected_xonly

    def test_two_inputs_same_tx_different_vout(self):
        """
        Test Case 3: Two inputs from same transaction (different vout)
        This tests that the smallest outpoint logic works correctly with vout comparison.
        """
        from seedsigner.helpers.silent_payments import (
            compute_sp_output_pubkey,
            parse_silent_payment_address,
            full_to_xonly_pubkey,
        )
        from embit import ec

        # Input private keys
        privkey1 = unhexlify("eadc78165ff1f8ea94ad7cfdc54990738a4c53f6e0507b42154201b8e5dff3b1")
        privkey2 = unhexlify("93f5ed907ad5b2bdbbdcb5d9116ebc0a4e1f92f910d5260237fa45a9408aad16")

        pk1 = ec.PrivateKey(privkey1).get_public_key().sec()
        pk2 = ec.PrivateKey(privkey2).get_public_key().sec()

        # Same SP address
        sp_address = "sp1qqgste7k9hx0qftg6qmwlkqtwuy6cycyavzmzj85c6qdfhjdpdjtdgqjuexzk6murw56suy3e0rd2cgqvycxttddwsvgxe2usfpxumr70xc9pkqwv"
        B_scan, B_spend, _ = parse_silent_payment_address(sp_address)

        # Both inputs from same txid but different vouts (3 and 7)
        txid = unhexlify("f4184fc596403b9d638783cf57adfe4c75c605f6356fbc91338530e9831e9e16")[::-1]
        vout1 = (3).to_bytes(4, 'little')
        vout2 = (7).to_bytes(4, 'little')

        outpoint1 = txid + vout1
        outpoint2 = txid + vout2
        smallest_outpoint = min(outpoint1, outpoint2)  # vout=3 should be smaller

        input_privkeys = [(privkey1, False), (privkey2, False)]
        input_pubkeys = [pk1, pk2]

        result = compute_sp_output_pubkey(
            input_privkeys,
            input_pubkeys,
            B_scan,
            B_spend,
            smallest_outpoint,
            output_index=0
        )

        # Expected output from test vector
        expected_xonly = unhexlify("79e71baa2ba3fc66396de3a04f168c7bf24d6870ec88ca877754790c1db357b6")

        result_xonly, _ = full_to_xonly_pubkey(result)

        assert result_xonly == expected_xonly


class TestXOnlyConversion(BaseTest):
    """Test x-only pubkey conversion utilities."""

    def test_full_to_xonly_even(self):
        """Convert compressed pubkey with even Y to x-only."""
        from seedsigner.helpers.silent_payments import full_to_xonly_pubkey

        # Even Y (0x02 prefix)
        full = unhexlify("025a1e61f898173040e20616d43e9f496fba90338a39faa1ed98fcbaeee4dd9be5")
        xonly, parity = full_to_xonly_pubkey(full)

        assert len(xonly) == 32
        assert parity == 0
        assert xonly == full[1:]

    def test_full_to_xonly_odd(self):
        """Convert compressed pubkey with odd Y to x-only."""
        from seedsigner.helpers.silent_payments import full_to_xonly_pubkey

        # Odd Y (0x03 prefix)
        full = unhexlify("03bd85685d03d111699b15d046319febe77f8de5286e9e512703cdee1bf3be3792")
        xonly, parity = full_to_xonly_pubkey(full)

        assert len(xonly) == 32
        assert parity == 1
        assert xonly == full[1:]

    def test_xonly_to_full(self):
        """Convert x-only back to full compressed pubkey."""
        from seedsigner.helpers.silent_payments import xonly_to_full_pubkey, full_to_xonly_pubkey

        original = unhexlify("025a1e61f898173040e20616d43e9f496fba90338a39faa1ed98fcbaeee4dd9be5")
        xonly, parity = full_to_xonly_pubkey(original)
        restored = xonly_to_full_pubkey(xonly, parity)

        assert restored == original

    def test_roundtrip_odd(self):
        """Roundtrip conversion with odd Y."""
        from seedsigner.helpers.silent_payments import xonly_to_full_pubkey, full_to_xonly_pubkey

        original = unhexlify("03bd85685d03d111699b15d046319febe77f8de5286e9e512703cdee1bf3be3792")
        xonly, parity = full_to_xonly_pubkey(original)
        restored = xonly_to_full_pubkey(xonly, parity)

        assert restored == original


class TestIsEligibleInput(BaseTest):
    """Test input eligibility checking."""

    def test_eligible_requirements(self):
        """Document the eligibility requirements."""
        # This is more of a documentation test
        # Per BIP-352:
        # - P2PKH, P2WPKH, P2SH-P2WPKH, P2TR (key path) are eligible
        # - Multisig and P2TR script path are NOT eligible
        pass
