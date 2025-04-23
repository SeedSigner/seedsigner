from gettext import gettext as _

from dataclasses import dataclass
from seedsigner.gui.components import GUIConstants, TextArea

from seedsigner.gui.screens.screen import ButtonListScreen, ButtonOption, WarningEdgesMixin



"""****************************************************************************
    Nostr Key Export
****************************************************************************"""
@dataclass
class BaseNostrKeyDisplayScreen(ButtonListScreen):
    """
    Base Screen class for either Nostr pubkey or privkey display.
    """
    key: str = None
    is_pubkey: bool = True

    def __post_init__(self):
        # Customize defaults
        self.title = _("Export Nostr Key")
        self.button_data = [ButtonOption("Next")]
        self.is_bottom_list = True

        super().__post_init__()

        keytype = TextArea(
            text=_("Public key:") if self.is_pubkey else _("Private key:"),
            is_text_centered=True,
            screen_y=self.top_nav.height + GUIConstants.COMPONENT_PADDING
        )
        self.components.append(keytype)

        # npub and nsec are 63 chars; hex format is 64 chars. Break into 4 lines.
        chars_per_line = 16
        key_str = "\n".join([s for s in [self.key[i:i+chars_per_line] for i in range(0, len(self.key), chars_per_line)]])

        key_display = TextArea(
            text=key_str,
            font_name=GUIConstants.FIXED_WIDTH_FONT_NAME,
            font_color=GUIConstants.NOSTR_ACCENT_COLOR,
            font_size=GUIConstants.get_button_font_size(),  # Intentionally using a bigger font size
            is_text_centered=True,
        )
        key_display.screen_y = keytype.screen_y + keytype.height + 2*GUIConstants.COMPONENT_PADDING
        self.components.append(key_display)



class NostrPublicKeyDisplayScreen(BaseNostrKeyDisplayScreen):
    pass



@dataclass
class NostrPrivateKeyDisplayScreen(WarningEdgesMixin, BaseNostrKeyDisplayScreen):
    status_color: str = GUIConstants.DIRE_WARNING_COLOR
    is_pubkey: bool = False
