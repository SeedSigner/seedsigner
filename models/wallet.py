# Internal Dependencies
from buttons import Buttons, B
from camera_process import CameraProcess
from camera_process import CameraPoll
from view import View

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
import textwrap

class Wallet:

    def __init__(self, current_network, hardened_derivation) -> None:
        self.current_network = current_network
        self.hardened_derivation = hardened_derivation

    def set_seed_phrase(self, seed_phrase):
        # requires a valid seed phrase or error will be thrown
        self.seed_phrase = seed_phrase
        self.seed = bip39.mnemonic_to_seed((" ".join(self.seed_phrase)).strip())
        self.root = bip32.HDKey.from_seed(self.seed, version=NETWORKS[self.current_network]["xprv"])
        self.fingerprint = self.root.child(0).fingerprint
        self.bip48_xprv = self.root.derive(self.hardened_derivation)
        self.bip48_xpub = self.bip48_xprv.to_public()

        self.tx = None
        self.inp_amount = None
        self.fee = None
        self.spend = None
        self.destinationaddress = None
        self.controller = None
        self.buttons = None

        self.camera_loop_timer = None
        self.camera_data = None
        self.is_camera_data = False

        self.qr_total_frames = 0
        self.qr_cur_frame_count = 0
        self.qr_data = []
        self.frame_display = []
        self.percentage_complete = 0

        self.scan_started_ind = 0

    ###
    ### Required Methods to implement for Child Wallet Class
    ###
    ### import_qr, parse_psbt, sign_transaction, total_frames_parse, current_frame_parse, data_parse, capture_complete
    ### get_name, set_network

    def import_qr(self) -> str:
        return "empty"

    def parse_psbt(self, raw_psbt) -> bool:
        # decodes and parses raw_psbt, also calculates the following instance values
        self.inp_amount = None
        self.change = None
        self.fee = None
        self.spend = None
        self.destinationaddress = None
        return False

    def sign_transaction(self) -> (bool, str):
        # signs transaction/pbst last passed to parse_psbt method
        return (False, '')

    def total_frames_parse(data) -> int:
        # parse and returns total number of frames from qr data frame
        return -1

    def current_frame_parse(data) -> int:
        # parses and returns current frame number from qr data frame
        return -1

    def data_parse(data) -> str:
        # parse qr data to string to be cancatinated together into a pbst transaction
        return "empty"

    def capture_complete(qr_data = []) -> bool:
        # returns true if the qr data list is complete
        return False

    def scan_animated_qr_pbst(self, controller) -> str:
        self.controller = controller
        self.buttons = controller.buttons
        self.controller.menu_view.draw_modal(["Initializing Camera"]) # TODO: Move to Controller
        # initialize camera
        self.controller.to_camera_queue.put(["start"])
        # First get blocking, this way it's clear when the camera is ready for the end user
        self.controller.from_camera_queue.get()
        self.camera_loop_timer = CameraPoll(0.05, self.process_camera_data)

        input = self.buttons.wait_for([B.KEY_LEFT, B.KEY_RIGHT])
        if input in (B.KEY_LEFT, B.KEY_RIGHT):
            self.camera_loop_timer.stop()
            self.controller.to_camera_queue.put(["stop"])
            return "nodata"
        elif input == B.OVERRIDE:
            self.camera_loop_timer.stop()
            self.controller.to_camera_queue.put(["stop"])
            if self.qr_data[0] == "invalid":
                return "invalid"
            return "".join(self.qr_data)

    def process_camera_data(self):
        try:
            data = self.controller.from_camera_queue.get(False)
        except:
            data = ["nodata"]

        if data[0] != "nodata":
            if self.qr_total_frames == 0:
                # get total frames if not set
                self.qr_total_frames = type(self).total_frames_parse(data[0])
                if self.qr_total_frames == -1:
                    # when invalid, trigger override to display error
                    self.qr_data = ["invalid"]
                    self.buttons.trigger_override() # something went wrong, invalid QR
                    return

                # create qr_data list with number of total frames
                self.qr_data = ["empty"] * self.qr_total_frames
                # create frame display / progress with number of total frames
                self.frame_display = ["-"] * self.qr_total_frames

            # get current frame
            current_frame = type(self).current_frame_parse(data[0])
            if self.qr_data[current_frame - 1] == "empty":
                # if frame has never been captured, store data element in it
                self.qr_data[current_frame - 1] = type(self).data_parse(data[0])
                # increment number of frames captured
                self.qr_cur_frame_count += 1
                # show in frame display / progress of captured frame
                self.frame_display[current_frame - 1] = "*"
                # calculate percentage complete of captured frames
                self.percentage_complete = int((self.qr_cur_frame_count / self.qr_total_frames) * 100)

            # checking if all frames has been captured, exit camera processing
            if type(self).capture_complete(self.qr_data):
                self.buttons.trigger_override()

            # if all frames have not all been captured, display progress to screen/display
            if not type(self).capture_complete(self.qr_data):
                View.draw.rectangle((0, 0, View.canvas_width, View.canvas_height), outline=0, fill=0)
                tw, th = View.draw.textsize("Collecting QR Codes:", font=View.IMPACT22)
                View.draw.text(((240 - tw) / 2, 15), "Collecting QR Codes:", fill="ORANGE", font=View.IMPACT22)
                lines = textwrap.wrap("".join(self.frame_display), width=11)
                yheight = 60
                for line in lines:
                    tw, th = View.draw.textsize(line, font=View.COURIERNEW30)
                    View.draw.text(((240 - tw) / 2, yheight), line, fill="ORANGE", font=View.COURIERNEW30)
                    yheight += 30
                tw, th = View.draw.textsize("Right to Exit", font=View.IMPACT18)
                View.draw.text(((240 - tw) / 2, 215), "Right to Exit", fill="ORANGE", font=View.IMPACT18)
                View.DispShowImage()

        elif self.scan_started_ind == 0:
            self.scan_started_ind = 1
            self.controller.menu_view.draw_modal(["Scan Animated QR"], "", "Right to Exit")

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
            inp_policy = Wallet.get_policy(inp, inp.witness_utxo.script_pubkey, tx.xpubs)
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
            out_policy = Wallet.get_policy(out, tx.tx.vout[i].script_pubkey, tx.xpubs)
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
            m, n, pubkeys = Wallet.parse_multisig(scope.witness_script)

            # check pubkeys are derived from cosigners
            cosigners = Wallet.get_cosigners(pubkeys, scope.bip32_derivations, xpubs)
            policy.update({
                "m": m, "n": n, "cosigners": cosigners
            })
        return policy

    ###
    ### Network Related Methods
    ###

    def get_network(self) -> str:
        return self.current_network

    def get_hardened_derivation(self) -> str:
        return self.hardened_derivation

    def set_network(self, network) -> bool:
        return False