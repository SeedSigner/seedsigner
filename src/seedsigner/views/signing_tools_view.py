# Internal file class dependencies
from . import View
from seedsigner.helpers import Buttons, B

# External Dependencies
import time


class SigningToolsView(View):

    def __init__(self, controller, seed_storage) -> None:
        View.__init__(self, controller)
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

    def display_xpub_info(self, wallet):
        (fingerprint, derivation, xpub) = wallet.get_xpub_info()
        derivation_display = "Derivation: " + derivation
        xpub_display = xpub[0:7] + "..." + xpub[-9:]
        self.draw_modal(["Master Fingerprint: ", fingerprint, derivation_display, xpub_display], "Xpub Info", "Right to Continue")

    ###
    ### Sign Transaction
    ###

    def display_signed_psbt_animated_qr(self, wallet, psbt) -> None:
        self.draw_modal(["Generating PSBT QR ..."])

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

        tw, th = self.draw.textsize("Confirm Tx Details", font=View.IMPACT25)
        self.draw.text(((240 - tw) / 2, 3), "Confirm Tx Details", fill=View.color, font=View.IMPACT25)

        in_fee_outs_str = str(wallet.ins)
        in_fee_outs_str += " inputs - fee = " if wallet.ins > 1 else " input - fee = "
        in_fee_outs_str += str(wallet.outs)
        in_fee_outs_str += " outs" if wallet.outs > 1 else " out"
        tw, th = self.draw.textsize(in_fee_outs_str, font=View.IMPACT22)
        self.draw.text(((240 - tw) / 2, 40), in_fee_outs_str, fill=View.color, font=View.IMPACT22)

        receiving_addr_str1 = ""
        receiving_addr_str2 = ""
        if wallet.dest_addr_cnt > 1:
            receiving_addr_str1 += "multiple"
            receiving_addr_str2 += "receiving addresses"
        elif wallet.dest_addr_cnt == 1:
            receiving_addr_str1 += "receiving address"
            receiving_addr_str2 += "last 13: ..." + wallet.destinationaddress[-13:]
        else:
            receiving_addr_str1 += "Self-Transfer"
        
        tw, th = self.draw.textsize(receiving_addr_str1, font=View.IMPACT22)
        self.draw.text(((240 - tw) / 2, 75), receiving_addr_str1, fill=View.color, font=View.IMPACT22)
        if len(receiving_addr_str2) > 0:
            tw, th = self.draw.textsize(receiving_addr_str2, font=View.IMPACT22)
            self.draw.text(((240 - tw) / 2, 100), receiving_addr_str2, fill=View.color, font=View.IMPACT22)


        if wallet.spend > 0:
            spending_str = "Spend: " + str(wallet.spend) + " sats"
            tw, th = self.draw.textsize(spending_str, font=View.IMPACT22)
            self.draw.text(((240 - tw) / 2, 130), spending_str, fill=View.color, font=View.IMPACT22)

        if wallet.change > 0 and wallet.dest_addr_cnt == 0:
            change_str = "Amount: " + str(int(wallet.change)) + " sats"
            tw, th = self.draw.textsize(change_str, font=View.IMPACT22)
            self.draw.text(((240 - tw) / 2, 155), change_str, fill=View.color, font=View.IMPACT22)
        elif wallet.change > 0:
            change_str = "Change: " + str(int(wallet.change)) + " sats"
            tw, th = self.draw.textsize(change_str, font=View.IMPACT22)
            self.draw.text(((240 - tw) / 2, 155), change_str, fill=View.color, font=View.IMPACT22)

        fee_str = "Fee: " + str(int(wallet.fee)) + " sats"
        tw, th = self.draw.textsize(fee_str, font=View.IMPACT22)
        self.draw.text(((240 - tw) / 2, 180), fee_str, fill=View.color, font=View.IMPACT22)

        tw, th = self.draw.textsize("Left to Exit, Right to Continue", font=View.IMPACT18)
        self.draw.text(((240 - tw) / 2, 215), "Left to Exit, Right to Continue", fill=View.color, font=View.IMPACT18)

        View.DispShowImage()

    def qr_gen_status(percentage):
        View.draw.rectangle((0, 0, View.canvas_width, View.canvas_height), outline=0, fill=0)
        tw, th = View.draw.textsize("QR Generation", font=View.IMPACT25)
        View.draw.text(((240 - tw) / 2, 90), "QR Generation", fill=View.color, font=View.IMPACT25)
        tw, th = View.draw.textsize(str(round(percentage)) + "% Complete", font=View.IMPACT25)
        View.draw.text(((240 - tw) / 2, 125), str(round(percentage)) + "% Complete", fill=View.color, font=View.IMPACT25)
        View.DispShowImage()

