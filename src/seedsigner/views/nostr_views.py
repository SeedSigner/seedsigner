from gettext import gettext as _

from seedsigner.helpers import nostr
from seedsigner.gui.screens.screen import RET_CODE__BACK_BUTTON, ButtonListScreen, ButtonOption
from seedsigner.models.settings_definition import SettingsConstants
from seedsigner.views.view import BackStackView, Destination, View



"""****************************************************************************
    Nostr Export Key
****************************************************************************"""
class NostrExportKeyStartView(View):
    def __init__(self, seed_num: int):
        super().__init__()
        self.seed_num = seed_num

    def run(self):
        from seedsigner.gui.screens.screen import WarningScreen
        selected_menu_num = self.run_screen(
            WarningScreen,
            title=_("Export Nostr Key"),
            status_headline=_("Keep keys separate!"),
            text=_("If this key already secures bitcoin, do not use it as your nostr key!"),
        )

        if selected_menu_num == RET_CODE__BACK_BUTTON:
            return Destination(BackStackView)

        return Destination(NostrExportKeySelectTypeView, view_args=dict(seed_num=self.seed_num))



class NostrExportKeySelectTypeView(View):
    # TRANSLATOR_NOTE: Option to export a nostr public key; do not translate "npub".
    PUBKEY_NPUB = ButtonOption("Public key: npub", return_data=nostr.NOSTR__PUBKEY_NPUB)

    # TRANSLATOR_NOTE: Option to export a nostr public key; "hex" == hexadecimal format.
    PUBKEY_HEX = ButtonOption("Public key: hex", return_data=nostr.NOSTR__PUBKEY_HEX)

    # TRANSLATOR_NOTE: Option to export a nostr private key; do not translate "nsec".
    PRIVKEY_NSEC = ButtonOption("Private key: nsec", return_data=nostr.NOSTR__PRIVKEY_NSEC)

    # TRANSLATOR_NOTE: Option to export a nostr private key; "hex" == hexadecimal format.
    PRIVKEY_HEX = ButtonOption("Private key: hex", return_data=nostr.NOSTR__PRIVKEY_HEX)


    def __init__(self, seed_num: int):
        super().__init__()
        self.seed_num = seed_num
        self.seed = self.controller.get_seed(seed_num)
    

    def run(self):
        button_data = [self.PUBKEY_NPUB, self.PUBKEY_HEX, self.PRIVKEY_NSEC, self.PRIVKEY_HEX]
        selected_menu_num = self.run_screen(
            ButtonListScreen,
            title=_("Export Nostr Key"),
            button_data=button_data,
            is_button_text_centered=False,
            is_bottom_list=True,
        )

        if selected_menu_num == RET_CODE__BACK_BUTTON:
            return Destination(BackStackView)
        
        nostr_key_format = button_data[selected_menu_num].return_data

        if nostr_key_format in [nostr.NOSTR__PUBKEY_NPUB, nostr.NOSTR__PUBKEY_HEX]:
            return Destination(NostrExportKeyDisplayKeyView, view_args=dict(seed_num=self.seed_num, nostr_key_format=nostr_key_format))
        else:
            # Show the warning screen before showing the private key
            return Destination(NostrExportKeyPrivateKeyWarningView, view_args=dict(seed_num=self.seed_num, nostr_key_format=nostr_key_format))



class BaseNostrKeyView(View):
    """ Base View class for most of the Nostr export key Views. """
    def __init__(self, seed_num: int, nostr_key_format: str = nostr.NOSTR__PRIVKEY_NSEC):
        super().__init__()
        self.seed_num = seed_num
        self.nostr_key_format = nostr_key_format


    @property
    def nostr_key(self) -> str:
        return nostr.get_nostr_key(
            seed=self.controller.get_seed(self.seed_num),
            format=self.nostr_key_format,
        )
    

    @property
    def is_pubkey(self) -> bool:
        return self.nostr_key_format in [nostr.NOSTR__PUBKEY_NPUB, nostr.NOSTR__PUBKEY_HEX]



class NostrExportKeyPrivateKeyWarningView(BaseNostrKeyView):
    def run(self):
        from seedsigner.gui.screens.screen import DireWarningScreen
        selected_menu_num = self.run_screen(
            DireWarningScreen,
            title=_("Nostr Private Key"),
            status_headline=_("Protect your key!"),
            text=_("Anyone with your private key has full control of your nostr identity."),
        )

        if selected_menu_num == RET_CODE__BACK_BUTTON:
            return Destination(BackStackView)

        return Destination(NostrExportKeyDisplayKeyView, view_args=dict(seed_num=self.seed_num, nostr_key_format=self.nostr_key_format))



class NostrExportKeyDisplayKeyView(BaseNostrKeyView):
    def run(self):
        from seedsigner.gui.screens.nostr_screens import NostrPublicKeyDisplayScreen, NostrPrivateKeyDisplayScreen

        selected_menu_num = self.run_screen(
            NostrPublicKeyDisplayScreen if self.is_pubkey else NostrPrivateKeyDisplayScreen,
            key=self.nostr_key,
        )

        if selected_menu_num == RET_CODE__BACK_BUTTON:
            return Destination(BackStackView)

        return Destination(NostrExportKeyQRView, view_args=dict(seed_num=self.seed_num, nostr_key_format=self.nostr_key_format))



class NostrExportKeyQRView(BaseNostrKeyView):
    def run(self):
        from seedsigner.gui.screens import QRDisplayScreen
        from seedsigner.models.encode_qr import GenericStaticQrEncoder
        from seedsigner.views.seed_views import SeedOptionsView

        qr_encoder = GenericStaticQrEncoder(
            qr_density=self.settings.get_value(SettingsConstants.SETTING__QR_DENSITY),
            data=self.nostr_key,
        )

        self.run_screen(
            QRDisplayScreen,
            qr_encoder=qr_encoder
        )

        return Destination(SeedOptionsView, view_args=dict(seed_num=self.seed_num), skip_current_view=True, clear_history=True)
