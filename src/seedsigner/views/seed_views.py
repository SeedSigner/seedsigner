from seedsigner.gui.screens.screen import LoadingScreenThread
from seedsigner.models.psbt_parser import PSBTParser
from .view import View, Destination, BackStackView, MainMenuView

from seedsigner.gui.screens import (RET_CODE__BACK_BUTTON, ButtonListScreen,
    LargeButtonScreen, WarningScreen, DireWarningScreen)
from seedsigner.models.seed import SeedConstants
from seedsigner.models.settings import Settings, SettingsConstants



class SeedsMenuView(View):
    def __init__(self):
        super().__init__()
        self.seeds = []
        for seed in self.controller.storage.seeds:
            self.seeds.append({
                "fingerprint": seed.get_fingerprint(self.settings.network),
                "has_passphrase": seed.passphrase is not None
            })


    def run(self):
        button_data = []
        for seed in self.seeds:
            button_data.append((seed["fingerprint"], "fingerprint_inline"))
        button_data.append("Load a seed")

        screen = ButtonListScreen(
            title="In-Memory Seeds",
            is_button_text_centered=False,
            button_data=button_data
        )
        selected_menu_num = screen.display()

        if len(self.seeds) > 0 and selected_menu_num < len(self.seeds):
            return Destination(SeedOptionsView, view_args={"seed_num": selected_menu_num})

        elif selected_menu_num == len(self.seeds):
            return Destination(LoadSeedView)

        elif selected_menu_num == RET_CODE__BACK_BUTTON:
            return Destination(BackStackView)



class LoadSeedView(View):
    def run(self):
        screen = ButtonListScreen(
            title="Load A Seed",
            is_button_text_centered=False,
            button_data=[
                ("Scan Seed QR", "scan_inline"),
                "Enter 24-word seed",
                "Enter 12-word seed",
                "Create a seed",
            ]
        )
        selected_menu_num = screen.display()

        if selected_menu_num == 0:
            from .scan_views import ScanView
            return Destination(ScanView)

        if selected_menu_num == 1:
            return Destination(MainMenuView)

        if selected_menu_num == 2:
            return Destination(MainMenuView)

        if selected_menu_num == 3:
            from .tools_views import ToolsMenuView
            return Destination(ToolsMenuView)

        elif selected_menu_num == RET_CODE__BACK_BUTTON:
            return Destination(BackStackView)
        
        raise Exception("Unhandled return option")




"""****************************************************************************
    Views for actions on individual seeds:
****************************************************************************"""

class SeedOptionsView(View):
    def __init__(self, seed_num: int):
        super().__init__()
        self.seed_num = seed_num
        self.seed = self.controller.get_seed(self.seed_num)


    def run(self):
        from seedsigner.gui.screens.seed_screens import SeedOptionsScreen

        SIGN_PSBT = "Sign PSBT"
        VIEW_WORDS = "View Seed Words"
        EXPORT_XPUB = "Export Xpub"
        EXPORT_SEEDQR = "Export Seed as QR"
        button_data = []

        if self.controller.psbt:
            if not PSBTParser.has_matching_fingerprint(self.controller.psbt, self.seed, network=self.settings.network):
                SIGN_PSBT += " (?)"
            button_data.append(SIGN_PSBT)
        
        button_data.append(VIEW_WORDS)

        if self.settings.xpub_export == SettingsConstants.OPTION__ENABLED:
            button_data.append(EXPORT_XPUB)
        
        button_data.append(EXPORT_SEEDQR)

        screen = SeedOptionsScreen(
            button_data=button_data,
            fingerprint=self.seed.get_fingerprint(self.settings.network),
            has_passphrase=self.seed.passphrase is not None
        )
        selected_menu_num = screen.display()

        if selected_menu_num == RET_CODE__BACK_BUTTON:
            return Destination(BackStackView)

        if button_data[selected_menu_num] == SIGN_PSBT:
            from seedsigner.views.psbt_views import PSBTOverviewView
            return Destination(PSBTOverviewView, view_args={"seed_num": self.seed_num})

        elif button_data[selected_menu_num] == VIEW_WORDS:
            return Destination(SeedWordsWarningView, view_args={"seed_num": self.seed_num})

        elif button_data[selected_menu_num] == EXPORT_XPUB and self.settings.xpub_export == SettingsConstants.OPTION__ENABLED:
            return Destination(SeedExportXpubSigTypeView, view_args={"seed_num": self.seed_num})                

        elif button_data[selected_menu_num] == EXPORT_SEEDQR:
            return None
            # return Destination(SeedExportSeedQRView, view_args={"seed_num": self.seed_num})



"""****************************************************************************
    View Seed Words flow
****************************************************************************"""
class SeedWordsWarningView(View):
    def __init__(self, seed_num: int):
        super().__init__()
        self.seed_num = seed_num


    def run(self):
        screen = DireWarningScreen(
            warning_text="""You must keep your seed words private & away from all online devices.""",
        )
        selected_menu_num = screen.display()

        if selected_menu_num == 0:
            # User clicked "I Understand"
            return Destination(SeedWordsView, view_args={"seed_num": self.seed_num})

        elif selected_menu_num == RET_CODE__BACK_BUTTON:
            return Destination(BackStackView)



class SeedWordsView(View):
    def __init__(self, seed_num: int, is_first_page: bool = True):
        super().__init__()
        self.seed_num = seed_num
        self.seed = self.controller.get_seed(self.seed_num)
        self.is_first_page = is_first_page


    def run(self):
        from seedsigner.gui.screens.seed_screens import SeedWordsScreen

        NEXT_12 = "Next"
        SEED_OPTIONS = "Seed Options"

        button_data = []
        if self.is_first_page and len(self.seed.mnemonic_list) == 24:
            button_data.append(NEXT_12)
        else:
            button_data.append(SEED_OPTIONS)

        screen = SeedWordsScreen(
            seed=self.seed,
            is_first_page=self.is_first_page,
            button_data=button_data,
        )
        selected_menu_num = screen.display()

        if selected_menu_num == RET_CODE__BACK_BUTTON:
            return Destination(BackStackView)

        if button_data[selected_menu_num] == NEXT_12:
            # Go on to page 2
            return Destination(SeedWordsView, view_args={"seed_num": self.seed_num, "is_first_page": False})

        elif button_data[selected_menu_num] == SEED_OPTIONS:
            # Back to SeedOptions for this seed; cannot back ("<") to this View.
            return Destination(SeedOptionsView, view_args={"seed_num": self.seed_num}, clear_history=True)




"""****************************************************************************
    Export Xpub flow
****************************************************************************"""
class SeedExportXpubSigTypeView(View):
    def __init__(self, seed_num: int):
        super().__init__()
        self.seed_num = seed_num


    def run(self):
        if len(self.settings.sig_types) == 1:
            # Nothing to select; skip this screen
            return Destination(SeedExportXpubScriptTypeView, view_args={"seed_num": self.seed_num, "sig_type": self.settings.sig_types[0]}, skip_current_view=True)

        SINGLE_SIG = "Single Sig"
        MULTISIG = "Multisig"
        button_data=[SINGLE_SIG, MULTISIG]

        screen = LargeButtonScreen(
            title="Export Xpub",
            button_data=button_data
        )
        selected_menu_num = screen.display()

        if selected_menu_num == RET_CODE__BACK_BUTTON:
            return Destination(BackStackView)

        if button_data[selected_menu_num] == SINGLE_SIG:
            return Destination(SeedExportXpubScriptTypeView, view_args={"seed_num": self.seed_num, "sig_type": SeedConstants.SINGLE_SIG})

        elif button_data[selected_menu_num] == MULTISIG:
            return Destination(SeedExportXpubScriptTypeView, view_args={"seed_num": self.seed_num, "sig_type": SeedConstants.MULTISIG})




class SeedExportXpubScriptTypeView(View):
    def __init__(self, seed_num: int, sig_type: str):
        super().__init__()
        self.seed_num = seed_num
        self.sig_type = sig_type


    def run(self):
        args = {"seed_num": self.seed_num, "sig_type": self.sig_type}
        if len(self.settings.script_types) == 1:
            # Nothing to select; skip this screen
            args["script_type"] = self.settings.script_types[0]
            return Destination(SeedExportXpubCoordinatorView, view_args=args, skip_current_view=True)

        screen = ButtonListScreen(
            title="Export Xpub",
            is_button_text_centered=False,
            is_bottom_list=True,
            button_data=[script_type["display_name"] for script_type in SeedConstants.ALL_SCRIPT_TYPES if script_type["type"] in self.settings.script_types]
        )
        selected_menu_num = screen.display()

        if selected_menu_num < len(SeedConstants.ALL_SCRIPT_TYPES):
            args["script_type"] = SeedConstants.ALL_SCRIPT_TYPES[selected_menu_num]["type"]

            if SeedConstants.ALL_SCRIPT_TYPES[selected_menu_num]["type"] == SeedConstants.CUSTOM_DERIVATION:
                return Destination(SeedExportXpubCustomDerivationView, view_args=args)

            return Destination(SeedExportXpubCoordinatorView, view_args=args)

        elif selected_menu_num == RET_CODE__BACK_BUTTON:
            return Destination(BackStackView)



class SeedExportXpubCustomDerivationView(View):
    def __init__(self, seed_num: int, sig_type: str, script_type: str):
        super().__init__()
        self.seed_num = seed_num
        self.sig_type = sig_type
        self.script_type = script_type
        self.custom_derivation_path = self.settings.custom_derivation

    def run(self):
        from seedsigner.gui.screens.seed_screens import SeedExportXpubCustomDerivationScreen
        screen = SeedExportXpubCustomDerivationScreen(
            derivation_path=self.custom_derivation_path
        )
        ret = screen.display()

        if ret == RET_CODE__BACK_BUTTON:
            return Destination(BackStackView)
        
        # ret should be the custom derivation path; store it in Settings
        self.settings.custom_derivation = ret

        return Destination(
            SeedExportXpubCoordinatorView,
            view_args={
                "seed_num": self.seed_num,
                "sig_type": self.sig_type,
                "script_type": self.script_type,
            }
        )



class SeedExportXpubCoordinatorView(View):
    def __init__(self, seed_num: int, sig_type: str, script_type: str):
        super().__init__()
        self.seed_num = seed_num
        self.sig_type = sig_type
        self.script_type = script_type


    def run(self):
        args = {
            "seed_num": self.seed_num,
            "sig_type": self.sig_type,
            "script_type": self.script_type,
        }
        if len(self.settings.coordinators) == 1:
            # Nothing to select; skip this screen
            args["coordinator"] = self.settings.coordinators[0]
            return Destination(SeedExportXpubWarningView, view_args=args, skip_current_view=True)

        screen = ButtonListScreen(
            title="Export Xpub",
            is_button_text_centered=False,
            is_bottom_list=True,
            button_data=self.settings.coordinators,
        )
        selected_menu_num = screen.display()

        if selected_menu_num < len(self.settings.coordinators):
            args["coordinator"] = self.settings.coordinators[selected_menu_num]
            return Destination(SeedExportXpubWarningView, view_args=args)

        elif selected_menu_num == RET_CODE__BACK_BUTTON:
            return Destination(BackStackView)



class SeedExportXpubWarningView(View):
    def __init__(self, seed_num: int, sig_type: str, script_type: str, coordinator: str):
        super().__init__()
        self.seed_num = seed_num
        self.sig_type = sig_type
        self.script_type = script_type
        self.coordinator = coordinator


    def run(self):
        if self.settings.show_privacy_warnings:
            screen = WarningScreen(
                warning_headline="Privacy Leak!",
                warning_text="""Xpub can be used to view all future transactions.""",
            )
            selected_menu_num = screen.display()
        else:
            selected_menu_num = 0

        if selected_menu_num == 0:
            # User clicked "I Understand"
            return Destination(
                SeedExportXpubDetailsView,
                view_args={
                    "seed_num": self.seed_num,
                    "sig_type": self.sig_type,
                    "script_type": self.script_type,
                    "coordinator": self.coordinator,
                }
            )

        elif selected_menu_num == RET_CODE__BACK_BUTTON:
            return Destination(BackStackView)



class SeedExportXpubDetailsView(View):
    """
        Collects the user input from all the previous screens leading up to this and
        finally calculates the xpub and displays the summary view to the user.
    """
    def __init__(self, seed_num: int, sig_type: str, script_type: str, coordinator: str):
        super().__init__()
        self.sig_type = sig_type
        self.script_type = script_type
        self.coordinator = coordinator
        self.seed_num = seed_num
        self.seed = self.controller.get_seed(self.seed_num)


    def run(self):
        import embit
        from binascii import hexlify
        from seedsigner.gui.screens.seed_screens import SeedExportXpubDetailsScreen

        # The calc_derivation takes a few moments. Run the loading screen while we wait.
        self.loading_screen = LoadingScreenThread(text="Generating xpub...")
        self.loading_screen.start()

        if self.script_type == SeedConstants.CUSTOM_DERIVATION:
            derivation_path = self.settings.custom_derivation
        else:
            derivation_path = Settings.calc_derivation(
                network=self.controller.settings.network,
                wallet_type=self.sig_type,
                script_type=self.script_type
            )

        if self.settings.show_xpub_details:
            version = embit.bip32.detect_version(
                derivation_path,
                default="xpub",
                network=embit.networks.NETWORKS[self.controller.settings.network]
            )

            root = embit.bip32.HDKey.from_seed(
                self.seed.seed,
                version=embit.networks.NETWORKS[self.controller.settings.network]["xprv"]
            )

            fingerprint = hexlify(root.child(0).fingerprint).decode('utf-8')
            xprv = root.derive(derivation_path)
            xpub = xprv.to_public()
            xpub_base58 = xpub.to_string(version=version)

            screen = SeedExportXpubDetailsScreen(
                fingerprint=fingerprint,
                has_passphrase=self.seed.passphrase is not None,
                derivation_path=derivation_path,
                xpub=xpub_base58,
            )

            self.loading_screen.stop()

            selected_menu_num = screen.display()
        else:
            self.loading_screen.stop()
            selected_menu_num = 0

        if selected_menu_num == 0:
            return Destination(
                SeedExportXpubQRDisplayView,
                {
                    "seed_num": self.seed_num,
                    "sig_type": self.sig_type,
                    "script_type": self.script_type,
                    "coordinator": self.coordinator,
                    "derivation_path": derivation_path,
                }
            )

        elif selected_menu_num == RET_CODE__BACK_BUTTON:
            return Destination(BackStackView)



class SeedExportXpubQRDisplayView(View):
    def __init__(self, seed_num: int, sig_type: str, script_type: str, coordinator: str, derivation_path: str):
        from seedsigner.models.encode_qr import EncodeQR
        from seedsigner.models.qr_type import QRType

        super().__init__()
        self.seed = self.controller.get_seed(seed_num)

        qr_type = QRType.XPUBQR
        if coordinator == SettingsConstants.COORDINATOR__SPECTER_DESKTOP:
            qr_type = QRType.SPECTERXPUBQR

        self.qr_encoder = EncodeQR(
            seed_phrase=self.seed.mnemonic_list,
            passphrase=self.seed.passphrase,
            derivation=derivation_path,
            network=self.settings.network,
            qr_type=qr_type,
            qr_density=self.settings.qr_density,
            wordlist=self.seed.wordlist
        )


    def run(self):
        from seedsigner.gui.screens.seed_screens import SeedExportXpubQRDisplayScreen
        screen = SeedExportXpubQRDisplayScreen(qr_encoder=self.qr_encoder)
        screen.display()

        return Destination(MainMenuView)



"""****************************************************************************
    Loading seeds, passphrases, etc
****************************************************************************"""
class SeedValidView(View):
    def __init__(self):
        super().__init__()

        self.seed = self.controller.storage.get_pending_seed()
        self.fingerprint = self.seed.get_fingerprint(network=self.controller.settings.network)


    def run(self):
        from seedsigner.gui.screens.seed_screens import SeedValidScreen
        from .psbt_views import PSBTOverviewView

        SIGN_PSBT = "Sign PSBT (?)"
        SCAN_PSBT = ("Scan a PSBT", "scan_inline")
        PASSPHRASE = "Add Passphrase"
        SEED_TOOLS = "Seed Tools"
        button_data = []

        # Can we auto-route past this screen entirely?
        if self.controller.psbt:
            if PSBTParser.has_matching_fingerprint(psbt=self.controller.psbt, seed=self.seed, network=self.settings.network):
                # The Seed we just entered can sign the psbt we have in memory.
                # Immediately forward on to the PSBT Overview.
                seed_num = self.controller.storage.finalize_pending_seed()
                return Destination(PSBTOverviewView, view_args={"seed_num": seed_num}, clear_history=True)
            else:
                # We can't be sure if we can sign the PSBT with this new key
                button_data.append(SIGN_PSBT)
        else:
            button_data.append(SCAN_PSBT)

        if self.settings.passphrase == SettingsConstants.OPTION__ENABLED or (not self.seed.passphrase and self.settings.passphrase == SettingsConstants.OPTION__PROMPT):
            button_data.append(PASSPHRASE)
        elif self.seed.passphrase:
            PASSPHRASE = "Edit Passphrase"
            button_data.append(PASSPHRASE)
        
        button_data.append(SEED_TOOLS)

        screen = SeedValidScreen(
            fingerprint=self.fingerprint,
            button_data=button_data,
        )
        selected_menu_num = screen.display()

        if selected_menu_num == RET_CODE__BACK_BUTTON:
            # Back button should clear out the pending seed and start over
            self.controller.storage.clear_pending_seed()
            return Destination(BackStackView)

        if button_data[selected_menu_num] == SIGN_PSBT:
            self.controller.storage.finalize_pending_seed()
            return Destination(PSBTOverviewView, view_args={"seed_num": len(self.controller.storage.seeds) - 1}, clear_history=True)

        elif type(button_data[selected_menu_num]) == tuple and button_data[selected_menu_num][0] == SCAN_PSBT[0]:
            self.controller.storage.finalize_pending_seed()
            # Jump back to the Scan mode, but this time to sign a PSBT
            from .scan_views import ScanView
            return Destination(ScanView, clear_history=True)
        
        elif button_data[selected_menu_num] == PASSPHRASE:
            return Destination(SeedAddPassphraseView)

        if button_data[selected_menu_num] == SEED_TOOLS:
            # Jump straight to the Seed Tools for this seed
            seed_num = self.controller.storage.finalize_pending_seed()
            return Destination(SeedOptionsView, view_args={"seed_num": seed_num}, clear_history=True)



class SeedAddPassphrasePromptView(View):
    def run(self):
        YES = "Yes"
        NO = "No"
        button_data = [YES, NO]

        screen = LargeButtonScreen(
            title="Add Passphrase?",
            button_data=button_data
        )
        selected_menu_num = screen.display()

        if selected_menu_num == RET_CODE__BACK_BUTTON:
            return Destination(BackStackView)

        if button_data[selected_menu_num] == YES:
            return Destination(SeedAddPassphraseView)

        elif button_data[selected_menu_num] == NO:
            return Destination(SeedValidView)



class SeedAddPassphraseView(View):
    def __init__(self):
        super().__init__()
        self.seed = self.controller.storage.get_pending_seed()


    def run(self):
        from seedsigner.gui.screens.seed_screens import SeedAddPassphraseScreen
        screen = SeedAddPassphraseScreen(passphrase=self.seed.passphrase)
        ret = screen.display()

        if ret == RET_CODE__BACK_BUTTON:
            return Destination(BackStackView)
        
        # The new passphrase will be the return value
        self.seed.passphrase = ret
        return Destination(SeedValidView)
