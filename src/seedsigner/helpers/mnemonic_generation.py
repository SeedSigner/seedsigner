import hashlib
import unicodedata

from embit import bip39
from seedsigner.models.settings_definition import SettingsConstants
from seedsigner.models.seed import Seed

"""
    This is SeedSigner's internal mnemonic generation utility.
     
    It can also be run as an independently-executable CLI to facilitate external
    verification of SeedSigner's results for a given input entropy.

    see: docs/dice_verification.md (the "Command Line Tool" section).
"""

DICE__NUM_ROLLS__12WORD = 50
DICE__NUM_ROLLS__24WORD = 99

# Explicitly separates combined-source derivation from every existing
# SeedSigner seed-generation path. Increment the version if the framing or
# derivation is ever changed.
CAMERA_DICE_DOMAIN = b"SeedSigner camera+dice v1"



def calculate_checksum(mnemonic: list | str, wordlist_language_code: str = SettingsConstants.WORDLIST_LANGUAGE__ENGLISH) -> list[str]:
    """
        Provide 12- or 24-word mnemonic, returns complete mnemonic w/checksum as a list.

        Mnemonic may be a list of words or a string of words separated by spaces or commas.

        If 11- or 23-words are provided, append word `0000` to end of list as temp final
        word.
    """
    if type(mnemonic) == str:
        import re
        # split on commas or spaces
        mnemonic = re.findall(r'[^,\s]+', mnemonic)

    if len(mnemonic) in [11, 23]:
        temp_final_word = Seed.get_wordlist(wordlist_language_code)[0]
        mnemonic.append(temp_final_word)

    if len(mnemonic) not in [12, 24]:
        raise Exception("Pass in a 12- or 24-word mnemonic")
    
    # Work on a copy of the input list
    mnemonic_copy = mnemonic.copy()

    # Convert the resulting mnemonic to bytes, but we `ignore_checksum` validation
    # because we assume it's incorrect since we either let the user select their own
    # final word OR we injected the 0000 word from the wordlist.
    mnemonic_bytes = bip39.mnemonic_to_bytes(unicodedata.normalize("NFKD", " ".join(mnemonic_copy)), ignore_checksum=True, wordlist=Seed.get_wordlist(wordlist_language_code))

    # This function will convert the bytes back into a mnemonic, but it will also
    # calculate the proper checksum bits while doing so. For a 12-word seed it will just
    # overwrite the last 4 bits from the above result with the checksum; for a 24-word
    # seed it'll overwrite the last 8 bits.
    return bip39.mnemonic_from_bytes(mnemonic_bytes).split()



def generate_mnemonic_from_bytes(entropy_bytes, wordlist_language_code: str = SettingsConstants.WORDLIST_LANGUAGE__ENGLISH) -> list[str]:
    return bip39.mnemonic_from_bytes(entropy_bytes, wordlist=Seed.get_wordlist(wordlist_language_code)).split()



def generate_mnemonic_from_dice(roll_data: str, wordlist_language_code: str = SettingsConstants.WORDLIST_LANGUAGE__ENGLISH) -> list[str]:
    """
        Takes a string of 50 or 99 dice rolls and returns a 12- or 24-word mnemonic.

        Uses the iancoleman.io/bip39 and bitcoiner.guide/seed "Base 10" or "Hex" mode approach:
        * dice rolls are treated as string data.
        * hashed via SHA256.

        Important note: This method is NOT compatible with iancoleman's "Dice" mode.
    """
    entropy_bytes = hashlib.sha256(roll_data.encode()).digest()

    if len(roll_data) == DICE__NUM_ROLLS__12WORD:
        # 12-word mnemonic; only use 128bits / 16 bytes
        entropy_bytes = entropy_bytes[:16]

    # Return as a list
    return bip39.mnemonic_from_bytes(entropy_bytes, wordlist=Seed.get_wordlist(wordlist_language_code)).split()



def combine_camera_and_dice_entropy(camera_entropy_digest: bytes | bytearray, roll_data: str) -> bytes:
    """
        Combine independently collected camera and dice entropy into one
        domain-separated 256-bit digest.

        Inputs are length-framed so the byte stream is unambiguous. The camera
        input must be the full 32-byte digest of SeedSigner's existing camera
        hash chain; the dice input remains the exact entered roll string.
    """
    if len(camera_entropy_digest) != 32:
        raise ValueError("Camera entropy digest must be exactly 32 bytes")
    if len(roll_data) not in [DICE__NUM_ROLLS__12WORD, DICE__NUM_ROLLS__24WORD]:
        raise ValueError(
            f"Dice input must contain {DICE__NUM_ROLLS__12WORD} or "
            f"{DICE__NUM_ROLLS__24WORD} rolls"
        )
    if any(roll not in "123456" for roll in roll_data):
        raise ValueError("Dice input contains an invalid face")

    roll_bytes = roll_data.encode("ascii")
    digest = hashlib.sha256()
    digest.update(CAMERA_DICE_DOMAIN)
    digest.update(len(camera_entropy_digest).to_bytes(2, "big"))
    digest.update(camera_entropy_digest)
    digest.update(len(roll_bytes).to_bytes(2, "big"))
    digest.update(roll_bytes)
    return digest.digest()



def generate_mnemonic_from_camera_and_dice(
    camera_entropy_digest: bytes | bytearray,
    roll_data: str,
    wordlist_language_code: str = SettingsConstants.WORDLIST_LANGUAGE__ENGLISH,
) -> list[str]:
    """Generate a BIP-39 mnemonic from the combined camera+dice digest."""
    entropy_bytes = combine_camera_and_dice_entropy(camera_entropy_digest, roll_data)

    if len(roll_data) == DICE__NUM_ROLLS__12WORD:
        entropy_bytes = entropy_bytes[:16]

    return bip39.mnemonic_from_bytes(
        entropy_bytes,
        wordlist=Seed.get_wordlist(wordlist_language_code),
    ).split()



def generate_mnemonic_from_coin_flips(coin_flips: str, wordlist_language_code: str = SettingsConstants.WORDLIST_LANGUAGE__ENGLISH) -> list[str]:
    """
        Takes a string of 128 or 256 0s and 1s and returns a 12- or 24-word mnemonic.

        Uses the iancoleman.io/bip39 and bitcoiner.guide/seed "Binary" mode approach:
        * binary digit stream is treated as string data.
        * hashed via SHA256.
    """
    entropy_bytes = hashlib.sha256(coin_flips.encode()).digest()

    if len(coin_flips) == 128:
        # 12-word mnemonic; only use 128bits / 16 bytes
        entropy_bytes = entropy_bytes[:16]

    # Return as a list
    return bip39.mnemonic_from_bytes(entropy_bytes, wordlist=Seed.get_wordlist(wordlist_language_code)).split()



def get_partial_final_word(coin_flips: str, wordlist_language_code: str = SettingsConstants.WORDLIST_LANGUAGE__ENGLISH) -> str:
    """ Look up the partial final word for the given coin flips.
        7 coin flips: 0101010 + **** where the final 4 bits will be replaced with the checksum
        3 coin flips: 010 + ******** where the final 8 bits will be replaced with the checksum
    """
    binary_string = coin_flips + "0" * (11 - len(coin_flips))
    wordlist_index = int(binary_string, 2)

    return Seed.get_wordlist(wordlist_language_code)[wordlist_index]
