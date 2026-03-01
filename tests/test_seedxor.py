import unittest
from unittest.mock import MagicMock

from seedsigner.helpers.mnemonic_generation import combine_mnemonics_with_xor
from seedsigner.helpers.seed_xor_validator import SeedXORValidator

from embit import bip39

EXAMPLE_24_A = "romance wink lottery autumn shop bring dawn tongue range crater truth ability miss spice fitness easy legal release recall obey exchange recycle dragon room"
EXAMPLE_24_B = "lion misery divide hurry latin fluid camp advance illegal lab pyramid unaware eager fringe sick camera series noodle toy crowd jeans select depth lounge"
EXAMPLE_24_C = "vault nominee cradle silk own frown throw leg cactus recall talent worry gadget surface shy planet purpose coffee drip few seven term squeeze educate"
RESULT_24_ABC = "silent toe meat possible chair blossom wait occur this worth option bag nurse find fish scene bench asthma bike wage world quit primary indoor"

EXAMPLE_12_A = "romance wink lottery autumn shop bring dawn tongue range crater truth ability"
EXAMPLE_12_B = "boat unfair shell violin tree robust open ride visual forest vintage approve"
EXAMPLE_12_C = "lion misery divide hurry latin fluid camp advance illegal lab pyramid unhappy"
RESULT_12_ABC = "cannon opinion leader nephew found yard metal galaxy crouch between real trade"

ZERO_ENTROPY_MNEMONIC_12 = "abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon about"
ZERO_ENTROPY_MNEMONIC_24 = "abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon art"



class TestCombineMnemonicsWithXOR(unittest.TestCase):
    """
    Tests the core XOR calculation logic, input validation, and error handling.
    """

    def test_xor_24_word_example(self):
        """Tests the 3-part 24-word XOR calculation from the provided example. """
        mnemonics = [EXAMPLE_24_A, EXAMPLE_24_B, EXAMPLE_24_C]
        result = combine_mnemonics_with_xor(mnemonics)
        self.assertEqual(result, RESULT_24_ABC.split())


    def test_xor_12_word_example(self):
        """Tests the 3-part 12-word XOR calculation from the provided example. """
        mnemonics = [EXAMPLE_12_A, EXAMPLE_12_B, EXAMPLE_12_C]
        result = combine_mnemonics_with_xor(mnemonics)
        self.assertEqual(result, RESULT_12_ABC.split())


    def test_xor_identity_property(self):
        """ Tests the XOR identity property (A ^ B ^ B = A). """
        mnemonics = [EXAMPLE_12_A, EXAMPLE_12_B, EXAMPLE_12_B]
        result = combine_mnemonics_with_xor(mnemonics)
        self.assertEqual(result, EXAMPLE_12_A.split())


    def test_xor_null_property(self):
        """ Tests the XOR null property (A ^ A = 0) for both 12 and 24-word mnemonics. """
        # Test 12-word case
        result_12 = combine_mnemonics_with_xor([EXAMPLE_12_A, EXAMPLE_12_A])
        self.assertEqual(result_12, ZERO_ENTROPY_MNEMONIC_12.split())

        # Test 24-word case
        result_24 = combine_mnemonics_with_xor([EXAMPLE_24_A, EXAMPLE_24_A])
        self.assertEqual(result_24, ZERO_ENTROPY_MNEMONIC_24.split())


    def test_handles_list_of_words_input(self):
        """Tests that the function correctly processes mnemonics formatted as a list of words. """
        mnemonics = [EXAMPLE_12_A.split(), EXAMPLE_12_B]
        result = combine_mnemonics_with_xor(mnemonics)

        expected_result = "person bitter door winner candy polar proud fringe early have bulb apple".split()
        self.assertEqual(result, expected_result)


    def test_raises_error_for_empty_list(self):
        """Ensures ValueError is raised for an empty mnemonic list. """
        with self.assertRaisesRegex(ValueError, "Mnemonic list cannot be empty"):
            combine_mnemonics_with_xor([])


    def test_raises_error_for_invalid_mnemonic(self):
        """Ensures ValueError is raised for a mnemonic with a word not in the wordlist. """
        invalid_mnemonic = "romance wink lottery autumn shop bring dawn tongue range crater truth notaword"
        with self.assertRaisesRegex(ValueError, "not in the dictionary"):
            combine_mnemonics_with_xor([EXAMPLE_12_A, invalid_mnemonic])


    def test_raises_error_for_mismatched_lengths(self):
        """ Ensures ValueError is raised when mnemonics have different entropy lengths. """
        with self.assertRaisesRegex(ValueError, "All mnemonics must generate entropy of the same length"):
            combine_mnemonics_with_xor([EXAMPLE_12_A, EXAMPLE_24_A])



class TestSeedXORValidator(unittest.TestCase):
    """
    Tests the validation logic for adding new shards to an XOR operation.
    """
    def setUp(self):
        """ Set up mock Seed objects for testing using the provided examples. """
        self.shard_12_A = MagicMock()
        self.shard_12_A.has_passphrase = False
        self.shard_12_A.mnemonic_str = EXAMPLE_12_A
        self.shard_12_A.mnemonic_list = EXAMPLE_12_A.split()

        self.shard_12_B = MagicMock()
        self.shard_12_B.has_passphrase = False
        self.shard_12_B.mnemonic_str = EXAMPLE_12_B
        self.shard_12_B.mnemonic_list = EXAMPLE_12_B.split()

        self.shard_24_A = MagicMock()
        self.shard_24_A.has_passphrase = False
        self.shard_24_A.mnemonic_str = EXAMPLE_24_A
        self.shard_24_A.mnemonic_list = EXAMPLE_24_A.split()


    def test_valid_first_shard(self):
        """ A valid shard added to an empty list should pass. """
        is_valid, error = SeedXORValidator.validate_shard(self.shard_12_A, [])
        self.assertTrue(is_valid)
        self.assertIsNone(error)


    def test_valid_second_shard(self):
        """ A second, valid, unique shard of the same length should pass. """
        is_valid, error = SeedXORValidator.validate_shard(self.shard_12_B, [self.shard_12_A])
        self.assertTrue(is_valid)
        self.assertIsNone(error)


    def test_rejects_shard_with_passphrase(self):
        """ Shards with passphrases should be rejected. """
        self.shard_12_A.has_passphrase = True
        is_valid, error = SeedXORValidator.validate_shard(self.shard_12_A, [])
        self.assertFalse(is_valid)
        self.assertEqual(error["title"], "Passphrase Not Allowed")


    def test_rejects_mismatched_mnemonic_length(self):
        """ Shards of different lengths should be rejected. """
        is_valid, error = SeedXORValidator.validate_shard(self.shard_24_A, [self.shard_12_A])
        self.assertFalse(is_valid)
        self.assertEqual(error["title"], "Mnemonic Length Mismatch")


    def test_rejects_duplicate_shard(self):
        """ An identical shard should be rejected. """
        is_valid, error = SeedXORValidator.validate_shard(self.shard_12_A, [self.shard_12_A])
        self.assertFalse(is_valid)
        self.assertEqual(error["title"], "Duplicate Shard")
        self.assertIn("shard #1", error["message"])


    def test_rejects_inverse_shard(self):
        """ A binary inverse shard (which would cancel another out) should be rejected. """
        entropy_a = bip39.mnemonic_to_bytes(EXAMPLE_12_A)
        inverse_entropy = bytes(b ^ 0xFF for b in entropy_a)
        inverse_mnemonic_str = bip39.mnemonic_from_bytes(inverse_entropy)

        inverse_shard = MagicMock()
        inverse_shard.has_passphrase = False
        inverse_shard.mnemonic_str = inverse_mnemonic_str
        inverse_shard.mnemonic_list = inverse_mnemonic_str.split()

        is_valid, error = SeedXORValidator.validate_shard(inverse_shard, [self.shard_12_A])
        self.assertFalse(is_valid)
        self.assertEqual(error["title"], "Seed Inversion")
        self.assertIn("binary inverse of shard #1", error["message"])
