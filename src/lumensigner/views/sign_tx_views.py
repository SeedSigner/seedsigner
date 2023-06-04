from typing import Union

from stellar_sdk import Keypair, TransactionEnvelope, FeeBumpTransactionEnvelope

from lumensigner.controller import Controller
from lumensigner.gui.components import (
    FontAwesomeIconConstants,
    SeedSignerCustomIconConstants,
)
from lumensigner.gui.screens.screen import (
    RET_CODE__BACK_BUTTON,
    ButtonListScreen,
    QRDisplayScreen,
)
from lumensigner.gui.screens.sign_tx_screens import (
    build_transaction_screens,
    SignTxShowAddressScreen,
)
from lumensigner.hardware.buttons import HardwareButtonsConstants
from lumensigner.models import EncodeQR, QRType
from lumensigner.views.view import BackStackView, View, Destination, MainMenuView


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
            address_index, te = self.controller.tx_data

            kp = Keypair.from_mnemonic_phrase(
                mnemonic_phrase=self.controller.sign_seed.mnemonic_str,
                passphrase=self.controller.sign_seed.passphrase,
                index=address_index,
            )
            return Destination(
                TransactionDetailsView,
                view_args={"te": te, "sign_kp": kp},
                skip_current_view=True,
            )

        self.controller.resume_main_flow = Controller.FLOW__SIGN_TX

        if button_data[selected_menu_num] == SCAN_SEED:
            from lumensigner.views.scan_views import ScanView

            return Destination(ScanView)

        elif button_data[selected_menu_num] in [TYPE_12WORD, TYPE_24WORD]:
            from lumensigner.views.seed_views import SeedMnemonicEntryView

            if button_data[selected_menu_num] == TYPE_12WORD:
                self.controller.storage.init_pending_mnemonic(num_words=12)
            else:
                self.controller.storage.init_pending_mnemonic(num_words=24)
            return Destination(SeedMnemonicEntryView)


class TransactionDetailsView(View):
    def __init__(
        self,
        te: Union[TransactionEnvelope, FeeBumpTransactionEnvelope],
        sign_kp: Keypair = None,
    ):
        super().__init__()
        self.sign_kp = sign_kp
        self.te = te

    def run(self, **kwargs):
        screens = build_transaction_screens(self.te)
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
                else:
                    return Destination(
                        TransactionFinalizeView,
                        view_args={
                            "sign_kp": self.sign_kp,
                            "te": self.te,
                        },
                        clear_history=True,
                    )
            elif ret in (
                HardwareButtonsConstants.KEY_UP,
                HardwareButtonsConstants.KEY1,
            ):
                if current_screen > 0:
                    current_screen -= 1


class TransactionFinalizeView(View):
    """ """

    def __init__(
        self,
        te: Union[TransactionEnvelope, FeeBumpTransactionEnvelope],
        sign_kp: Keypair = None,
    ):
        super().__init__()
        self.sign_kp = sign_kp
        self.te = te

    def run(self):
        SIGN = "Sign"
        ABORT = "Abort"
        button_data = [SIGN, ABORT]
        selected_menu_num = SignTxShowAddressScreen(
            address=self.sign_kp.public_key,
            button_data=button_data,
            show_back_button=False,
        ).display()
        print("selected_menu_num: ", selected_menu_num)

        if button_data[selected_menu_num] == SIGN:
            signature = self.sign_kp.sign(self.te.hash())
            qr_encoder = EncodeQR(qr_type=QRType.STELLAR_SIGNATURE, signature=signature)
            QRDisplayScreen(
                qr_encoder=qr_encoder,
            ).display()
            return Destination(MainMenuView)

        elif button_data[selected_menu_num] == ABORT:
            return Destination(MainMenuView)
