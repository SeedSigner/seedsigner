import pytest
import random

from embit import bip39
from seedsigner.helpers import mnemonic_generation
from seedsigner.models.settings_definition import SettingsConstants



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



def test_coin_flips():
    """ Given random coin flips, the resulting mnemonic should be valid. """
    coin_flips = ""
    for i in range(0, mnemonic_generation.COIN__NUM_FLIPS__24WORD):
        # Do not need truly rigorous random for this test
        coin_flips += str(random.randint(0, 1))

    mnemonic = mnemonic_generation.generate_mnemonic_from_coin_flips(coin_flips)

    assert len(mnemonic) == 24
    assert bip39.mnemonic_is_valid(" ".join(mnemonic))

    coin_flips = ""
    for i in range(0, mnemonic_generation.COIN__NUM_FLIPS__12WORD):
        # Do not need truly rigorous random for this test
        coin_flips += str(random.randint(0, 1))

    mnemonic = mnemonic_generation.generate_mnemonic_from_coin_flips(coin_flips)
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



def test_256_coin_flips():
    """ 256 coin flips input should yield the same 24-word mnemonic as iancoleman.io/bip39 """
    # Check "Show entropy details", paste in coin flip sequence, click "Binary", select "Mnemonic Length" as "Use Raw Entropy (3 words per 32 bits)"
    coin_flips = "1010101010101110110001000000001100100011000000000011000000001001110000000000000010000000000110000001110010110010000100110011001010101010101011101100010000000011001000110000000000110000000010011100000000000000100000000001100000011100101100100001001100110010"
    expected = "primary involve absorb ecology adapt agent abandon avoid blossom tortoise luggage grab priority ginger arrive gas copy evoke ability ability limb flip error employ"

    mnemonic = mnemonic_generation.generate_mnemonic_from_coin_flips(coin_flips)
    actual = " ".join(mnemonic)
    assert bip39.mnemonic_is_valid(actual)
    assert actual == expected

    coin_flips = "0000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000"
    expected = "abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon art"

    mnemonic = mnemonic_generation.generate_mnemonic_from_coin_flips(coin_flips)
    actual = " ".join(mnemonic)
    assert bip39.mnemonic_is_valid(actual)
    assert actual == expected

    coin_flips = "1111000101001010101010101010010000100111100000101010000101101101111000000101110101010010101010010101010001001011010101111101001001000010111110101011111101010010011010101001010111010100000011111001010010101101001010010101010010101010100101010010100101001001"
    expected = "vanish fetch poverty excuse claw report lift prevent power pelican sting pig cook garden endless famous staff lake clip famous enjoy enhance pioneer click"

    mnemonic = mnemonic_generation.generate_mnemonic_from_coin_flips(coin_flips)
    actual = " ".join(mnemonic)
    assert bip39.mnemonic_is_valid(actual)
    assert actual == expected



def test_128_coin_flips():
    """ 128 coin flips input should yield the same 12-word mnemonic as iancoleman.io/bip39 """
    # Check "Show entropy details", paste in coin flip sequence, click "Binary", select "Mnemonic Length" as "Use Raw Entropy (3 words per 32 bits)"
    coin_flips = "10101010101011101100010000000011001000110000000000110000000010011100000000000000100000000001100000011100101100100001001100110010"
    expected = "primary involve absorb ecology adapt agent abandon avoid blossom tortoise luggage grape"
    mnemonic = mnemonic_generation.generate_mnemonic_from_coin_flips(coin_flips)
    actual = " ".join(mnemonic)
    assert bip39.mnemonic_is_valid(actual)
    assert actual == expected

    coin_flips = "00000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000"
    expected = "abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon about"
    mnemonic = mnemonic_generation.generate_mnemonic_from_coin_flips(coin_flips)
    actual = " ".join(mnemonic)
    assert bip39.mnemonic_is_valid(actual)
    assert actual == expected

    coin_flips = "10100010100101010110101011010001010011101011111010010101010010101010101010010100101010101001010101010110101011111111000001001000"
    expected = "penalty prize reform output true pipe prevent next next rely winter museum"
    mnemonic = mnemonic_generation.generate_mnemonic_from_coin_flips(coin_flips)
    actual = " ".join(mnemonic)
    assert bip39.mnemonic_is_valid(actual)
    assert actual == expected

    
def test_coin_flips_invalid_input():
    """
        Should raise a ValueError if coin_flips contains invalid characters or has an invalid length.
    """
    # Test invalid characters
    with pytest.raises(ValueError) as e:
        invalid_coin_flips = "01012" + "0" * 123  # 128 chars with a '2'
        mnemonic_generation.generate_mnemonic_from_coin_flips(invalid_coin_flips)
    assert "only contain '0' or '1'" in str(e)

    with pytest.raises(ValueError) as e:
        invalid_coin_flips = "01ab" + "0" * 252  # 256 chars with 'a' and 'b'
        mnemonic_generation.generate_mnemonic_from_coin_flips(invalid_coin_flips)
    assert "only contain '0' or '1'" in str(e)

    # Test invalid lengths
    with pytest.raises(ValueError) as e:
        invalid_coin_flips = "0101"  # Too short (4 chars)
        mnemonic_generation.generate_mnemonic_from_coin_flips(invalid_coin_flips)
    assert "128 or 256 bits" in str(e)

    with pytest.raises(ValueError) as e:
        invalid_coin_flips = "0" * 127  # Too short (127 chars)
        mnemonic_generation.generate_mnemonic_from_coin_flips(invalid_coin_flips)
    assert "128 or 256 bits" in str(e)

    with pytest.raises(ValueError) as e:
        invalid_coin_flips = "0" * 129  # Too long for 128, too short for 256
        mnemonic_generation.generate_mnemonic_from_coin_flips(invalid_coin_flips)
    assert "128 or 256 bits" in str(e)

    with pytest.raises(ValueError) as e:
        invalid_coin_flips = "0" * 255  # Too short for 256
        mnemonic_generation.generate_mnemonic_from_coin_flips(invalid_coin_flips)
    assert "128 or 256 bits" in str(e)