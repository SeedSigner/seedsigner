import json
from seedsigner.models.psbt_parser import PSBTParser

from seedsigner.models.settings import SettingsConstants
from seedsigner.views.psbt_views import PSBTSelectSeedView
from seedsigner.views.seed_views import SeedAddPassphraseView

from .view import BackStackView, MainMenuView, NotYetImplementedView, View, Destination

from seedsigner.gui.screens.screen import RET_CODE__BACK_BUTTON
from seedsigner.models import DecodeQR, Seed
from seedsigner.models.qr_type import QRType



class ScanView(View):
    def run(self):
        from seedsigner.gui.screens.scan_screens import ScanScreen

        # Run the live preview and QR code capture process
        # TODO: Does this belong in its own BaseThread?
        wordlist_language_code = self.settings.get_value(SettingsConstants.SETTING__WORDLIST_LANGUAGE)
        self.decoder = DecodeQR(wordlist_language_code=wordlist_language_code)
        screen = ScanScreen(decoder=self.decoder)
        screen.display()

        if self.decoder.is_complete:
            if self.decoder.is_seed:
                seed_mnemonic = self.decoder.get_seed_phrase()
                if not seed_mnemonic:
                    # seed is not valid, Exit if not valid with message
                    raise Exception("Not yet implemented!")
                else:
                    # Found a valid mnemonic seed! All new seeds should be considered
                    #   pending (might set a passphrase, SeedXOR, etc) until finalized.
                    from .seed_views import SeedFinalizeView
                    self.controller.storage.set_pending_seed(
                        Seed(mnemonic=seed_mnemonic, wordlist_language_code=wordlist_language_code)
                    )
                    if self.settings.get_value(SettingsConstants.SETTING__PASSPHRASE) == SettingsConstants.OPTION__REQUIRED:
                        return Destination(SeedAddPassphraseView)
                    else:
                        return Destination(SeedFinalizeView)
            
            elif self.decoder.is_psbt:
                psbt = self.decoder.get_psbt()
                self.controller.psbt = psbt
                self.controller.psbt_parser = None
                return Destination(PSBTSelectSeedView)

            elif self.decoder.is_settings:
                from seedsigner.models.settings import Settings
                settings = self.decoder.get_settings_data()
                Settings.get_instance().update(new_settings=settings)

                print(json.dumps(Settings.get_instance()._data, indent=4))

                return Destination(SettingsUpdatedView, {"config_name": self.decoder.get_settings_config_name()})
            
            elif self.decoder.is_wallet_descriptor:
                # TODO
                print("Implement QR scanning for wallet descriptors!")
                return Destination(NotYetImplementedView)
            
            elif self.decoder.is_address:
                # TODO: Reserved for Nick!
                print("Implement QR scanning for Bitcoin addresses!")
                return Destination(NotYetImplementedView)
            
            else:
                return Destination(NotYetImplementedView)

        return Destination(MainMenuView)



class SettingsUpdatedView(View):
    def __init__(self, config_name: str):
        super().__init__()

        self.config_name = config_name
    

    def run(self):
        from seedsigner.gui.screens.scan_screens import SettingsUpdatedScreen
        screen = SettingsUpdatedScreen(config_name=self.config_name)
        selected_menu_num = screen.display()

        if selected_menu_num == RET_CODE__BACK_BUTTON:
            return Destination(BackStackView)

        # Only one exit point
        return Destination(MainMenuView)

