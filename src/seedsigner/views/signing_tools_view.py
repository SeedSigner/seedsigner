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
        derivation_display = "Derivación: " + derivation
        xpub_display = xpub[0:7] + "..." + xpub[-9:]
        self.draw_modal(["Huella Master: ", fingerprint, derivation_display, xpub_display], "Info Xpub", "Derecha Para Continuar")

    ###
    ### Signing Tx
    ###

    def display_transaction_information(self, p) -> None:
        self.draw.rectangle((0, 0, View.canvas_width, View.canvas_height), outline=0, fill=0)

        tw, th = self.draw.textsize("Confirma Detalles de Tx", font=View.IMPACT25)
        self.draw.text(((240 - tw) / 2, 3), "Confirma Detalles de Tx", fill=View.color, font=View.IMPACT25)

        in_fee_outs_str = str(len(p.psbt.inputs))
        in_fee_outs_str += " inputs - cuota = " if len(p.psbt.inputs) > 1 else " input - cuota = "
        in_fee_outs_str += str(len(p.psbt.outputs))
        in_fee_outs_str += " outs" if len(p.psbt.outputs) > 1 else " out"
        tw, th = self.draw.textsize(in_fee_outs_str, font=View.IMPACT22)
        self.draw.text(((240 - tw) / 2, 40), in_fee_outs_str, fill=View.color, font=View.IMPACT22)

        receiving_addr_str1 = ""
        receiving_addr_str2 = ""
        if len(p.destination_addresses) > 1:
            receiving_addr_str1 += "multiple"
            receiving_addr_str2 += "direcciones de recepción"
        elif len(p.destination_addresses) == 1:
            receiving_addr_str1 += "dirección de recepción"
            receiving_addr_str2 += "últimos 13: ..." + p.destination_addresses[0][-13:]
        else:
            receiving_addr_str1 += "Transferencia-propia"
        
        tw, th = self.draw.textsize(receiving_addr_str1, font=View.IMPACT22)
        self.draw.text(((240 - tw) / 2, 75), receiving_addr_str1, fill=View.color, font=View.IMPACT22)
        if len(receiving_addr_str2) > 0:
            tw, th = self.draw.textsize(receiving_addr_str2, font=View.IMPACT22)
            self.draw.text(((240 - tw) / 2, 100), receiving_addr_str2, fill=View.color, font=View.IMPACT22)


        if p.spend_amount > 0:
            spending_str = "Gastar: " + str(p.spend_amount) + " sats"
            tw, th = self.draw.textsize(spending_str, font=View.IMPACT22)
            self.draw.text(((240 - tw) / 2, 130), spending_str, fill=View.color, font=View.IMPACT22)

        if p.change_amount > 0 and len(p.destination_addresses) == 0:
            change_str = "Cantidad: " + str(p.change_amount) + " sats"
            tw, th = self.draw.textsize(change_str, font=View.IMPACT22)
            self.draw.text(((240 - tw) / 2, 155), change_str, fill=View.color, font=View.IMPACT22)
        elif p.change_amount > 0:
            change_str = "Cambio: " + str(p.change_amount) + " sats"
            tw, th = self.draw.textsize(change_str, font=View.IMPACT22)
            self.draw.text(((240 - tw) / 2, 155), change_str, fill=View.color, font=View.IMPACT22)

        fee_str = "Cuota: " + str(p.fee_amount) + " sats"
        tw, th = self.draw.textsize(fee_str, font=View.IMPACT22)
        self.draw.text(((240 - tw) / 2, 180), fee_str, fill=View.color, font=View.IMPACT22)

        tw, th = self.draw.textsize("Izq. Para Salir, Derecha Para Cont.", font=View.IMPACT18)
        self.draw.text(((240 - tw) / 2, 215), "Izq. Para Salir, Derecha Para Cont.", fill=View.color, font=View.IMPACT18)

        View.DispShowImage()

    def qr_gen_status(percentage):
        View.draw.rectangle((0, 0, View.canvas_width, View.canvas_height), outline=0, fill=0)
        tw, th = View.draw.textsize("Generación de QR", font=View.IMPACT25)
        View.draw.text(((240 - tw) / 2, 90), "Generación de QR", fill=View.color, font=View.IMPACT25)
        tw, th = View.draw.textsize(str(round(percentage)) + "% Completo", font=View.IMPACT25)
        View.draw.text(((240 - tw) / 2, 125), str(round(percentage)) + "% Completo", fill=View.color, font=View.IMPACT25)
        View.DispShowImage()

