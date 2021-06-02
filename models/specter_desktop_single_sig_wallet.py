from specter_desktop_multisig_wallet import SpecterDesktopMultisigWallet
from wallet import Wallet

# External Dependencies
from embit.bip39 import mnemonic_to_bytes
from embit.bip39 import mnemonic_from_bytes
from embit import bip39
from embit import script
from embit import bip32
from embit import psbt
from embit.networks import NETWORKS
from embit import ec
from io import BytesIO
from binascii import unhexlify, hexlify, a2b_base64, b2a_base64
import re
import textwrap

class SpecterDesktopSingleSigWallet(SpecterDesktopMultisigWallet):

    def __init__(self, current_network = "main", hardened_derivation = "m/84h/0h/0h") -> None:
        if current_network == "main":
            Wallet.__init__(self, current_network, "m/84h/0h/0h")
        elif current_network == "test":
            Wallet.__init__(self, current_network, "m/84h/1h/0h")
        else:
            Wallet.__init__(self, current_network, hardened_derivation)

    def get_name(self) -> str:
        return "Specter Single Sig"

    def set_network(self, network) -> bool:
        if network == "main":
            self.current_network = "main"
            self.hardened_derivation = "m/84h/0h/0h"
        elif network == "test":
            self.current_network = "test"
            self.hardened_derivation = "m/84h/1h/0h"
        else:
            return False

        return True

