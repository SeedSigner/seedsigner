# SeedSigner file class dependencies
from . import View
from seedsigner.helpers import B, QR
from seedsigner.gui.keyboard import Keyboard, TextEntryDisplay
from seedsigner.models import EncodeQR



class SettingsToolsView(View):
    def __init__(self) -> None:
        View.__init__(self)

        self.qr = QR()
        self.donate_image = None
        self.derivation = None


    ### Donate Menu Item
    def display_donate_info_screen(self):
        self.renderer.draw_modal(["You can support", "SeedSigner by donating", "any amount of BTC", "Thank You!!!"], "", "(Press right for a QR code)")
        return True


    def display_donate_qr(self):
        self.renderer.draw_modal(["Loading..."])
        self.donate_image = self.qr.qrimage("bc1qphlyv2dde290tqdlnk8uswztnshw3x9rjurexqqhksvu7vdevhtsuw4efe")
        self.renderer.show_image(self.donate_image)
        return True

