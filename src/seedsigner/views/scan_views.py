from seedsigner.models import Settings, DecodeQR, DecodeQRStatus, Seed
from .view import View
from seedsigner.gui.screens.scan_screens import ScanScreen


class ScanView(View):
    def __init__(self):
        from seedsigner.gui.screens.scan_screens import ScanScreen
        super().__init__()

        self.decoder = DecodeQR(wordlist=self.settings.wordlist)


    def run(self):
        # Run the live preview and QR code capture process
        ScanScreen(decoder=self.decoder).display()

        if self.decoder.isComplete() and self.decoder.isSeed():
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
                return SeedValidView

