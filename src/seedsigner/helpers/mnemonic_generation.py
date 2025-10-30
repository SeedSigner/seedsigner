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



# Note: This currently isn't being used since we're now chaining hashed bytes for the
#   image-based entropy and aren't just ingesting a single image.
def generate_mnemonic_from_image(image, wordlist_language_code: str = SettingsConstants.WORDLIST_LANGUAGE__ENGLISH) -> list[str]:
    import hashlib
    hash = hashlib.sha256(image.tobytes())

    # Return as a list
    return bip39.mnemonic_from_bytes(hash.digest(), wordlist=Seed.get_wordlist(wordlist_language_code)).split()


def combine_mnemonics_with_xor(mnemonics: list[str], wordlist_language_code: str = SettingsConstants.WORDLIST_LANGUAGE__ENGLISH) -> list[str]:
    """
    Combine multiple BIP39 mnemonic seed phrases using XOR operation (SeedXOR).

    The process works by XOR-ing the entropy (random data) of each mnemonic together.
    When you XOR the shares back together, you get the original seed phrase.
    
    Args:
        mnemonics: List of mnemonic seed phrases (as strings) to combine
        wordlist_language_code: Language code for the BIP39 wordlist (default: English)
    
    Returns:
        Combined mnemonic as a list of words
        
    Raises:
        ValueError: If mnemonics list is empty, contains invalid mnemonics, 
                   or mnemonics have different entropy lengths
    """
    if not mnemonics:
        raise ValueError("Mnemonic list cannot be empty")
        
    wordlist = Seed.get_wordlist(wordlist_language_code)
    
    try:
        entropy_list = [bip39.mnemonic_to_bytes(" ".join(mnemonic) if isinstance(mnemonic, list) else mnemonic, wordlist=wordlist) 
                       for mnemonic in mnemonics]
    except Exception as e:
        raise ValueError(f"Invalid mnemonic: {str(e)}")
    
    if len(set(len(entropy) for entropy in entropy_list)) != 1:
        raise ValueError("All mnemonics must generate entropy of the same length")
    
    combined_entropy = bytes(len(entropy_list[0]))
    for entropy in entropy_list:
        combined_entropy = bytes(a ^ b for a, b in zip(combined_entropy, entropy))
    
    return bip39.mnemonic_from_bytes(combined_entropy, wordlist=wordlist).split()
