import random

from embit import bip39
from seedsigner.helpers import mnemonic_generation



def test_dice_rolls():
    """ Given 99 random dice rolls, the resulting mnemonic should be valid. """
    dice_rolls = ""
    for i in range(0, 99):
        # Do not need truly rigorous random for this test
        dice_rolls += str(random.randint(0, 5))

    mnemonic = mnemonic_generation.generate_mnemonic_from_dice(dice_rolls)
    assert bip39.mnemonic_is_valid(" ".join(mnemonic))



def test_calculate_checksum():
    """ Given an 11-word or 23-word mnemonic, the calculated checksum should yield a
        valid complete mnemonic.
    """
    # Test mnemonics from https://iancoleman.io/bip39/
    partial_mnemonic = "crawl focus rescue cable view pledge rather dinner cousin unfair day"
    mnemonic = mnemonic_generation.calculate_checksum(partial_mnemonic.split(" "), wordlist_language_code=bip39.WORDLIST)
    assert bip39.mnemonic_is_valid(" ".join(mnemonic))

    partial_mnemonic = "bubble father debate ankle injury fence mesh evolve section wet coyote violin pyramid flower rent arrow round clutch myth safe base skin mobile"
    mnemonic = mnemonic_generation.calculate_checksum(partial_mnemonic.split(" "), wordlist_language_code=bip39.WORDLIST)
    assert bip39.mnemonic_is_valid(" ".join(mnemonic))



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

