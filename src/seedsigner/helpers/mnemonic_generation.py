from embit import bip39
from embit.bip39 import mnemonic_to_bytes, mnemonic_from_bytes
import unicodedata
import hashlib


# Given 11/23 word partial mnemonic, returns a valid full mnemonic
# Given 12/24 random words, corrects the checksum bits in the last word to return a valid mnemonic
def calculate_checksum(partial_mnemonic: list, wordlist):
    # Work on a copy of the input list
    mnemonic_copy = partial_mnemonic.copy()
    if len(mnemonic_copy) in [11, 23]:
        mnemonic_copy.append("abandon")
    elif len(mnemonic_copy) not in [12, 24]:
        raise Exception("Pass in a 11-, 12-, 23-, or 24-word mnemonic")

    # Ignores the final checksum word and recalcs
    mnemonic_bytes = bip39.mnemonic_to_bytes(unicodedata.normalize("NFKD", " ".join(mnemonic_copy)), ignore_checksum=True, wordlist=wordlist)

    # Return as a list
    return bip39.mnemonic_from_bytes(mnemonic_bytes).split()



def generate_mnemonic_from_bytes(entropy_bytes):
    # Return as a list
    return bip39.mnemonic_from_bytes(entropy_bytes).split()



def generate_mnemonic_from_dice(roll_data: str):
    entropy_bytes = hashlib.sha256(roll_data.encode()).digest()

    # Return as a list
    return bip39.mnemonic_from_bytes(entropy_bytes).split()



# Note: This currently isn't being used since we're now chaining hashed bytes for the
#   image-based entropy and aren't just ingesting a single image.
def generate_mnemonic_from_image(image):
    hash = hashlib.sha256(image.tobytes())

    # Return as a list
    return bip39.mnemonic_from_bytes(hash.digest()).split()
