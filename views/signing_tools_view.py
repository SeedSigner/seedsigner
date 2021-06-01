# Internal file class dependencies
from view import View
from qr import QR
from buttons import Buttons, B
from wallet import Wallet

# External Dependencies
import time

class SigningToolsView(View):

    def __init__(self, controller, seed_storage) -> None:
        View.__init__(self, controller)
        self.seed_storage = seed_storage
        self.qr = QR()

    ###
    ### XPub
    ###

    def display_xpub_qr(self, wallet):
        self.draw_modal(["Generating QR ..."])

        xpubstring = wallet.import_qr()
        
        print(xpubstring)

        xpub_image = self.qr.qrimage(xpubstring, 120)

        View.DispShowImage(xpub_image)

    ###
    ### Sign Transaction
    ###

    def display_signed_psbt_animated_qr(self, psbt) -> None:
        self.draw_modal(["Generating QR ..."])

        print(psbt)
        images = self.qr.makeqrcodes(psbt, "Specter Desktop Multisig", 60, SigningToolsView.qr_gen_status)

        cnt = 0
        while True:
            View.DispShowImage(images[cnt])
            cnt += 1
            if cnt >= len(images):
                cnt = 0
            time.sleep(0.2)
            if self.buttons.check_for_low(B.KEY_RIGHT):
                return

    def display_transaction_information(self, wallet) -> None:
        self.draw.rectangle((0, 0, View.canvas_width, View.canvas_height), outline=0, fill=0)
        tw, th = self.draw.textsize("Confirm last 13 chars", font=View.IMPACT22)
        self.draw.text(((240 - tw) / 2, 5), "Confirm last 13 chars", fill="ORANGE", font=View.IMPACT22)
        tw, th = self.draw.textsize("of the receiving address:", font=View.IMPACT22)
        self.draw.text(((240 - tw) / 2, 30), "of the receiving address:", fill="ORANGE", font=View.IMPACT22)
        tw, th = self.draw.textsize(wallet.destinationaddress[-13:], font=View.IMPACT22)
        self.draw.text(((240 - tw) / 2, 55), wallet.destinationaddress[-13:], fill="ORANGE", font=View.IMPACT22)
        tw, th = self.draw.textsize("Amount Sending:", font=View.IMPACT22)
        self.draw.text(((240 - tw) / 2, 90), "Amount Sending:", fill="ORANGE", font=View.IMPACT22)
        if wallet.spend == 0:
            tw, th = self.draw.textsize("Self-Transfer (not parsed)", font=View.IMPACT22)
            self.draw.text(((240 - tw) / 2, 115), "Self-Transfer (not parsed)", fill="ORANGE", font=View.IMPACT22)
        else:
            tw, th = self.draw.textsize(str(wallet.spend) + " satoshis", font=View.IMPACT22)
            self.draw.text(((240 - tw) / 2, 115), str(wallet.spend) + " satoshis", fill="ORANGE", font=View.IMPACT22)
        tw, th = self.draw.textsize("Plus a fee of:", font=View.IMPACT22)
        self.draw.text(((240 - tw) / 2, 150), "Plus a fee of:", fill="ORANGE", font=View.IMPACT22)
        tw, th = self.draw.textsize(str(int(wallet.fee)) + " satoshis", font=View.IMPACT22)
        self.draw.text(((240 - tw) / 2, 175), str(int(wallet.fee)) + " satoshis", fill="ORANGE", font=View.IMPACT22)
        tw, th = self.draw.textsize("Left to Exit, Right to Continue", font=View.IMPACT18)
        self.draw.text(((240 - tw) / 2, 215), "Left to Exit, Right to Continue", fill="ORANGE", font=View.IMPACT18)
        View.DispShowImage()

    def qr_gen_status(percentage):
        View.draw.rectangle((0, 0, View.canvas_width, View.canvas_height), outline=0, fill=0)
        tw, th = View.draw.textsize("QR Generation", font=View.IMPACT25)
        View.draw.text(((240 - tw) / 2, 90), "QR Generation", fill="ORANGE", font=View.IMPACT25)
        tw, th = View.draw.textsize(str(round(percentage)) + "% Complete", font=View.IMPACT25)
        View.draw.text(((240 - tw) / 2, 125), str(round(percentage)) + "% Complete", fill="ORANGE", font=View.IMPACT25)
        View.DispShowImage()

