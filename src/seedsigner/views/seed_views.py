from .view import View



class SeedValidView(View):
    def __init__(self):
        super().__init__()

        self.seed = self.controller.storage.get_pending_seed()
        self.fingerprint = self.seed.get_fingerprint(network=self.controller.settings.network)


    def run(self):
        from seedsigner.gui.screens.seed_screens import SeedValidScreen
        from .view import MainMenuView, BackStackView

        selected_menu_num = SeedValidScreen(
            fingerprint=self.fingerprint
        ).display()

        if selected_menu_num == 0:
            return MainMenuView

        elif selected_menu_num == 1:
            # TODO: SeedAdvancedView to set passphrase, SeedXOR
            return None

        elif selected_menu_num == SeedValidScreen.RET_CODE__BACK_BUTTON:
            return BackStackView
