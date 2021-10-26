from .view import View, BackStackView, MainMenuView

from seedsigner.gui.screens.base import ButtonListScreen, LargeButtonScreen
from seedsigner.models.seed import SeedConstants
from seedsigner.models.settings import SettingsConstants



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

        selected_menu_num = ButtonListScreen(
            title="In-Memory Seeds",
            is_button_text_centered=False,
            button_data=button_data
        ).display()

        if len(self.seeds) > 0 and selected_menu_num < len(self.seeds):
            return (SeedOptionsView, {"seed_num": selected_menu_num})

        elif selected_menu_num == len(self.seeds):
            # TODO: Load a Seed
            raise Exception("Not yet implemented")

        elif selected_menu_num == ButtonListScreen.RET_CODE__BACK_BUTTON:
            return BackStackView



class SeedOptionsView(View):
    def __init__(self, seed_num: int):
        super().__init__()
        self.seed_num = seed_num
        self.seed = self.controller.storage.seeds[self.seed_num]


    def run(self):
        from seedsigner.gui.screens.seed_screens import SeedOptionsScreen

        selected_menu_num = SeedOptionsScreen(
            fingerprint=self.seed.get_fingerprint(self.settings.network),
            has_passphrase=self.seed.passphrase is not None
        ).display()

        if selected_menu_num == 0:
            # TODO: View seed words
            return None

        elif selected_menu_num == 1:
            # TODO: Locked-down "Uncle Jim" mode options to bypass the prompts and just
            #   use the configured defaults (e.g. single sig, native segwit, Blue Wallet)
            return (SeedExportXpubSigTypeView, {"seed_num": self.seed_num})

        elif selected_menu_num == 2:
            # TODO: Export Seed as QR
            return None

        elif selected_menu_num == SeedOptionsScreen.RET_CODE__BACK_BUTTON:
            return BackStackView



class SeedExportXpubSigTypeView(View):
    def __init__(self, seed_num: int):
        super().__init__()
        self.seed_num = seed_num


    def run(self):
        selected_menu_num = LargeButtonScreen(
            title="Export Xpub",
            button_data=[
                "Single Sig",
                "Multisig",
            ]
        ).display()

        if selected_menu_num == 0:
            return (SeedExportXpubScriptTypeView, {"seed_num": self.seed_num, "sig_type": SeedConstants.SINGLE_SIG})

        elif selected_menu_num == 1:
            return (SeedExportXpubScriptTypeView, {"seed_num": self.seed_num, "sig_type": SeedConstants.MULTISIG})

        elif selected_menu_num == LargeButtonScreen.RET_CODE__BACK_BUTTON:
            return BackStackView



class SeedExportXpubScriptTypeView(View):
    def __init__(self, seed_num: int, sig_type: str):
        super().__init__()
        self.seed_num = seed_num
        self.sig_type = sig_type


    def run(self):
        selected_menu_num = ButtonListScreen(
            title="Export Xpub",
            is_button_text_centered=False,
            is_bottom_list=True,
            button_data=[script_type[1] for script_type in SeedConstants.ALL_SCRIPT_TYPES]
        ).display()

        args = {"seed_num": self.seed_num, "sig_type": self.sig_type}
        if selected_menu_num < len(SeedConstants.ALL_SCRIPT_TYPES):
            args["script_type"] = SeedConstants.ALL_SCRIPT_TYPES[selected_menu_num][0]

            if SeedConstants.ALL_SCRIPT_TYPES[selected_menu_num][0] == SeedConstants.CUSTOM_DERIVATION:
                # TODO: Route to custom derivation View
                raise Exception("Not yet implemented")

            return (SeedExportXpubCoordinatorView, args)

        elif selected_menu_num == ButtonListScreen.RET_CODE__BACK_BUTTON:
            return BackStackView



class SeedExportXpubCoordinatorView(View):
    def __init__(self, seed_num: int, sig_type: str, script_type: str):
        super().__init__()
        self.seed_num = seed_num
        self.sig_type = sig_type
        self.script_type = script_type


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

        selected_menu_num = ButtonListScreen(
            title="Export Xpub",
            is_button_text_centered=False,
            is_bottom_list=True,
            button_data=coordinator_list,
        ).display()

        if selected_menu_num < len(coordinator_list):
            args = {"seed_num": self.seed_num,
                    "sig_type": self.sig_type,
                    "script_type": self.script_type,
                    "coordinator": SettingsConstants.ALL_COORDINATORS[selected_menu_num]}
            return (SeedExportXpubWarningView, args)

        elif selected_menu_num == ButtonListScreen.RET_CODE__BACK_BUTTON:
            return BackStackView



class SeedExportXpubWarningView(View):
    def __init__(self, seed_num: int, sig_type: str, script_type: str, coordinator: str):
        super().__init__()
        self.seed_num = seed_num
        self.sig_type = sig_type
        self.script_type = script_type
        self.coordinator = coordinator


    def run(self):
        # from seedsigner.gui.screens.seed_screens import SeedExportXpubWalletScreen

        # TODO: Implement a generic "Caution" Screen
        caution_title = "Privacy Leak!"
        caution_text = """Xpub can be used to track all future transactions."""

        raise Exception("Not yet implemented")



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

        selected_menu_num = SeedValidScreen(
            fingerprint=self.fingerprint
        ).display()

        if selected_menu_num == 0:
            self.controller.storage.finalize_pending_seed()
            return MainMenuView

        elif selected_menu_num == 1:
            # TODO: SeedAdvancedView to set passphrase, SeedXOR
            return None

        elif selected_menu_num == SeedValidScreen.RET_CODE__BACK_BUTTON:
            # Back button should reset our progress
            self.controller.storage.clear_pending_seed()
            return BackStackView


