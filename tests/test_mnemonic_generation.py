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
    mnemonic = mnemonic_generation.calculate_checksum(partial_mnemonic.split(" "))
    assert bip39.mnemonic_is_valid(" ".join(mnemonic))

    partial_mnemonic = "bubble father debate ankle injury fence mesh evolve section wet coyote violin pyramid flower rent arrow round clutch myth safe base skin mobile"
    mnemonic = mnemonic_generation.calculate_checksum(partial_mnemonic.split(" "))
    assert bip39.mnemonic_is_valid(" ".join(mnemonic))

