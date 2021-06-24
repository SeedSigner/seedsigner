# Internal file class dependencies
from . import View
from seedsigner.helpers import Buttons, B

# External Dependencies
import time


class SigningToolsView(View):

    def __init__(self, seed_storage) -> None:
        View.__init__(self)
        self.seed_storage = seed_storage

    ###
    ### XPub
    ###

    def display_xpub_qr(self, wallet):
        xpubstring = wallet.import_qr()
        
        print(xpubstring)

        xpub_images = wallet.make_xpub_qr_codes(xpubstring)

        cnt = 0
        step = False
        if len(xpub_images) == 1:
            View.DispShowImage(xpub_images[0])
        while True:
            if len(xpub_images) != 1:
                if step == False:
                    View.DispShowImage(xpub_images[cnt])
                else:
                    frame_text = (str(cnt+1) + " of " + str(len(xpub_images)))
                    View.DispShowImageWithText(xpub_images[cnt], frame_text)
                    time.sleep(0.3)
                    # View.DispShowImage(xpub_images[cnt])
            if step == False:
                cnt += 1
                if cnt >= len(xpub_images):
                    cnt = 0
                wallet.qr_sleep()
                if self.buttons.check_for_low(B.KEY_RIGHT):
                    return
                if self.buttons.check_for_low(B.KEY1):
                    step = True
            else:
                input = self.buttons.wait_for([B.KEY1, B.KEY_RIGHT, B.KEY_UP, B.KEY_DOWN])
                if input == B.KEY_RIGHT:
                    return
                elif input == B.KEY1 or input == B.KEY_DOWN:
                    cnt += 1
                    if cnt >= len(xpub_images):
                        cnt = 0
                elif input == B.KEY_UP:
                    cnt -= 1
                    if cnt < 0:
                        cnt = len(xpub_images) - 1

    ###
    ### Sign Transaction
    ###

    def display_signed_psbt_animated_qr(self, wallet, psbt) -> None:
        self.draw_modal(["Generating QR ..."])

        print(psbt)
        images = wallet.make_signing_qr_codes(psbt, SigningToolsView.qr_gen_status)

        cnt = 0
        step = False
        while True:
            if step == False:
                View.DispShowImage(images[cnt])
            else:
                frame_text = (str(cnt+1) + " of " + str(len(images)))
                View.DispShowImageWithText(images[cnt], frame_text)
                time.sleep(0.3)
            if step == False:
                cnt += 1
                if cnt >= len(images):
                    cnt = 0
                wallet.qr_sleep()
                if self.buttons.check_for_low(B.KEY_RIGHT):
                    return
                if self.buttons.check_for_low(B.KEY1):
                    step = True
            else:
                input = self.buttons.wait_for([B.KEY1, B.KEY_RIGHT, B.KEY_UP, B.KEY_DOWN])
                if input == B.KEY_RIGHT:
                    return
                elif input == B.KEY1 or input == B.KEY_DOWN:
                    cnt += 1
                    if cnt >= len(images):
                        cnt = 0
                elif input == B.KEY_UP:
                    cnt -= 1
                    if cnt < 0:
                        cnt = len(images) - 1


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

