from . import Wallet

from seedsigner.helpers import Buttons, B, CameraProcess, CameraPoll, QR
from seedsigner.helpers.bcur import bcur_decode, cbor_decode, bc32decode, bc32encode, cbor_encode, bcur_encode
from seedsigner.helpers.ur2.ur_decoder import URDecoder
from seedsigner.helpers.ur2.ur_encoder import UREncoder
from seedsigner.helpers.ur2.cbor_lite import CBOREncoder
from seedsigner.helpers.ur2.ur import UR
from seedsigner.views import View

# External Dependencies
import time
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

class GenericUR2Wallet(Wallet):

    def __init__(self, current_network = "main", qr_density = Wallet.QRMEDIUM, policy = "PKWSH") -> None:
        Wallet.__init__(self, current_network, qr_density, policy)

    def get_name(self) -> str:
        return "UR 2.0 Generic"

    def set_network(self, network) -> bool:
        if network == "main":
            self.current_network = "main"
            self.hardened_derivation = "m/48h/0h/0h/2h"
        elif network == "test":
            self.current_network = "test"
            self.hardened_derivation = "m/48h/1h/0h/2h"
        else:
            return False

        return True

    def set_qr_density(self, density):
        self.cur_qr_density = density
        if density == Wallet.QRLOW:
            self.qrsize = 60
        elif density == Wallet.QRMEDIUM:
            self.qrsize = 80
        elif density == Wallet.QRHIGH:
            self.qrsize = 120