import hashlib
import unicodedata

from embit import bip39
from embit.bip39 import mnemonic_to_bytes, mnemonic_from_bytes
from typing import List

from seedsigner.models.seed import Seed


# Given 11/23 word partial mnemonic, returns a valid full mnemonic
# Given 12/24 random words, corrects the checksum bits in the last word to return a valid mnemonic
def calculate_checksum(partial_mnemonic: list, wordlist_language_code: str) -> List[str]:
    # Work on a copy of the input list
    mnemonic_copy = partial_mnemonic.copy()
    if len(mnemonic_copy) in [11, 23]:
        # 12-word seeds contribute 7 bits of entropy to the final word; 24-word seeds
        # contribute 3 bits. But we don't have any partial entropy bits to use to help us
        # create the final word. So just default to filling those missing values with zeroes
        # ("abandon" is word 0000, so effectively inserts zeroes).
        mnemonic_copy.append("abandon")
    elif len(mnemonic_copy) not in [12, 24]:
        raise Exception("Pass in a 11-, 12-, 23-, or 24-word mnemonic")

    # Convert the resulting mnemonic to bytes, but we `ignore_checksum` validation because
    # we have to assume it's incorrect (either hard coded, or random from the user); we'll
    # fix that next.
    mnemonic_bytes = bip39.mnemonic_to_bytes(unicodedata.normalize("NFKD", " ".join(mnemonic_copy)), ignore_checksum=True, wordlist=Seed.get_wordlist(wordlist_language_code))

    # This function will convert the bytes back into a mnemonic, but it will also
    # calculate the proper checksum bits while doing so. For a 12-word seed it will just
    # overwrite the last 4 bits from the above result with the checksum; for a 24-word
    # seed it'll overwrite the last 8 bits.
    return bip39.mnemonic_from_bytes(mnemonic_bytes).split()



def generate_mnemonic_from_bytes(entropy_bytes) -> List[str]:
    return bip39.mnemonic_from_bytes(entropy_bytes).split()



def generate_mnemonic_from_dice(roll_data: str) -> List[str]:
    entropy_bytes = hashlib.sha256(roll_data.encode()).digest()

    if len(roll_data) == 50:
        # 12-word mnemonic; only use 128bits / 16 bytes
        entropy_bytes = entropy_bytes[:16]

    # Return as a list
    return bip39.mnemonic_from_bytes(entropy_bytes).split()



# Note: This currently isn't being used since we're now chaining hashed bytes for the
#   image-based entropy and aren't just ingesting a single image.
def generate_mnemonic_from_image(image) -> List[str]:
    import hashlib
    hash = hashlib.sha256(image.tobytes())

    # Return as a list
    return bip39.mnemonic_from_bytes(hash.digest()).split()
