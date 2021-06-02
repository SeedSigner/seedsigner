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
from ur2.ur_decoder import URDecoder
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

        (self.inp_amount, policy) = BlueVaultWallet.input_amount(self.tx)
        (self.change, self.fee, self.spend, self.destinationaddress) = BlueVaultWallet.change_fee_spend_amounts(self.tx, self.inp_amount, policy, self.current_network)

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

    def capture_complete(qr_data = []) -> bool:
        if "empty" not in qr_data:
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
        qr_cnt = (len(qrdata) // self.qrsize) + 1

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
    ### Internal Wallet Transactions
    ###

    def input_amount(tx) -> (float, str):
        # Check inputs of the transaction and check that they use the same script type
        # For multisig parsed policy will look like this:
        # { script_type: p2wsh, cosigners: [xpubs strings], m: 2, n: 3}
        policy = None
        inp_amount = 0.0
        for inp in tx.inputs:
            inp_amount += inp.witness_utxo.value
            # get policy of the input
            inp_policy = BlueVaultWallet.get_policy(inp, inp.witness_utxo.script_pubkey, tx.xpubs)
            # if policy is None - assign current
            if policy is None:
                policy = inp_policy
            # otherwise check that everything in the policy is the same
            else:
                # check policy is the same
                if policy != inp_policy:
                    raise RuntimeError("Mixed inputs in the transaction")

        return (inp_amount, policy)

    def change_fee_spend_amounts(tx, inp_amount, policy, currentnetwork) -> (float, float, float):
        spend = 0
        change = 0
        destinationaddress = ""
        for i, out in enumerate(tx.outputs):
            out_policy = BlueVaultWallet.get_policy(out, tx.tx.vout[i].script_pubkey, tx.xpubs)
            is_change = False
            # if policy is the same - probably change
            if out_policy == policy:
                # double-check that it's change
                # we already checked in get_cosigners and parse_multisig
                # that pubkeys are generated from cosigners,
                # and witness script is corresponding multisig
                # so we only need to check that scriptpubkey is generated from
                # witness script

                # empty script by default
                sc = script.Script(b"")
                # multisig, we know witness script
                if policy["type"] == "p2wsh":
                    sc = script.p2wsh(out.witness_script)
                elif policy["type"] == "p2sh-p2wsh":
                    sc = script.p2sh(script.p2wsh(out.witness_script))
                # single-sig
                elif "pkh" in policy["type"]:
                    if len(out.bip32_derivations.values()) > 0:
                        der = list(out.bip32_derivations.values())[0].derivation
                        my_pubkey = root.derive(der)
                    if policy["type"] == "p2wpkh":
                        sc = script.p2wpkh(my_pubkey)
                    elif policy["type"] == "p2sh-p2wpkh":
                        sc = script.p2sh(script.p2wpkh(my_pubkey))
                if sc.data == tx.tx.vout[i].script_pubkey.data:
                    is_change = True
            if is_change:
                change += tx.tx.vout[i].value
                print("Change %d sats" % tx.tx.vout[i].value)
            else:
                spend += tx.tx.vout[i].value
                print("Spending %d sats to %s" % (tx.tx.vout[i].value, tx.tx.vout[i].script_pubkey.address(NETWORKS[currentnetwork])))
                destinationaddress = tx.tx.vout[i].script_pubkey.address(NETWORKS[currentnetwork])

        fee = inp_amount - change - spend

        return (change, fee, spend, destinationaddress)

    def parse_multisig(sc):
        """Takes a script and extracts m,n and pubkeys from it"""
        # OP_m <len:pubkey> ... <len:pubkey> OP_n OP_CHECKMULTISIG
        # check min size
        if len(sc.data) < 37 or sc.data[-1] != 0xae:
            raise ValueError("Not a multisig script")
        m = sc.data[0] - 0x50
        if m < 1 or m > 16:
            raise ValueError("Invalid multisig script")
        n = sc.data[-2] - 0x50
        if n < m or n > 16:
            raise ValueError("Invalid multisig script")
        s = BytesIO(sc.data)
        # drop first byte
        s.read(1)
        # read pubkeys
        pubkeys = []
        for i in range(n):
            char = s.read(1)
            if char != b"\x21":
                raise ValueError("Invlid pubkey")
            pubkeys.append(ec.PublicKey.parse(s.read(33)))
        # check that nothing left
        if s.read() != sc.data[-2:]:
            raise ValueError("Invalid multisig script")
        return m, n, pubkeys

    def get_cosigners(pubkeys, derivations, xpubs):
        """Returns xpubs used to derive pubkeys using global xpub field from psbt"""
        cosigners = []
        for i, pubkey in enumerate(pubkeys):
            if pubkey not in derivations:
                raise ValueError("Missing derivation")
            der = derivations[pubkey]
            for xpub in xpubs:
                origin_der = xpubs[xpub]
                # check fingerprint
                if origin_der.fingerprint == der.fingerprint:
                    # check derivation - last two indexes give pub from xpub
                    if origin_der.derivation == der.derivation[:-2]:
                        # check that it derives to pubkey actually
                        if xpub.derive(der.derivation[-2:]).key == pubkey:
                            # append strings so they can be sorted and compared
                            cosigners.append(xpub.to_base58())
                            break
        if len(cosigners) != len(pubkeys):
            raise RuntimeError("Can't get all cosigners")
        return sorted(cosigners)

    def get_policy(scope, scriptpubkey, xpubs):
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
            m, n, pubkeys = BlueVaultWallet.parse_multisig(scope.witness_script)

            # check pubkeys are derived from cosigners
            policy.update({
                "m": m, "n": n
            })
        return policy