from .view import View, Destination, BackStackView, MainMenuView
from seedsigner.gui.screens import (RET_CODE__BACK_BUTTON, ButtonListScreen, LargeButtonScreen,
    WarningScreen, DireWarningScreen)
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
            # TODO: Load a Seed
            raise Exception("Not yet implemented")

        elif selected_menu_num == RET_CODE__BACK_BUTTON:
            return Destination(BackStackView)



class SeedOptionsView(View):
    def __init__(self, seed_num: int):
        super().__init__()
        self.seed_num = seed_num
        self.seed = self.controller.storage.seeds[self.seed_num]


    def run(self):
        from seedsigner.gui.screens.seed_screens import SeedOptionsScreen

        screen = SeedOptionsScreen(
            fingerprint=self.seed.get_fingerprint(self.settings.network),
            has_passphrase=self.seed.passphrase is not None
        )
        selected_menu_num = screen.display()

        if selected_menu_num == 0:
            # View seed words
            return Destination(ShowSeedWordsWarningView, view_args={"seed_num": self.seed_num})

        elif selected_menu_num == 1:
            # TODO: Locked-down "Uncle Jim" mode options to bypass the prompts and just
            #   use the configured defaults (e.g. single sig, native segwit, Blue Wallet)
            return Destination(SeedExportXpubSigTypeView, view_args={"seed_num": self.seed_num})

        elif selected_menu_num == 2:
            # TODO: Export Seed as QR
            return Destination(None)

        elif selected_menu_num == RET_CODE__BACK_BUTTON:
            return Destination(BackStackView)


"""****************************************************************************
    View Seed Words flow
****************************************************************************"""
class ShowSeedWordsWarningView(View):
    def __init__(self, seed_num: int):
        super().__init__()
        self.seed_num = seed_num


    def run(self):
        # from seedsigner.gui.screens.seed_screens import SeedExportXpubWalletScreen

        screen = DireWarningScreen(
            warning_text="""You must keep your seed words private & away from all online devices.""",
        )
        selected_menu_num = screen.display()

        if selected_menu_num == 0:
            # User clicked "I Understand"
            raise Exception("not implemented yet")

        elif selected_menu_num == RET_CODE__BACK_BUTTON:
            return Destination(BackStackView)




"""****************************************************************************
    Export Xpub flow
****************************************************************************"""
class SeedExportXpubSigTypeView(View):
    def __init__(self, seed_num: int):
        super().__init__()
        self.seed_num = seed_num


    def run(self):
        screen = LargeButtonScreen(
            title="Export Xpub",
            button_data=[
                "Single Sig",
                "Multisig",
            ]
        )
        selected_menu_num = screen.display()

        if selected_menu_num == 0:
            return Destination(SeedExportXpubScriptTypeView, view_args={"seed_num": self.seed_num, "sig_type": SeedConstants.SINGLE_SIG})

        elif selected_menu_num == 1:
            return Destination(SeedExportXpubScriptTypeView, view_args={"seed_num": self.seed_num, "sig_type": SeedConstants.MULTISIG})

        elif selected_menu_num == RET_CODE__BACK_BUTTON:
            return Destination(BackStackView)



class SeedExportXpubScriptTypeView(View):
    def __init__(self, seed_num: int, sig_type: str):
        super().__init__()
        self.seed_num = seed_num
        self.sig_type = sig_type


    def run(self):
        screen = ButtonListScreen(
            title="Export Xpub",
            is_button_text_centered=False,
            is_bottom_list=True,
            button_data=[script_type["display_name"] for script_type in SeedConstants.ALL_SCRIPT_TYPES]
        )
        selected_menu_num = screen.display()

        args = {"seed_num": self.seed_num, "sig_type": self.sig_type}

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

    def run(self):
        from seedsigner.gui.screens.seed_screens import SeedExportXpubCustomDerivationScreen
        screen = SeedExportXpubCustomDerivationScreen()
        ret = screen.display()

        if ret == RET_CODE__BACK_BUTTON:
            return Destination(BackStackView)
        
        # ret should be the custom derivation path
        custom_derivation_path = ret

        return Destination(
            SeedExportXpubCoordinatorView,
            view_args={
                "seed_num": self.seed_num,
                "sig_type": self.sig_type,
                "script_type": self.script_type,
                "custom_derivation_path": custom_derivation_path,
            }
        )



class SeedExportXpubCoordinatorView(View):
    def __init__(self, seed_num: int, sig_type: str, script_type: str, custom_derivation_path: str = None):
        super().__init__()
        self.seed_num = seed_num
        self.sig_type = sig_type
        self.script_type = script_type
        self.custom_derivation_path = custom_derivation_path


    def run(self):
        default_coordinator = self.settings.software

        # Set up how the list should be ordered
        coordinator_list = []
        if default_coordinator == SettingsConstants.COORDINATOR__PROMPT:
            # Use the default list, but omit "Prompt"
            coordinator_list = SettingsConstants.ALL_COORDINATORS[:-1]
        else:
            # List the selected coordinator first, then the rest (but omit "Prompt")
            coordinator_list.append(default_coordinator)
            for coordinator in SettingsConstants.ALL_COORDINATORS[:-1]:
                if coordinator != default_coordinator:
                    coordinator_list.append(coordinator)

        screen = ButtonListScreen(
            title="Export Xpub",
            is_button_text_centered=False,
            is_bottom_list=True,
            button_data=coordinator_list,
        )
        selected_menu_num = screen.display()

        if selected_menu_num < len(coordinator_list):
            args = {
                "seed_num": self.seed_num,
                "sig_type": self.sig_type,
                "script_type": self.script_type,
                "coordinator": SettingsConstants.ALL_COORDINATORS[selected_menu_num],
                "custom_derivation_path": self.custom_derivation_path,
            }
            return Destination(SeedExportXpubWarningView, view_args=args)

        elif selected_menu_num == RET_CODE__BACK_BUTTON:
            return Destination(BackStackView)



class SeedExportXpubWarningView(View):
    def __init__(self, seed_num: int, sig_type: str, script_type: str, coordinator: str, custom_derivation_path: str = None):
        super().__init__()
        self.seed_num = seed_num
        self.sig_type = sig_type
        self.script_type = script_type
        self.coordinator = coordinator
        self.custom_derivation_path = custom_derivation_path


    def run(self):
        # from seedsigner.gui.screens.seed_screens import SeedExportXpubWalletScreen

        screen = WarningScreen(
            warning_headline="Privacy Leak!",
            warning_text="""Xpub can be used to view all future transactions.""",
        )
        selected_menu_num = screen.display()

        if selected_menu_num == 0:
            # User clicked "I Understand"
            return Destination(
                SeedExportXpubDetailsView,
                view_args={
                    "seed_num": self.seed_num,
                    "sig_type": self.sig_type,
                    "script_type": self.script_type,
                    "coordinator": self.coordinator,
                    "custom_derivation_path": self.custom_derivation_path,
                }
            )

        elif selected_menu_num == RET_CODE__BACK_BUTTON:
            return Destination(BackStackView)



class SeedExportXpubDetailsView(View):
    """
        Collects the user input from all the previous screens leading up to this and
        finally calculates the xpub and displays the summary view to the user.
    """
    def __init__(self, seed_num: int, sig_type: str, script_type: str, coordinator: str, custom_derivation_path: str = None):
        super().__init__()
        self.sig_type = sig_type
        self.script_type = script_type
        self.coordinator = coordinator
        self.seed_num = seed_num
        self.seed = self.controller.storage.seeds[seed_num]
        self.custom_derivation_path = custom_derivation_path


    def run(self):
        import embit
        from binascii import hexlify
        from seedsigner.gui.screens.seed_screens import SeedExportXpubDetailsScreen

        if self.custom_derivation_path:
            derivation_path = self.custom_derivation_path
        else:
            derivation_path = Settings.calc_derivation(
                network=self.controller.settings.network,
                wallet_type=self.sig_type,
                script_type=self.script_type
            )

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
        selected_menu_num = screen.display()

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
        self.seed = self.controller.storage.seeds[seed_num]

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

        screen = SeedValidScreen(
            fingerprint=self.fingerprint
        )
        selected_menu_num = screen.display()

        if selected_menu_num == 0:
            # Jump back to the Scan mode, but this time to sign a PSBT
            from .scan_views import ScanView
            self.controller.storage.finalize_pending_seed()
            return Destination(ScanView, clear_history=True)
        
        elif selected_menu_num == 1:
            # Jump straight to the Seed Tools for this seed
            seed_num = self.controller.storage.finalize_pending_seed()
            return Destination(SeedOptionsView, view_args={"seed_num": seed_num}, clear_history=True)

        elif selected_menu_num == 2:
            # TODO: SeedAdvancedView to set passphrase, SeedXOR merge, etc.
            raise Exception("Not implemented yet")

        elif selected_menu_num == RET_CODE__BACK_BUTTON:
            # Back button should clear out the pending seed and start over
            self.controller.storage.clear_pending_seed()
            return Destination(BackStackView)


