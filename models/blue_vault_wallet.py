from wallet import Wallet
from qr import QR

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
from bcur import bcur_decode, cbor_decode, bc32decode, bc32encode, cbor_encode, bcur_encode
import re

class BlueVaultWallet(Wallet):

    def __init__(self, current_network = "main", hardened_derivation = "m/48h/0h/0h/2h") -> None:
        if current_network == "main":
            Wallet.__init__(self, current_network, "m/48h/0h/0h/2h")
        elif current_network == "test":
            Wallet.__init__(self, current_network, "m/48h/1h/0h/2h")
        else:
            Wallet.__init__(self, current_network, hardened_derivation)

        self.qrsize = 100

    def get_name(self) -> str:
        return "Blue Wallet Vault"

    def import_qr(self) -> str:
        xpubstring = "[%s%s]%s" % (
             hexlify(self.fingerprint).decode('utf-8'),
             self.hardened_derivation[1:],
             self.bip48_xpub.to_base58(NETWORKS[self.current_network]["Zpub"]))

        return xpubstring

    def parse_psbt(self, raw_psbt) -> bool:
        raw_psbt = b2a_base64(cbor_decode(bc32decode(raw_psbt)))

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

        return bcur_encode(raw_trimmed_signed_psbt)

    def total_frames_parse(data) -> int:
        if re.search("^UR\:BYTES\/(\d+)OF(\d+)", data, re.IGNORECASE) != None:
            return int(re.search("^UR\:BYTES\/(\d+)OF(\d+)", data, re.IGNORECASE).group(2))
        else:
            return -1

    def current_frame_parse(data) -> int:
        if re.search("^UR\:BYTES\/(\d+)OF(\d+)", data, re.IGNORECASE) != None:
            return int(re.search("^UR\:BYTES\/(\d+)OF(\d+)", data, re.IGNORECASE).group(1))
        else:
            return -1

    def data_parse(data) -> str:
        return data.split("/")[-1].strip()

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
        qr = QR()
        images = []
        images.append(qr.qrimage(data))
        return images

    def make_signing_qr_codes(self, data, callback = None) -> []:
        qr = QR()

        qrdata = data[0].upper()
        qrhash = data[1].upper()

        cnt = 0
        images = []
        start = 0
        stop = self.qrsize
        qr_cnt = ((len(data)-1) // self.qrsize) + 1

        while cnt < qr_cnt:
            part = "UR:BYTES/" + str(cnt+1) + "OF" + str(qr_cnt) + "/" + qrhash + "/" + qrdata[start:stop]
            images.append(qr.qrimage(part))
            print(part)
            start = start + self.qrsize
            stop = stop + self.qrsize
            if stop > len(qrdata):
                stop = len(qrdata)
            cnt += 1

            if callback != None:
                    callback((cnt * 100.0) / qr_cnt)

        return images

    def set_qr_density(density):
        if density == Wallet.LOW:
            self.qrsize = 100
        elif density == Wallet.HIGH:
            self.qrsize = 140

    ###
    ### Internal Wallet Transactions OVERRIDE
    ###

    def get_policy(self, scope, scriptpubkey, xpubs):
        """Parse scope and get policy"""
        # we don't know the policy yet, let's parse it
        script_type = scriptpubkey.script_type()
        # p2sh can be either legacy multisig, or nested segwit multisig
        # or nested segwit singlesig
        if script_type == "p2sh":
            if scope.witness_script is not None:
                script_type = "p2sh-p2wsh"
            elif scope.redeem_script is not None and scope.redeem_script.script_type() == "p2wpkh":
                script_type = "p2sh-p2wpkh"
        policy = { "type": script_type }
        # expected multisig
        if "p2wsh" in script_type and scope.witness_script is not None:
            m, n, pubkeys = super().parse_multisig(scope.witness_script)

            # check pubkeys are derived from cosigners
            policy.update({
                "m": m, "n": n
            })
        return policy