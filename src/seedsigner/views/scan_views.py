from seedsigner.models import DecodeQR, Seed
from seedsigner.models.settings import SettingsConstants
from seedsigner.views.request_address import RequestAddressSelectSeedView
from seedsigner.views.sign_tx_views import TransactionSelectSeedView

from seedsigner.views.view import MainMenuView, NotYetImplementedView, View, Destination


class ScanView(View):
    def run(self):
        from seedsigner.gui.screens.scan_screens import ScanScreen

        wordlist_language_code = self.settings.get_value(
            SettingsConstants.SETTING__WORDLIST_LANGUAGE
        )
        self.decoder = DecodeQR(wordlist_language_code=wordlist_language_code)

        # Start the live preview and background QR reading
        ScanScreen(decoder=self.decoder).display()

        # Handle the results
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
                        Seed(
                            mnemonic=seed_mnemonic,
                            wordlist_language_code=wordlist_language_code,
                        )
                    )
                    if (
                        self.settings.get_value(SettingsConstants.SETTING__PASSPHRASE)
                        == SettingsConstants.OPTION__REQUIRED
                    ):
                        from seedsigner.views.seed_views import SeedAddPassphraseView

                        return Destination(SeedAddPassphraseView)
                    else:
                        return Destination(SeedFinalizeView)

            elif self.decoder.is_sign_hash:
                from seedsigner.views.sign_hash_views import SignHashSelectSeedView

                self.controller.sign_hash_data = self.decoder.get_sign_hash_data()
                return Destination(SignHashSelectSeedView, skip_current_view=True)

            elif self.decoder.is_transaction:
                self.controller.tx_data = self.decoder.get_sign_transaction_data()
                print("Transaction: ", self.controller.tx_data)
                return Destination(TransactionSelectSeedView, skip_current_view=True)

            elif self.decoder.is_request_address:
                self.controller.request_address_data = (
                    self.decoder.get_request_address_data()
                )
                print("Request Address: ", self.controller.request_address_data)
                return Destination(RequestAddressSelectSeedView, skip_current_view=True)

            else:
                return Destination(NotYetImplementedView)

        elif self.decoder.is_invalid:
            raise Exception("QRCode not recognized or not yet supported.")

        return Destination(MainMenuView)
