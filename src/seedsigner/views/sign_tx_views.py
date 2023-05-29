from seedsigner.controller import Controller
from seedsigner.gui.components import (
    FontAwesomeIconConstants,
    SeedSignerCustomIconConstants,
)
from seedsigner.gui.screens.screen import (
    RET_CODE__BACK_BUTTON,
    ButtonListScreen,
)
from .view import BackStackView, View, Destination, MainMenuView
from ..gui.screens.transaction_screens import PaymentOperationScreen
from ..hardware.buttons import HardwareButtonsConstants


class TransactionSelectSeedView(View):
    def run(self):
        # Note: we can't just autoroute to the PSBT Overview because we might have a
        # multisig where we want to sign with more than one key on this device.
        # if not self.controller.tx_data:
        #     # Shouldn't be able to get here
        #     raise Exception("No transaction currently loaded")

        seeds = self.controller.storage.seeds
        SCAN_SEED = ("Scan a seed", FontAwesomeIconConstants.QRCODE)
        TYPE_12WORD = ("Enter 12-word seed", FontAwesomeIconConstants.KEYBOARD)
        TYPE_24WORD = ("Enter 24-word seed", FontAwesomeIconConstants.KEYBOARD)
        button_data = [
            (seed.get_fingerprint(), SeedSignerCustomIconConstants.FINGERPRINT, "blue")
            for seed in seeds
        ]
        button_data += [SCAN_SEED, TYPE_12WORD, TYPE_24WORD]

        selected_menu_num = ButtonListScreen(
            title="Select Signer",
            is_button_text_centered=False,
            button_data=button_data,
        ).display()

        if selected_menu_num == RET_CODE__BACK_BUTTON:
            return Destination(BackStackView)

        if len(seeds) > 0 and selected_menu_num < len(seeds):
            # User selected one of the n seeds
            self.controller.sign_seed = self.controller.get_seed(selected_menu_num)
            # address_index = parse_address_index_from_derivation_path(
            #     self.controller.sign_hash_data[0]
            # )
            # sign_kp = Keypair.from_mnemonic_phrase(
            #     mnemonic_phrase=self.controller.sign_seed.mnemonic_str,
            #     passphrase=self.controller.sign_seed.passphrase,
            #     index=address_index,
            # )
            screens = [
                PaymentOperationScreen(operation_index=0),
                PaymentOperationScreen(operation_index=1),
                PaymentOperationScreen(operation_index=2),
            ]
            current_screen = 0
            while True:
                ret = screens[current_screen].display()
                if ret == RET_CODE__BACK_BUTTON:
                    return Destination(MainMenuView)
                elif ret in (
                    HardwareButtonsConstants.KEY_DOWN,
                    HardwareButtonsConstants.KEY3,
                ):
                    if current_screen < len(screens) - 1:
                        current_screen += 1
                elif ret in (
                    HardwareButtonsConstants.KEY_UP,
                    HardwareButtonsConstants.KEY1,
                ):
                    if current_screen > 0:
                        current_screen -= 1
            return Destination(MainMenuView)
            # return Destination(SignHashDireWarningView, view_args={"sign_kp": sign_kp})

        self.controller.resume_main_flow = Controller.FLOW__SIGN_TX

        if button_data[selected_menu_num] == SCAN_SEED:
            from seedsigner.views.scan_views import ScanView

            return Destination(ScanView)

        elif button_data[selected_menu_num] in [TYPE_12WORD, TYPE_24WORD]:
            from seedsigner.views.seed_views import SeedMnemonicEntryView

            if button_data[selected_menu_num] == TYPE_12WORD:
                self.controller.storage.init_pending_mnemonic(num_words=12)
            else:
                self.controller.storage.init_pending_mnemonic(num_words=24)
            return Destination(SeedMnemonicEntryView)


class TransactionFinalizeView(View):
    """ """

    def run(self):
        pass
