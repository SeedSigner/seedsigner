from wallet import Wallet
from buttons import Buttons, B
from camera_process import CameraProcess
from camera_process import CameraPoll
from view import View
from qr import QR

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
from bcur import bcur_decode, cbor_decode, bc32decode, bc32encode, cbor_encode, bcur_encode
from ur2.ur_decoder import URDecoder
from ur2.ur_encoder import UREncoder
from ur2.cbor_lite import CBOREncoder
from ur2.ur import UR
import re
import textwrap

class SparrowMultiSigWallet(Wallet):

    def __init__(self, current_network = "main", hardened_derivation = "m/48h/0h/0h/2h") -> None:
        if current_network == "main":
            Wallet.__init__(self, current_network, "m/48h/0h/0h/2h")
        elif current_network == "test":
            Wallet.__init__(self, current_network, "m/48h/1h/0h/2h")
        else:
            Wallet.__init__(self, current_network, hardened_derivation)

        self.qrsize = 70
        self.blink = False

    def set_seed_phrase(self, seed_phrase):
        Wallet.set_seed_phrase(self, seed_phrase)
        self.ur_decoder = URDecoder()

    def get_name(self) -> str:
        return "Sparrow Multisig"

    # def import_qr(self) -> str:
    #     xpubstring = '{"xfp": "' + hexlify(self.fingerprint).decode('utf-8') + '","p2wsh": "' + self.bip48_xpub.to_base58(NETWORKS[self.current_network]["Zpub"]) + '","p2wsh_deriv": "' + self.hardened_derivation[1:].replace("h", "'") + '"}'

    #     return xpubstring

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

        for inp in self.tx.inputs:
            if inp.witness_utxo is not None:
                inp.non_witness_utxo = None

        #remove scripts from outputs (DIY should know about the wallet)
        for out in self.tx.outputs:
            out.witness_script = None
            out.redeem_script = None

        raw_trimmed_signed_psbt = self.tx.serialize()

        # #added section to trim psbt
        # trimmed_psbt = psbt.PSBT(self.tx.tx)
        # sigsEnd = 0
        # for i, inp in enumerate(self.tx.inputs):
        #     sigsEnd += len(list(inp.partial_sigs.keys()))
        #     trimmed_psbt.inputs[i].partial_sigs = inp.partial_sigs

        # raw_trimmed_signed_psbt = trimmed_psbt.serialize()

        # convert to base64
        b64_psbt = b2a_base64(raw_trimmed_signed_psbt)
        # somehow b2a ends with \n...
        if b64_psbt[-1:] == b"\n":
            b64_psbt = b64_psbt[:-1]

        return b64_psbt.decode('utf-8')

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
            return b2a_base64(cbor_decode(self.ur_decoder.result.cbor))

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

            # get data and percentage
            self.ur_decoder.receive_part(data[0])
            self.percentage_complete = self.ur_decoder.estimated_percent_complete()
            frames_complete = round(self.percentage_complete * self.qr_total_frames)
            for i in range(frames_complete):
                self.frame_display[i] = "*"

            # checking if all frames has been captured, exit camera processing
            if self.capture_complete():
                self.buttons.trigger_override()

            # if all frames have not all been captured, display progress to screen/display
            if not self.capture_complete():
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
                if self.blink == True:
                    View.draw.text((230, 5), "+", fill="ORANGE", font=View.IMPACT16)
                    self.blink = False
                else:
                    self.blink = True
                View.DispShowImage()

        elif self.scan_started_ind == 0:
            self.scan_started_ind = 1
            self.controller.menu_view.draw_modal(["Scan Animated QR"], "", "Right to Exit")

    def total_frames_parse(data) -> int:
        if re.search("^UR\:CRYPTO-PSBT\/(\d+)\-(\d+)\/", data, re.IGNORECASE) != None:
            return 10 #valid
        else:
            return -1 #invalid

    def capture_complete(self) -> bool:
        if self.ur_decoder.is_complete():
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

        cnt = 0
        images = []
        start = 0
        stop = self.qrsize
        qr_cnt = (len(data) // self.qrsize) + 1

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

    def qr_sleep(self):
        time.sleep(0.4)

    def set_qr_density(density):
        if density == Wallet.LOW:
            self.qrsize = 70
        elif density == Wallet.HIGH:
            self.qrsize = 90