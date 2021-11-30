import json

from .view import BackStackView, MainMenuView, View, Destination

from seedsigner.gui.screens.screen import RET_CODE__BACK_BUTTON
from seedsigner.models import DecodeQR, Seed
from seedsigner.models.qr_type import QRType



class ScanView(View):

    def run(self):
        from seedsigner.gui.screens.scan_screens import ScanScreen

        # Run the live preview and QR code capture process
        self.decoder = DecodeQR(wordlist=self.settings.wordlist)
        screen = ScanScreen(decoder=self.decoder)
        screen.display()

        if self.decoder.isComplete():
            if self.decoder.isSeed():
                # first QR is Seed
                seed_mnemonic = self.decoder.getSeedPhrase()
                if not seed_mnemonic:
                    # seed is not valid, Exit if not valid with message
                    raise Exception("Not yet implemented!")
                else:
                    # Found a valid mnemonic seed! All new seeds should be considered
                    #   pending (might set a passphrase, SeedXOR, etc) until finalized.
                    from .seed_views import SeedValidView
                    self.controller.storage.set_pending_seed(
                        Seed(mnemonic=seed_mnemonic, wordlist=self.controller.settings.wordlist)
                    )
                    return Destination(SeedValidView)

            elif self.decoder.qr_type == QRType.SETTINGS:
                from seedsigner.models.settings import Settings
                settings = self.decoder.get_settings_data()
                Settings.get_instance().update(new_settings=settings)

                return Destination(SettingsUpdatedView, {"config_name": self.decoder.get_settings_config_name()})

        return Destination(MainMenuView)



class SettingsUpdatedView(View):
    def __init__(self, config_name: str):
        super().__init__()

        self.config_name = config_name
    

    def run(self):
        from seedsigner.gui.screens.scan_screens import SettingsUpdatedScreen
        screen = SettingsUpdatedScreen(config_name=self.config_name)
        selected_menu_num = screen.display()

        if selected_menu_num == 0:
            return Destination(MainMenuView)

        elif selected_menu_num == RET_CODE__BACK_BUTTON:
            return Destination(BackStackView)


