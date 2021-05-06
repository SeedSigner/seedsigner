# SeedSigner file class dependencies
from view import View
from qr import QR
from buttons import B

class SettingsToolsView(View):

    def __init__(self, controller) -> None:
        View.__init__(self, controller)

        self.qr = QR()
        self.donate_image = None

    ### Donate Menu Item

    def display_donate_info_screen(self):
        self.draw_modal(["You can support", "SeedSigner by donating", "any amount of BTC", "Thank You!!!"], "", "(Press right for a QR code)")
        return True

    def display_donate_qr(self):
        self.draw_modal(["Loading..."])
        self.donate_image = self.qr.qrimage("bc1q8u3dyltlg6pu56fe7m58aqz9cwrfld0s03zlrjl0wvm9x4nfa60q2l0g97")
        View.DispShowImage(self.donate_image)
        return True

    ### Display Network Selection

    def display_current_network(self) -> str:
        r = self.controller.menu_view.display_generic_selection_menu(["... [ Return to Settings ]", "Mainnet", "Testnet"], "Which Network?")
        if r == 2:
            return "main"
        elif r == 3:
            return "test"
        else:
            return "cancel"

    ### Display Wallet Selection

    def display_wallet_selection(self) ->str:
        r = self.controller.menu_view.display_generic_selection_menu(["... [ Return to Settings ]", "Specter Desktop"], "Which Wallet?")
        if r == 2:
            return "Specter Desktop"
        else:
            return "cancel"

    ###
    ### Version Info
    ###

    def display_version_info(self):
    
        line1 = "SeedSigner"
        line2 = "Version v" + self.controller.VERSION
        line3 = "built for use with"
        line4 = "Specter-desktop"
        line5 = "v1.1.0 or higher"
        line6 = "(Joystick RIGHT to EXIT)"

        View.draw.rectangle((0, 0, View.canvas_width, View.canvas_height), outline=0, fill=0)
        tw, th = View.draw.textsize(line1, font=View.IMPACT22)
        View.draw.text(((240 - tw) / 2, 20), line1, fill="ORANGE", font=View.IMPACT22)
        tw, th = View.draw.textsize(line2, font=View.IMPACT22)
        View.draw.text(((240 - tw) / 2, 55), line2, fill="ORANGE", font=View.IMPACT22)
        tw, th = View.draw.textsize(line3, font=View.IMPACT22)
        View.draw.text(((240 - tw) / 2, 90), line3, fill="ORANGE", font=View.IMPACT22)
        tw, th = View.draw.textsize(line4, font=View.IMPACT22)
        View.draw.text(((240 - tw) / 2, 125), line4, fill="ORANGE", font=View.IMPACT22)
        tw, th = View.draw.textsize(line5, font=View.IMPACT22)
        View.draw.text(((240 - tw) / 2, 160), line5, fill="ORANGE", font=View.IMPACT22)
        tw, th = View.draw.textsize(line6, font=View.IMPACT18)
        View.draw.text(((240 - tw) / 2, 210), line6, fill="ORANGE", font=View.IMPACT18)
        View.DispShowImage()