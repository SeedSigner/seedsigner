# SeedSigner file class dependencies
from . import View
from seedsigner.helpers import B, QR
from seedsigner.models import EncodeQRDensity



class SettingsToolsView(View):

    def __init__(self) -> None:
        View.__init__(self)

        self.qr = QR()
        self.donate_image = None

    ### Donate Menu Item

    def display_donate_info_screen(self):
        self.draw_modal(["Puedes Apoyar a ", "SeedSigner donando", "cualquier cantidad de BTC", "¡Gracias!"], "", "(Palanca derecha para un QR)")
        return True

    def display_donate_qr(self):
        self.draw_modal(["Cargando..."])
        self.donate_image = self.qr.qrimage("bc1qphlyv2dde290tqdlnk8uswztnshw3x9rjurexqqhksvu7vdevhtsuw4efe")
        View.DispShowImage(self.donate_image)
        return True

    ### Display Network Selection

    def display_current_network(self) -> str:
        r = self.controller.menu_view.display_generic_selection_menu(["...[Regresar a Configuración ]", "Mainnet", "Testnet"], "¿Qué Red?")
        if r == 2:
            return "main"
        elif r == 3:
            return "test"
        else:
            return None

    ### Display Wallet Selection

    def display_wallet_selection(self) -> str:
        r = self.controller.menu_view.display_generic_selection_menu(["...[Regresar a Configuración ]", "Prompt", "Specter Desktop", "Blue Wallet", "Sparrow"], "Which Wallet?")
        if r == 2:
            return "Prompt"
        elif r == 3:
            return "Specter Desktop"
        elif r == 4:
            return "Blue Wallet"
        elif r == 5:
            return "Sparrow"
        else:
            return None

    ### Display QR Density Selection

    def display_qr_density_selection(self) -> str:
        r = self.controller.menu_view.display_generic_selection_menu(["...[Regresar a Configuración ]", "Baja", "Mediana", "Alta"], "¿Cuál densidad de QR?")
        if r == 2:
            return EncodeQRDensity.LOW
        elif r == 3:
            return EncodeQRDensity.MEDIUM
        elif r == 4:
            return EncodeQRDensity.HIGH
        else:
            return None

    ### Display Wallet Policy Selection

    def display_wallet_policy_selection(self) -> str:

        lines = ["...[Regresar a Configuración ]"]
        lines.append("Multi Firma Segwit Nativo")
        lines.append("Firma Sencilla Segwit Nativo")

        r = self.controller.menu_view.display_generic_selection_menu(lines, "¿Qué wallet policy?")
        if r == 1:
            return None
        elif lines[r-1] == "Multi Firma Segwit Nativo":
            return "PKWSH"
        elif lines[r-1] == "Firma Sencilla Segwit Nativo":
            return "PKWPKH"
        else:
            return None

    def display_persistent_settings(self) -> bool:

        lines = ["...[Regresar a Configuración ]"]
        lines.append("Sí")
        lines.append("No")

        r = self.controller.menu_view.display_generic_selection_menu(lines, "¿Usar Conf. Persistente?")
        if r == 1:
            return None
        elif r == 2:
            return True
        elif r == 3:
            return False
        else:
            return None

    ###
    ### Version Info
    ###

    def display_version_info(self):
    
        line1 = "SeedSigner"
        line2 = "Version v" + self.controller.VERSION
        line3 = "(Palanca DERECHA para SALIR)"

        View.draw.rectangle((0, 0, View.canvas_width, View.canvas_height), outline=0, fill=0)
        tw, th = View.draw.textsize(line1, font=View.IMPACT22)
        View.draw.text(((240 - tw) / 2, 20), line1, fill=View.color, font=View.IMPACT22)
        tw, th = View.draw.textsize(line2, font=View.IMPACT22)
        View.draw.text(((240 - tw) / 2, 55), line2, fill=View.color, font=View.IMPACT22)
        tw, th = View.draw.textsize(line3, font=View.IMPACT18)
        View.draw.text(((240 - tw) / 2, 210), line3, fill=View.color, font=View.IMPACT18)
        View.DispShowImage()
