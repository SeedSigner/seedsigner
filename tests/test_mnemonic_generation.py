import pytest
import random

from embit import bip39
from seedsigner.helpers import mnemonic_generation
from seedsigner.models.settings_definition import SettingsConstants



def test__get_wordlist():
    """ Currently, BIP39 engish wordlist is supported, exclusively """
    assert mnemonic_generation._get_wordlist("en") == bip39.WORDLIST

    with pytest.raises(Exception) as e:
        mnemonic_generation._get_wordlist("de")
    assert "Unrecognized wordlist_language_code" in str(e)



def test_dice_rolls():
    """ Given random dice rolls, the resulting mnemonic should be valid. """
    dice_rolls = ""
    for i in range(0, 99):
        # Do not need truly rigorous random for this test
        dice_rolls += str(random.randint(1, 6))

    mnemonic = mnemonic_generation.generate_mnemonic_from_dice(dice_rolls)

    assert len(mnemonic) == 24
    assert bip39.mnemonic_is_valid(" ".join(mnemonic))

    dice_rolls = ""
    for i in range(0, mnemonic_generation.DICE__NUM_ROLLS__12WORD):
        # Do not need truly rigorous random for this test
        dice_rolls += str(random.randint(1, 6))

    mnemonic = mnemonic_generation.generate_mnemonic_from_dice(dice_rolls)
    assert len(mnemonic) == 12
    assert bip39.mnemonic_is_valid(" ".join(mnemonic))



def test_calculate_checksum_input_type():
    """
        Given an 11-word or 23-word mnemonic, the calculated checksum should yield a
        valid complete mnemonic.
        
        calculate_checksum should accept the mnemonic as:
        * a list of strings
        * string: "A B C", "A, B, C", "A,B,C"
    """
    # Test mnemonics from https://iancoleman.io/bip39/
    def _try_all_input_formats(partial_mnemonic: str):
        # List of strings
        mnemonic = mnemonic_generation.calculate_checksum(partial_mnemonic.split(" "))
        assert bip39.mnemonic_is_valid(" ".join(mnemonic))

        # Comma-separated string
        mnemonic = mnemonic_generation.calculate_checksum(partial_mnemonic.replace(" ", ","))
        assert bip39.mnemonic_is_valid(" ".join(mnemonic))

        # Comma-separated string w/space
        mnemonic = mnemonic_generation.calculate_checksum(partial_mnemonic.replace(" ", ", "))
        assert bip39.mnemonic_is_valid(" ".join(mnemonic))

        # Space-separated string
        mnemonic = mnemonic_generation.calculate_checksum(partial_mnemonic)
        assert bip39.mnemonic_is_valid(" ".join(mnemonic))

    partial_mnemonic = "crawl focus rescue cable view pledge rather dinner cousin unfair day"
    _try_all_input_formats(partial_mnemonic)

    partial_mnemonic = "bubble father debate ankle injury fence mesh evolve section wet coyote violin pyramid flower rent arrow round clutch myth safe base skin mobile"
    _try_all_input_formats(partial_mnemonic)



def test_calculate_checksum_invalid_mnemonics():
    """
        Should raise an Exception on a mnemonic that is invalid due to length or using invalid words.
    """
    with pytest.raises(Exception) as e:
        # Mnemonic is too short: 10 words instead of 11
        partial_mnemonic = "abandon " * 9 + "about"
        mnemonic_generation.calculate_checksum(partial_mnemonic)
    assert "12- or 24-word" in str(e)

    with pytest.raises(Exception) as e:
        # Valid mnemonic but unsupported length
        mnemonic = "devote myth base logic dust horse nut collect buddy element eyebrow visit empty dress jungle"
        mnemonic_generation.calculate_checksum(mnemonic)
    assert "12- or 24-word" in str(e)

    with pytest.raises(Exception) as e:
        # Mnemonic is too short: 22 words instead of 23
        partial_mnemonic = "abandon " * 21 + "about"
        mnemonic_generation.calculate_checksum(partial_mnemonic)
    assert "12- or 24-word" in str(e)

    with pytest.raises(ValueError) as e:
        # Invalid BIP-39 word
        partial_mnemonic = "foobar " * 11 + "about"
        mnemonic_generation.calculate_checksum(partial_mnemonic)
    assert "not in the dictionary" in str(e)



def test_calculate_checksum_with_default_final_word():
    """ 11-word and 23-word mnemonics use word `0000` as a temp final word to complete
        the mnemonic.
    """
    partial_mnemonic = "crawl focus rescue cable view pledge rather dinner cousin unfair day"
    mnemonic1 = mnemonic_generation.calculate_checksum(partial_mnemonic)

    partial_mnemonic += " abandon"
    mnemonic2 = mnemonic_generation.calculate_checksum(partial_mnemonic)
    assert mnemonic1 == mnemonic2

    partial_mnemonic = "bubble father debate ankle injury fence mesh evolve section wet coyote violin pyramid flower rent arrow round clutch myth safe base skin mobile"
    mnemonic1 = mnemonic_generation.calculate_checksum(partial_mnemonic)

    partial_mnemonic += " abandon"
    mnemonic2 = mnemonic_generation.calculate_checksum(partial_mnemonic)
    assert mnemonic1 == mnemonic2



def test_generate_mnemonic_from_bytes():
    """
        Should generate a valid BIP-39 mnemonic from entropy bytes
    """
    # From iancoleman.io
    entropy = "3350f6ac9eeb07d2c6209932808aa7f6"
    expected_mnemonic = "crew marble private differ race truly blush basket crater affair prepare unique".split()
    mnemonic = mnemonic_generation.generate_mnemonic_from_bytes(bytes.fromhex(entropy))
    assert mnemonic == expected_mnemonic

    entropy = "5bf41629fce815c3570955e8f45422abd7e2234141bd4d7ec63b741043b98cad"
    expected_mnemonic = "fossil pass media what life ticket found click trophy pencil anger fish lawsuit balance agree dash estate wage mom trial aerobic system crawl review".split()
    mnemonic = mnemonic_generation.generate_mnemonic_from_bytes(bytes.fromhex(entropy))
    assert mnemonic == expected_mnemonic



def test_verify_against_coldcard_sample():
    """ https://coldcard.com/docs/verifying-dice-roll-math """
    dice_rolls = "123456"
    expected = "mirror reject rookie talk pudding throw happy era myth already payment own sentence push head sting video explain letter bomb casual hotel rather garment"

    mnemonic = mnemonic_generation.generate_mnemonic_from_dice(dice_rolls)
    actual = " ".join(mnemonic)
    assert bip39.mnemonic_is_valid(actual)
    assert actual == expected



def test_known_dice_rolls():
    """ Given 99 known dice rolls, the resulting mnemonic should be valid and match the expected. """
    dice_rolls = "522222222222222222222222222222222222222222222555555555555555555555555555555555555555555555555555555"
    expected = "resource timber firm banner horror pupil frozen main pear direct pioneer broken grid core insane begin sister pony end debate task silk empty curious"

    mnemonic = mnemonic_generation.generate_mnemonic_from_dice(dice_rolls)
    actual = " ".join(mnemonic)
    assert bip39.mnemonic_is_valid(actual)
    assert actual == expected

    dice_rolls = "222222222222222222222222222222222222222222222555555555555555555555555555555555555555555555555555555"
    expected = "garden uphold level clog sword globe armor issue two cute scorpion improve verb artwork blind tail raw butter combine move produce foil feature wave"

    mnemonic = mnemonic_generation.generate_mnemonic_from_dice(dice_rolls)
    actual = " ".join(mnemonic)
    assert bip39.mnemonic_is_valid(actual)
    assert actual == expected

    dice_rolls = "222222222222222222222222222222222222222222222555555555555555555555555555555555555555555555555555556"
    expected = "lizard broken love tired depend eyebrow excess lonely advance father various cram ignore panic feed plunge miss regret boring unique galaxy fan detail fly"

    mnemonic = mnemonic_generation.generate_mnemonic_from_dice(dice_rolls)
    actual = " ".join(mnemonic)
    assert bip39.mnemonic_is_valid(actual)
    assert actual == expected



def test_50_dice_rolls():
    """ 50 dice roll input should yield the same 12-word mnemonic as iancoleman.io/bip39 """
    # Check "Show entropy details", paste in dice_rolls sequence, click "Hex", select "Mnemonic Length" as "12 Words"
    dice_rolls = "12345612345612345612345612345612345612345612345612"
    expected = "unveil nice picture region tragic fault cream strike tourist control recipe tourist"
    mnemonic = mnemonic_generation.generate_mnemonic_from_dice(dice_rolls)
    actual = " ".join(mnemonic)
    assert bip39.mnemonic_is_valid(actual)
    assert actual == expected

    dice_rolls = "11111111111111111111111111111111111111111111111111"
    expected = "diet glad hat rural panther lawsuit act drop gallery urge where fit"
    mnemonic = mnemonic_generation.generate_mnemonic_from_dice(dice_rolls)
    actual = " ".join(mnemonic)
    assert bip39.mnemonic_is_valid(actual)
    assert actual == expected

    dice_rolls = "66666666666666666666666666666666666666666666666666"
    expected = "senior morning song proud recycle toy search apple trigger lend vibrant arrest"
    mnemonic = mnemonic_generation.generate_mnemonic_from_dice(dice_rolls)
    actual = " ".join(mnemonic)
    assert bip39.mnemonic_is_valid(actual)
    assert actual == expected



# TODO: SINCE NOT YET IMPLEMENTED, CONSIDER IF WE WANT TO SUPPORT THIS NON-REVERSIBLE ALGO, rather than 8bits = 1byte
def test_mnemnonic_from_coin_flips():
    """ test 128 coin flips to 12-word mnemonic, and 256 coin flips to 24-word mnemnonic """
    coin_flips = "00110011010100001111011010101100100111101110101100000111110100101100011000100000100110010011001010000000100010101010011111110110"
    expected = "license state october hockey seed piano buzz hub curious boss regular zero"
    assert mnemonic_generation.generate_mnemonic_from_coin_flips(coin_flips) == expected.split()

    coin_flips = "101101111110100000101100010100111111100111010000001010111000011010101110000100101010101111010001111010001010100001000101010101111010111111000100010001101000001010000011011110101001101011111101100011000111011011101000001000001000011101110011000110010101101"
    expected = "town trap family monkey tongue vocal fluid unable tattoo hour approve legal unusual energy away copy grow coconut spawn violin mean author appear calm"
    assert mnemonic_generation.generate_mnemonic_from_coin_flips(coin_flips) == expected.split()



def test_get_partial_final_word():
    """ test that we get a final word given some coin_flips """
    assert mnemonic_generation.get_partial_final_word("10101010110") == "print"
    assert mnemonic_generation.get_partial_final_word("1010101011") == "print"
    assert mnemonic_generation.get_partial_final_word("101010101") == "pride"
    assert mnemonic_generation.get_partial_final_word("10101010") == "present"
    assert mnemonic_generation.get_partial_final_word("1010101") == "present"
    assert mnemonic_generation.get_partial_final_word("101010") == "pool"
    assert mnemonic_generation.get_partial_final_word("10101") == "pool"
    assert mnemonic_generation.get_partial_final_word("1010") == "parade"
    assert mnemonic_generation.get_partial_final_word("101") == "parade"
    assert mnemonic_generation.get_partial_final_word("10") == "length"
    assert mnemonic_generation.get_partial_final_word("1") == "length"

    # TODO: IS THIS OK OR SHOULD THE FIRST TWO ASSERTS FAIL???
    # test unexpected input fails
    assert mnemonic_generation.get_partial_final_word("") == "abandon"
    assert mnemonic_generation.get_partial_final_word("0000000000000000000000000000") == "abandon"
    with pytest.raises(Exception) as e:
        mnemonic_generation.get_partial_final_word("1000000000000000000000000000")



# TODO: SHOULD THIS TEST AND THE IMPLEMENTATION BE REMOVED (doesnt even support 12words)???
def test_generate_mnemonic_from_image():
    """ test image entropy, which is no longer the same algo """
    from PIL import Image
    expected = "note annual knife knee mechanic patient kid element cool able odor chaos humor fold fly harbor zone muscle govern cruel betray romance season maid"
    assert mnemonic_generation.generate_mnemonic_from_image(Image.new("RGB", (1024, 768)))

