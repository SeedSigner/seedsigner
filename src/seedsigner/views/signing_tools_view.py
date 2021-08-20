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

    def display_xpub_info(self, fingerprint, derivation, xpub):
        derivation_display = "Derivation: " + derivation
        xpub_display = xpub[0:7] + "..." + xpub[-9:]
        self.draw_modal(["Master Fingerprint: ", fingerprint, derivation_display, xpub_display], "Xpub Info", "Right to Continue")

    ###
    ### Signing Tx
    ###

    def display_transaction_information(self, p) -> None:
        self.draw.rectangle((0, 0, View.canvas_width, View.canvas_height), outline=0, fill=0)

        tw, th = self.draw.textsize("Confirm Tx Details", font=View.IMPACT25)
        self.draw.text(((240 - tw) / 2, 3), "Confirm Tx Details", fill=View.color, font=View.IMPACT25)

        in_fee_outs_str = str(len(p.psbt.inputs))
        in_fee_outs_str += " inputs - fee = " if len(p.psbt.inputs) > 1 else " input - fee = "
        in_fee_outs_str += str(len(p.psbt.outputs))
        in_fee_outs_str += " outs" if len(p.psbt.outputs) > 1 else " out"
        tw, th = self.draw.textsize(in_fee_outs_str, font=View.IMPACT22)
        self.draw.text(((240 - tw) / 2, 40), in_fee_outs_str, fill=View.color, font=View.IMPACT22)

        receiving_addr_str1 = ""
        receiving_addr_str2 = ""
        if len(p.destination_addresses) > 1:
            receiving_addr_str1 += "multiple"
            receiving_addr_str2 += "receiving addresses"
        elif len(p.destination_addresses) == 1:
            receiving_addr_str1 += "receiving address"
            receiving_addr_str2 += "last 13: ..." + p.destination_addresses[0][-13:]
        else:
            receiving_addr_str1 += "Self-Transfer"
        
        tw, th = self.draw.textsize(receiving_addr_str1, font=View.IMPACT22)
        self.draw.text(((240 - tw) / 2, 75), receiving_addr_str1, fill=View.color, font=View.IMPACT22)
        if len(receiving_addr_str2) > 0:
            tw, th = self.draw.textsize(receiving_addr_str2, font=View.IMPACT22)
            self.draw.text(((240 - tw) / 2, 100), receiving_addr_str2, fill=View.color, font=View.IMPACT22)


        if p.spend_amount > 0:
            spending_str = "Spend: " + str(p.spend_amount) + " sats"
            tw, th = self.draw.textsize(spending_str, font=View.IMPACT22)
            self.draw.text(((240 - tw) / 2, 130), spending_str, fill=View.color, font=View.IMPACT22)

        if p.change_amount > 0 and len(p.destination_addresses) == 0:
            change_str = "Amount: " + str(p.change_amount) + " sats"
            tw, th = self.draw.textsize(change_str, font=View.IMPACT22)
            self.draw.text(((240 - tw) / 2, 155), change_str, fill=View.color, font=View.IMPACT22)
        elif p.change_amount > 0:
            change_str = "Change: " + str(p.change_amount) + " sats"
            tw, th = self.draw.textsize(change_str, font=View.IMPACT22)
            self.draw.text(((240 - tw) / 2, 155), change_str, fill=View.color, font=View.IMPACT22)

        fee_str = "Fee: " + str(p.fee_amount) + " sats"
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

