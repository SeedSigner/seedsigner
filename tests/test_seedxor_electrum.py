"""
Tests for Electrum seed support in Seed XOR operations.

Verifies that:
1. Electrum seeds can participate in XOR operations
2. XOR'ing an Electrum seed with random BIP-39 parts and back produces
   the original Electrum seed
3. The result type is correctly detected (Electrum vs BIP-39)
4. Word count restrictions are enforced
5. XOR is commutative and associative
"""

import unittest
from unittest.mock import MagicMock

from seedsigner.helpers.mnemonic_generation import combine_mnemonics_with_xor
from seedsigner.models.seed import Seed, ElectrumSeed
from seedsigner.helpers.seed_xor_validator import SeedXORValidator

from embit import bip39

# A known valid Electrum segwit seed (12 words, HMAC prefix "100")
# This is from the existing test suite in test_seed.py
ELECTRUM_SEED = "regular reject rare profit once math fringe chase until ketchup century escape"

# Valid BIP-39 12-word seeds to use as XOR partners
BIP39_SEED_A = "romance wink lottery autumn shop bring dawn tongue range crater truth ability"
BIP39_SEED_B = "zoo zoo zoo zoo zoo zoo zoo zoo zoo zoo zoo wrong"

# A valid BIP-39 24-word seed
BIP39_SEED_24 = "romance wink lottery autumn shop bring dawn tongue range crater truth ability miss spice fitness easy legal release recall obey exchange recycle dragon room"



class TestSeedXORWithElectrumSeeds(unittest.TestCase):

    def test_electrum_seed_is_valid(self):
        """Verify our test Electrum seed is actually valid."""
        seed = ElectrumSeed(mnemonic=ELECTRUM_SEED.split())
        self.assertIsNotNone(seed.seed_bytes)

    def test_electrum_seed_roundtrip(self):
        """
        XOR an Electrum seed with a BIP-39 seed, then XOR the result back
        with the same BIP-39 seed. The entropy is perfectly preserved.

        The XOR result will have a BIP-39 checksum (last word may differ),
        but get_electrum_mnemonic recovers the exact original Electrum seed.
        """
        electrum_words = ELECTRUM_SEED.split()

        # Split: electrum XOR bip39 = part_b
        part_b = combine_mnemonics_with_xor([ELECTRUM_SEED, BIP39_SEED_A])

        # Reconstruct: part_b XOR bip39 = entropy of original electrum
        reconstructed = combine_mnemonics_with_xor([" ".join(part_b), BIP39_SEED_A])

        # The first 11 words are identical (they carry only entropy bits)
        self.assertEqual(reconstructed[:-1], electrum_words[:-1])

        # Use get_electrum_mnemonic to recover the exact original last word
        electrum_mnemonic = Seed.get_electrum_mnemonic(reconstructed)
        self.assertIsNotNone(electrum_mnemonic)
        self.assertEqual(electrum_mnemonic, electrum_words)

    def test_xor_result_type_detection_electrum(self):
        """
        After XOR reconstruction, the result should be detected as Electrum.
        """
        part_b = combine_mnemonics_with_xor([ELECTRUM_SEED, BIP39_SEED_A])
        reconstructed = combine_mnemonics_with_xor([" ".join(part_b), BIP39_SEED_A])

        self.assertEqual(Seed.detect_mnemonic_type(reconstructed), "electrum")

    def test_xor_result_type_detection_bip39(self):
        """
        XOR of two BIP-39 seeds should be detected as BIP-39.
        """
        result = combine_mnemonics_with_xor([BIP39_SEED_A, BIP39_SEED_B])
        self.assertEqual(Seed.detect_mnemonic_type(result), "bip39")

    def test_xor_part_is_valid_bip39(self):
        """
        XOR parts derived from an Electrum seed should be valid BIP-39.
        They should NOT be valid Electrum seeds (astronomically unlikely).
        """
        part_b = combine_mnemonics_with_xor([ELECTRUM_SEED, BIP39_SEED_A])

        # part_b should be a valid BIP-39 mnemonic
        self.assertTrue(bip39.mnemonic_is_valid(" ".join(part_b)))

        # part_b is almost certainly NOT a valid Electrum seed
        self.assertEqual(Seed.detect_mnemonic_type(part_b), "bip39")

    def test_mixed_12word_electrum_bip39(self):
        """
        Can XOR a 12-word Electrum seed with multiple 12-word BIP-39 seeds.
        The entropy round-trips perfectly; get_electrum_mnemonic recovers
        the exact original.
        """
        electrum_words = ELECTRUM_SEED.split()

        # 3-way split
        parts = combine_mnemonics_with_xor([ELECTRUM_SEED, BIP39_SEED_A, BIP39_SEED_B])
        # Reconstruct
        result = combine_mnemonics_with_xor([" ".join(parts), BIP39_SEED_A, BIP39_SEED_B])

        # First 11 words match (pure entropy)
        self.assertEqual(result[:-1], electrum_words[:-1])

        # Recover exact Electrum mnemonic
        electrum_mnemonic = Seed.get_electrum_mnemonic(result)
        self.assertIsNotNone(electrum_mnemonic)
        self.assertEqual(electrum_mnemonic, electrum_words)

    def test_word_count_mismatch_rejected(self):
        """
        Cannot XOR a 12-word Electrum seed with a 24-word BIP-39 seed.
        """
        with self.assertRaises(ValueError):
            combine_mnemonics_with_xor([ELECTRUM_SEED, BIP39_SEED_24])

    def test_three_way_xor_order_independent(self):
        """
        XOR is commutative and associative: order doesn't matter.
        """
        result_abc = combine_mnemonics_with_xor([ELECTRUM_SEED, BIP39_SEED_A, BIP39_SEED_B])
        result_bca = combine_mnemonics_with_xor([BIP39_SEED_A, BIP39_SEED_B, ELECTRUM_SEED])
        result_cab = combine_mnemonics_with_xor([BIP39_SEED_B, ELECTRUM_SEED, BIP39_SEED_A])

        self.assertEqual(result_abc, result_bca)
        self.assertEqual(result_bca, result_cab)

    def test_detect_mnemonic_type_known_electrum(self):
        """
        detect_mnemonic_type should identify a known Electrum seed.
        """
        self.assertEqual(Seed.detect_mnemonic_type(ELECTRUM_SEED.split()), "electrum")

    def test_detect_mnemonic_type_known_bip39(self):
        """
        detect_mnemonic_type should identify a known BIP-39 seed.
        Note: We use BIP39_SEED_B here because BIP39_SEED_A happens to have
        a last-word variant that collides with an Electrum standard prefix.
        """
        self.assertEqual(Seed.detect_mnemonic_type(BIP39_SEED_B.split()), "bip39")

    def test_validator_accepts_electrum_shard(self):
        """
        The SeedXORValidator should accept an Electrum seed as a shard
        (it has no passphrase and valid word count).
        """
        # Create a real ElectrumSeed object
        electrum_seed = ElectrumSeed(mnemonic=ELECTRUM_SEED.split())
        bip39_seed = Seed(mnemonic=BIP39_SEED_A.split())

        # First shard (Electrum)
        is_valid, error = SeedXORValidator.validate_shard(electrum_seed, [])
        self.assertTrue(is_valid)
        self.assertIsNone(error)

        # Second shard (BIP-39 after Electrum)
        is_valid, error = SeedXORValidator.validate_shard(bip39_seed, [electrum_seed])
        self.assertTrue(is_valid)
        self.assertIsNone(error)

    def test_validator_rejects_electrum_with_passphrase(self):
        """
        Electrum seeds with a passphrase should be rejected as XOR components.
        """
        electrum_seed = ElectrumSeed(mnemonic=ELECTRUM_SEED.split(), passphrase="test")

        is_valid, error = SeedXORValidator.validate_shard(electrum_seed, [])
        self.assertFalse(is_valid)
        self.assertEqual(error["title"], "Passphrase Not Allowed")

    def test_reconstructed_electrum_seed_derivation(self):
        """
        After XOR reconstruction and Electrum mnemonic recovery, the seed
        should produce the same derivation path and fingerprint as the original.
        """
        original = ElectrumSeed(mnemonic=ELECTRUM_SEED.split())
        original_fingerprint = original.get_fingerprint()

        # Split and reconstruct
        part_b = combine_mnemonics_with_xor([ELECTRUM_SEED, BIP39_SEED_A])
        reconstructed_mnemonic = combine_mnemonics_with_xor([" ".join(part_b), BIP39_SEED_A])

        # Verify it's detected as Electrum
        self.assertEqual(Seed.detect_mnemonic_type(reconstructed_mnemonic), "electrum")

        # Recover the exact Electrum mnemonic (correct last word)
        electrum_mnemonic = Seed.get_electrum_mnemonic(reconstructed_mnemonic)
        self.assertIsNotNone(electrum_mnemonic)

        # Create ElectrumSeed from recovered mnemonic
        reconstructed = ElectrumSeed(mnemonic=electrum_mnemonic)
        reconstructed_fingerprint = reconstructed.get_fingerprint()

        self.assertEqual(original_fingerprint, reconstructed_fingerprint)
        self.assertEqual(original.derivation_override(), reconstructed.derivation_override())
        self.assertFalse(reconstructed.seedqr_supported)
