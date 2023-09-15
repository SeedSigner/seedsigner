import re

from embit.descriptor import Descriptor

from seedsigner.models.decode_qr import DecodeQR
from seedsigner.models.seed import Seed
from seedsigner.models.settings import SettingsConstants
from seedsigner.views.settings_views import SettingsIngestSettingsQRView
from seedsigner.views.view import BackStackView, ErrorView, MainMenuView, NotYetImplementedView, View, Destination



class ScanView(View):
    """
        The catch-all generic scanning View that will accept any of our supported QR
        formats and will route to the most sensible next step.

        Can also be used as a base class for more specific scanning flows with
        dedicated errors when an unexpected QR type is scanned (e.g. Scan PSBT was
        selected but a SeedQR was scanned).
    """
    instructions_text = "Scan a QR code"
    invalid_qr_type_message = "QRCode not recognized or not yet supported."


    def __init__(self):
        super().__init__()
        # Define the decoder here to make it available to child classes' is_valid_qr_type
        # checks and so we can inject data into it in the test suite's `before_run()`.
        self.wordlist_language_code = self.settings.get_value(SettingsConstants.SETTING__WORDLIST_LANGUAGE)
        self.decoder: DecodeQR = DecodeQR(wordlist_language_code=self.wordlist_language_code)


    @property
    def is_valid_qr_type(self):
        return True


    def run(self):
        from seedsigner.gui.screens.scan_screens import ScanScreen

        # Start the live preview and background QR reading
        self.run_screen(
            ScanScreen,
            instructions_text=self.instructions_text,
            decoder=self.decoder
        )

        # Handle the results
        if self.decoder.is_complete:
            if not self.is_valid_qr_type:
                # We recognized the QR type but it was not the type expected for the
                # current flow.
                # Report QR types in more human-readable text (e.g. QRType
                # `seed__compactseedqr` as "seed: compactseedqr").
                return Destination(ErrorView, view_args=dict(
                    title="Error",
                    status_headline="Wrong QR Type",
                    text=self.invalid_qr_type_message + f""", received "{self.decoder.qr_type.replace("__", ": ").replace("_", " ")}\" format""",
                    button_text="Back",
                    next_destination=Destination(BackStackView, skip_current_view=True),
                ))

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
                        Seed(mnemonic=seed_mnemonic, wordlist_language_code=self.wordlist_language_code)
                    )
                    if self.settings.get_value(SettingsConstants.SETTING__PASSPHRASE) == SettingsConstants.OPTION__REQUIRED:
                        from seedsigner.views.seed_views import SeedAddPassphraseView
                        return Destination(SeedAddPassphraseView)
                    else:
                        return Destination(SeedFinalizeView)
            
            elif self.decoder.is_psbt:
                from seedsigner.views.psbt_views import PSBTSelectSeedView
                psbt = self.decoder.get_psbt()
                self.controller.psbt = psbt
                self.controller.psbt_parser = None
                return Destination(PSBTSelectSeedView, skip_current_view=True)

            elif self.decoder.is_settings:
                data = self.decoder.get_settings_data()
                return Destination(SettingsIngestSettingsQRView, view_args=dict(data=data))
            
            elif self.decoder.is_wallet_descriptor:
                from seedsigner.views.seed_views import MultisigWalletDescriptorView
                descriptor_str = self.decoder.get_wallet_descriptor()

                try:
                    # We need to replace `/0/*` wildcards with `/{0,1}/*` in order to use
                    # the Descriptor to verify change, too.
                    orig_descriptor_str = descriptor_str
                    if len(re.findall (r'\[([0-9,a-f,A-F]+?)(\/[0-9,\/,h\']+?)\].*?(\/0\/\*)', descriptor_str)) > 0:
                        p = re.compile(r'(\[[0-9,a-f,A-F]+?\/[0-9,\/,h\']+?\].*?)(\/0\/\*)')
                        descriptor_str = p.sub(r'\1/{0,1}/*', descriptor_str)
                    elif len(re.findall (r'(\[[0-9,a-f,A-F]+?\/[0-9,\/,h,\']+?\][a-z,A-Z,0-9]*?)([\,,\)])', descriptor_str)) > 0:
                        p = re.compile(r'(\[[0-9,a-f,A-F]+?\/[0-9,\/,h,\']+?\][a-z,A-Z,0-9]*?)([\,,\)])')
                        descriptor_str = p.sub(r'\1/{0,1}/*\2', descriptor_str)
                except Exception as e:
                    print(repr(e))
                    descriptor_str = orig_descriptor_str

                descriptor = Descriptor.from_string(descriptor_str)

                if not descriptor.is_basic_multisig:
                    # TODO: Handle single-sig descriptors?
                    print(f"Received single sig descriptor: {descriptor}")
                    return Destination(NotYetImplementedView)

                self.controller.multisig_wallet_descriptor = descriptor
                return Destination(MultisigWalletDescriptorView, skip_current_view=True)
            
            elif self.decoder.is_address:
                from seedsigner.views.seed_views import AddressVerificationStartView
                address = self.decoder.get_address()
                (script_type, network) = self.decoder.get_address_type()

                return Destination(
                    AddressVerificationStartView,
                    skip_current_view=True,
                    view_args={
                        "address": address,
                        "script_type": script_type,
                        "network": network,
                    }
                )
            
            elif self.decoder.is_sign_message:
                from seedsigner.views.seed_views import SeedSignMessageStartView
                qr_data = self.decoder.get_qr_data()

                return Destination(
                    SeedSignMessageStartView,
                    view_args=dict(
                        derivation_path=qr_data["derivation_path"],
                        message=qr_data["message"],
                    )
                )
            
            else:
                return Destination(NotYetImplementedView)

        elif self.decoder.is_invalid:
            # For now, don't even try to re-do the attempted operation, just reset and
            # start everything over.
            self.controller.resume_main_flow = None
            return Destination(ErrorView, view_args=dict(
                title="Error",
                status_headline="Unknown QR Type",
                text="QRCode is invalid or is a data format not yet supported.",
                button_text="Done",
                next_destination=Destination(MainMenuView, clear_history=True),
            ))

        return Destination(MainMenuView)



class ScanPSBTView(ScanView):
    instructions_text = "Scan PSBT"
    invalid_qr_type_message = "Expected a PSBT"

    @property
    def is_valid_qr_type(self):
        return self.decoder.is_psbt



class ScanSeedQRView(ScanView):
    instructions_text = "Scan SeedQR"
    invalid_qr_type_message = "Expected a SeedQR"

    @property
    def is_valid_qr_type(self):
        return self.decoder.is_seed



class ScanWalletDescriptorView(ScanView):
    instructions_text = "Scan descriptor"
    invalid_qr_type_message = "Expected a wallet descriptor QR"

    @property
    def is_valid_qr_type(self):
        return self.decoder.is_wallet_descriptor



class ScanAddressView(ScanView):
    instructions_text = "Scan address QR"
    invalid_qr_type_message = "Expected an address QR"

    @property
    def is_valid_qr_type(self):
        return self.decoder.is_address
