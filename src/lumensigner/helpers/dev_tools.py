import os
from typing import List

from lumensigner.models import Seed

DEV_MODE_ENABLED = os.getenv("LUMEN_SIGNER_DEV_MODE", "0") == "1"

# Generate the mnemonic
DEV_MNEMONIC = (
    "type agree captain cake screen wait maximum attack boost humble penalty transfer"
)


def set_dev_mnemonic(
    seeds: List[Seed], wordlist_language_code: str, mnemonic: str = DEV_MNEMONIC
):
    print(
        "Setting dev mnemonic, this should only be used for development!\n"
        f"mnemonic: {mnemonic}\n"
    )
    mnemonic = mnemonic.split(" ")
    seed = Seed(
        mnemonic,
        wordlist_language_code=wordlist_language_code,
    )
    seeds.append(seed)
