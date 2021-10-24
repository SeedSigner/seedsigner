from .view import View, BackStackView, MainMenuView


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
        from seedsigner.gui.screens.seed_screens import SeedsMenuScreen

        selected_menu_num = SeedsMenuScreen(
            seeds=self.seeds
        ).display()

        if selected_menu_num < len(self.seeds):
            return (SeedOptionsView, {"seed_num": selected_menu_num})

        elif selected_menu_num == len(self.seeds):
            # TODO: Load a Seed
            pass

        elif selected_menu_num == SeedsMenuScreen.RET_CODE__BACK_BUTTON:
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
            return (SeedExportXpub1View, {"seed_num": self.seed_num})

        elif selected_menu_num == 2:
            # TODO: Export Seed as QR
            return None

        elif selected_menu_num == SeedOptionsScreen.RET_CODE__BACK_BUTTON:
            return BackStackView



SINGLE_SIG = "singlesig"
MULTISIG = "multisig"
class SeedExportXpub1View(View):
    def __init__(self, seed_num: int):
        super().__init__()
        self.seed_num = seed_num


    def run(self):
        from seedsigner.gui.screens.seed_screens import SeedExportXpub1Screen

        selected_menu_num = SeedExportXpub1Screen().display()

        if selected_menu_num == 0:
            return (SeedExportXpub2View, {"seed_num": self.seed_num, "wallet_type": SINGLE_SIG})

        elif selected_menu_num == 1:
            return (SeedExportXpub2View, {"seed_num": self.seed_num, "wallet_type": MULTISIG})

        elif selected_menu_num == SeedExportXpub1Screen.RET_CODE__BACK_BUTTON:
            return BackStackView



class SeedExportXpub2View(View):
    def __init__(self, seed_num: int, wallet_type: str):
        super().__init__()
        self.seed_num = seed_num
        self.wallet_type = wallet_type


    def run(self):
        from seedsigner.gui.screens.seed_screens import SeedExportXpub2Screen

        selected_menu_num = SeedExportXpub2Screen().display()

        if selected_menu_num == 0:
            # TODO: Native Segwit
            return None

        elif selected_menu_num == 1:
            # TODO: Nested Segwit
            return None

        elif selected_menu_num == 2:
            # TODO: Taproot
            return None

        elif selected_menu_num == 3:
            # TODO: Custom Derivation
            return None

        elif selected_menu_num == SeedExportXpub2Screen.RET_CODE__BACK_BUTTON:
            return BackStackView



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


