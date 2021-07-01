from . import Wallet
from seedsigner.helpers import QR

# External Dependencies
from embit import bip32, bip39, ec, psbt, script
from embit.bip39 import mnemonic_to_bytes, mnemonic_from_bytes
from embit.networks import NETWORKS
from io import BytesIO
from binascii import unhexlify, hexlify, a2b_base64, b2a_base64
import re

class SpecterDesktopMultisigWallet(Wallet):

    def __init__(self, current_network = "main", qr_density = Wallet.QRMEDIUM, hardened_derivation = "m/48h/0h/0h/2h") -> None:
        if current_network == "main":
            Wallet.__init__(self, current_network, qr_density, "m/48h/0h/0h/2h")
        elif current_network == "test":
            Wallet.__init__(self, current_network, qr_density, "m/48h/1h/0h/2h")
        else:
            Wallet.__init__(self, current_network, qr_density, hardened_derivation)

    def get_name(self) -> str:
        return "Specter Desktop"

    def import_qr(self) -> str:
        xpubstring = "[%s%s]%s" % (
             hexlify(self.fingerprint).decode('utf-8'),
             self.hardened_derivation[1:],
             self.bip48_xpub.to_base58(NETWORKS[self.current_network]["Zpub"]))

        return xpubstring

    def parse_psbt(self, raw_psbt) -> bool:

        base64_psbt = a2b_base64(raw_psbt)
        self.tx = psbt.PSBT.parse(base64_psbt)

        (self.inp_amount, policy) = self.input_amount(self.tx)
        (self.change, self.fee, self.spend, self.destinationaddress) = self.change_fee_spend_amounts(self.tx, self.inp_amount, policy, self.current_network)

        return True

    def sign_transaction(self) -> (str):

        # sign the transaction
        self.tx.sign_with(self.root)

        #added section to trim psbt
        trimmed_psbt = psbt.PSBT(self.tx.tx)
        sigsEnd = 0
        for i, inp in enumerate(self.tx.inputs):
            sigsEnd += len(list(inp.partial_sigs.keys()))
            trimmed_psbt.inputs[i].partial_sigs = inp.partial_sigs

        raw_trimmed_signed_psbt = trimmed_psbt.serialize()

        # convert to base64
        b64_psbt = b2a_base64(raw_trimmed_signed_psbt)
        # somehow b2a ends with \n...
        if b64_psbt[-1:] == b"\n":
            b64_psbt = b64_psbt[:-1]

        return b64_psbt.decode('utf-8')

    def total_frames_parse(data) -> int:
        if re.search("^p(\d+)of(\d+) ", data, re.IGNORECASE) != None:
            return int(re.search("^p(\d+)of(\d+) ", data, re.IGNORECASE).group(2))
        else:
            return -1

    def current_frame_parse(data) -> int:
        if re.search("^p(\d+)of(\d+) ", data, re.IGNORECASE) != None:
            return int(re.search("^p(\d+)of(\d+) ", data, re.IGNORECASE).group(1))
        else:
            return -1

    def data_parse(data) -> str:
        return data.split(" ")[-1].strip()

    def capture_complete(self) -> bool:
        if "empty" not in self.qr_data:
            return True
        else:
            return False

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

    def make_xpub_qr_codes(self, data, callback = None) -> []:
        return self.make_signing_qr_codes(data, callback)

    def make_signing_qr_codes(self, data, callback = None) -> []:
        qr = QR()

        cnt = 0
        images = []
        start = 0
        stop = self.qrsize
        qr_cnt = ((len(data)-1) // self.qrsize) + 1

        while cnt < qr_cnt:
            part = "p" + str(cnt+1) + "of" + str(qr_cnt) + " " + data[start:stop]
            images.append(qr.qrimage(part))
            print(part)
            start = start + self.qrsize
            stop = stop + self.qrsize
            if stop > len(data):
                stop = len(data)
            cnt += 1

            if callback != None:
                    callback((cnt * 100.0) / qr_cnt)

        return images

    def set_qr_density(self, density):
        self.cur_qr_density = density
        if density == Wallet.QRLOW:
            self.qrsize = 60
        elif density == Wallet.QRMEDIUM:
            self.qrsize = 80
        elif density == Wallet.QRHIGH:
            self.qrsize = 100