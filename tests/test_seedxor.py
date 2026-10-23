import unittest
from unittest.mock import MagicMock

from seedsigner.helpers.mnemonic_generation import combine_mnemonics_with_xor
from seedsigner.helpers.seed_xor_validator import SeedXORValidator
from seedsigner.models.seed import Seed

from embit import bip39

from seedxor_test_vectors import (
    EXAMPLE_24_A, EXAMPLE_24_B, EXAMPLE_24_C, RESULT_24_ABC,
    EXAMPLE_12_A, EXAMPLE_12_B, EXAMPLE_12_C, RESULT_12_ABC,
    ZERO_ENTROPY_MNEMONIC_12, ZERO_ENTROPY_MNEMONIC_24,
)



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
        """Ensures ValueError is raised for a mnemonic with a bad checksum or invalid word. """
        invalid_mnemonic = "romance wink lottery autumn shop bring dawn tongue range crater truth zebra" # 'zebra' is invalid
        with self.assertRaisesRegex(ValueError, "Invalid mnemonic"):
            combine_mnemonics_with_xor([EXAMPLE_12_A, invalid_mnemonic])


    def test_raises_error_for_mismatched_lengths(self):
        """ Ensures ValueError is raised when mnemonics have different entropy lengths. """
        with self.assertRaisesRegex(ValueError, "All mnemonics must generate entropy of the same length"):
            combine_mnemonics_with_xor([EXAMPLE_12_A, EXAMPLE_24_A])



class TestSeedXORValidator(unittest.TestCase):
    """
    Tests the validation logic for adding new parts to an XOR operation.
    """
    def setUp(self):
        """ Set up mock Seed objects for testing using the provided examples. """
        wordlist = Seed.get_wordlist()

        self.part_12_A = MagicMock()
        self.part_12_A.has_passphrase = False
        self.part_12_A.mnemonic_str = EXAMPLE_12_A
        self.part_12_A.mnemonic_list = EXAMPLE_12_A.split()
        self.part_12_A.wordlist = wordlist

        self.part_12_B = MagicMock()
        self.part_12_B.has_passphrase = False
        self.part_12_B.mnemonic_str = EXAMPLE_12_B
        self.part_12_B.mnemonic_list = EXAMPLE_12_B.split()
        self.part_12_B.wordlist = wordlist
        
        self.part_24_A = MagicMock()
        self.part_24_A.has_passphrase = False
        self.part_24_A.mnemonic_str = EXAMPLE_24_A
        self.part_24_A.mnemonic_list = EXAMPLE_24_A.split()
        self.part_24_A.wordlist = wordlist


    def test_valid_first_part(self):
        """ A valid part added to an empty list should pass. """
        is_valid, error = SeedXORValidator.validate_part(self.part_12_A, [])
        self.assertTrue(is_valid)
        self.assertIsNone(error)


    def test_valid_second_part(self):
        """ A second, valid, unique part of the same length should pass. """
        is_valid, error = SeedXORValidator.validate_part(self.part_12_B, [self.part_12_A])
        self.assertTrue(is_valid)
        self.assertIsNone(error)


    def test_rejects_part_with_passphrase(self):
        """ Parts with passphrases should be rejected. """
        self.part_12_A.has_passphrase = True
        is_valid, error = SeedXORValidator.validate_part(self.part_12_A, [])
        self.assertFalse(is_valid)
        self.assertEqual(error["title"], "Passphrase Not Allowed")


    def test_rejects_mismatched_mnemonic_length(self):
        """ Parts of different lengths should be rejected. """
        is_valid, error = SeedXORValidator.validate_part(self.part_24_A, [self.part_12_A])
        self.assertFalse(is_valid)
        self.assertEqual(error["title"], "Mnemonic Length Mismatch")


    def test_rejects_duplicate_part(self):
        """ An identical part should be rejected. """
        is_valid, error = SeedXORValidator.validate_part(self.part_12_A, [self.part_12_A])
        self.assertFalse(is_valid)
        self.assertEqual(error["title"], "Duplicate Part")
        self.assertIn("part #1", error["message"])


    def test_rejects_inverse_part(self):
        """ A binary inverse part should be rejected: XORing a part with its complement yields a known all-ones (zero-entropy) seed. """
        entropy_a = bip39.mnemonic_to_bytes(EXAMPLE_12_A)
        inverse_entropy = bytes(b ^ 0xFF for b in entropy_a)
        inverse_mnemonic_str = bip39.mnemonic_from_bytes(inverse_entropy)

        inverse_part = MagicMock()
        inverse_part.has_passphrase = False
        inverse_part.mnemonic_str = inverse_mnemonic_str
        inverse_part.mnemonic_list = inverse_mnemonic_str.split()
        inverse_part.wordlist = Seed.get_wordlist()

        is_valid, error = SeedXORValidator.validate_part(inverse_part, [self.part_12_A])
        self.assertFalse(is_valid)
        self.assertEqual(error["title"], "Seed Inversion")
        self.assertIn("binary inverse of part #1", error["message"])


    def test_validate_part_uses_seed_wordlist(self):
        """
        validate_part must pass the Seed's wordlist to bip39.mnemonic_to_bytes
        instead of relying on the English default.  Verifies the wordlist
        attribute is present and forwarded correctly.
        """
        # The mocks from setUp already have .wordlist set; verify validate_part
        # works with it (the inversion check reads .wordlist).
        is_valid, error = SeedXORValidator.validate_part(self.part_12_B, [self.part_12_A])
        self.assertTrue(is_valid)
        self.assertIsNone(error)

    def test_validate_part_handles_unparseable_mnemonic(self):
        """
        If bip39.mnemonic_to_bytes raises (e.g. wordlist mismatch), validate_part
        must return a clean error dict instead of propagating the exception.
        """
        bad_part = MagicMock()
        bad_part.has_passphrase = False
        bad_part.mnemonic_str = "totally invalid mnemonic words that do not exist"
        bad_part.mnemonic_list = "totally invalid mnemonic words that do not exist".split()
        # Use a wordlist that won't contain these words.
        bad_part.wordlist = Seed.get_wordlist()

        is_valid, error = SeedXORValidator.validate_part(bad_part, [])
        self.assertFalse(is_valid)
        self.assertEqual(error["title"], "Invalid Part")


class TestSeedXORValidatorCombinedSeed(unittest.TestCase):
    """
    Tests for SeedXORValidator.validate_combined_seed — catches degenerate
    XOR results (all-zero / all-ones entropy) that pass the BIP39 checksum
    but are known, worthless seeds.
    """

    def test_valid_combined_seed_passes(self):
        """ A normal combined seed should pass validation. """
        combined_mnemonic = combine_mnemonics_with_xor([EXAMPLE_12_A, EXAMPLE_12_B])
        seed = MagicMock()
        seed.mnemonic_str = " ".join(combined_mnemonic)
        seed.wordlist = Seed.get_wordlist()

        is_valid, error = SeedXORValidator.validate_combined_seed(seed)
        self.assertTrue(is_valid)
        self.assertIsNone(error)

    def test_zero_entropy_combined_seed_rejected(self):
        """ All-zero entropy (the 'abandon...about' seed) must be rejected. """
        seed = MagicMock()
        seed.mnemonic_str = ZERO_ENTROPY_MNEMONIC_12
        seed.wordlist = Seed.get_wordlist()

        is_valid, error = SeedXORValidator.validate_combined_seed(seed)
        self.assertFalse(is_valid)
        self.assertEqual(error["title"], "Zero Entropy Result")

    def test_all_ones_entropy_combined_seed_rejected(self):
        """ All-0xFF entropy (a known, worthless seed) must be rejected. """
        all_ones_entropy = bytes([0xFF] * 16)
        all_ones_mnemonic = bip39.mnemonic_from_bytes(all_ones_entropy)

        seed = MagicMock()
        seed.mnemonic_str = all_ones_mnemonic
        seed.wordlist = Seed.get_wordlist()

        is_valid, error = SeedXORValidator.validate_combined_seed(seed)
        self.assertFalse(is_valid)
        self.assertEqual(error["title"], "Known Seed Result")

