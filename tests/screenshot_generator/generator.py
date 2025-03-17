import embit
import pathlib
import pytest
import os
import random
import sys
import time
from unittest.mock import Mock, patch, MagicMock

from embit import compact
from embit.psbt import PSBT, OutputScope
from embit.script import Script

# Prevent importing modules w/Raspi hardware dependencies.
# These must precede any SeedSigner imports.
sys.modules['seedsigner.hardware.ST7789'] = MagicMock()
sys.modules['seedsigner.views.screensaver.ScreensaverScreen'] = MagicMock()
sys.modules['RPi'] = MagicMock()
sys.modules['RPi.GPIO'] = MagicMock()
sys.modules['seedsigner.hardware.camera'] = MagicMock()
sys.modules['seedsigner.hardware.microsd'] = MagicMock()

# Force the screenshots to mimic Pi Zero's output without libraqm
patch('PIL.ImageFont.core.HAVE_RAQM', False).start()

from seedsigner.controller import Controller
from seedsigner.gui.renderer import Renderer
from seedsigner.gui.screens.seed_screens import SeedAddPassphraseScreen
from seedsigner.gui.toast import RemoveSDCardToastManagerThread, SDCardStateChangeToastManagerThread
from seedsigner.gui.toast import DefaultToast, InfoToast, SuccessToast, WarningToast, ErrorToast, DireWarningToast
from seedsigner.hardware.microsd import MicroSD
from seedsigner.helpers import embit_utils
from seedsigner.models.decode_qr import DecodeQR
from seedsigner.models.psbt_parser import OPCODES, PSBTParser
from seedsigner.models.qr_type import QRType
from seedsigner.models.seed import Seed
from seedsigner.models.settings import Settings
from seedsigner.models.settings_definition import SettingsConstants, SettingsDefinition
from seedsigner.views import (MainMenuView, PowerOptionsView, RestartView, NotYetImplementedView, UnhandledExceptionView, 
    psbt_views, seed_views, settings_views, tools_views, scan_views)
from seedsigner.views.screensaver import OpeningSplashView
from seedsigner.views.view import NetworkMismatchErrorView, OptionDisabledView, PowerOffView

from .utils import ScreenshotComplete, ScreenshotConfig, ScreenshotRenderer

import warnings; warnings.warn = lambda *args, **kwargs: None



# Dynamically generate a pytest test run for each locale
@pytest.mark.parametrize("locale", [x for x, y in SettingsConstants.ALL_LOCALES])
def test_generate_all(locale, target_locale):
    """
    `target_locale` is a fixture created in conftest.py via the `--locale` command line arg.

    Optionally skips all other locales.
    """
    if target_locale and locale != target_locale:
        pytest.skip(f"Skipping {locale}")
    
    generate_screenshots(locale)



"""**************************************************************************************
    Set up global test data that will be re-used across a variety of screenshots and for
    all locales.
**************************************************************************************"""
BASE64_PSBT_1 = """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"""
mnemonic_12b = ["abandon"] * 11 + ["about"]
seed_12b = Seed(mnemonic=mnemonic_12b, wordlist_language_code=SettingsConstants.WORDLIST_LANGUAGE__ENGLISH)

def add_op_return_to_psbt(psbt: PSBT, raw_payload_data: bytes):
    data = (compact.to_bytes(OPCODES.OP_RETURN) + 
        compact.to_bytes(OPCODES.OP_PUSHDATA1) + 
        compact.to_bytes(len(raw_payload_data)) +
        raw_payload_data)
    script = Script(data)
    output = OutputScope()
    output.script_pubkey = script
    output.value = 0
    psbt.outputs.append(output)
    return psbt.to_string()

# Prep a PSBT with a human-readable OP_RETURN
raw_payload_data = "Chancellor on the brink of third bailout for banks".encode()
psbt = PSBT.from_base64(BASE64_PSBT_1)

# Simplify the output side
output = psbt.outputs[-1]
psbt.outputs.clear()
psbt.outputs.append(output)
assert len(psbt.outputs) == 1
BASE64_PSBT_WITH_OP_RETURN_TEXT = add_op_return_to_psbt(psbt, raw_payload_data)

# Prep a PSBT with a (repeatably) random 80-byte OP_RETURN
random.seed(6102)
BASE64_PSBT_WITH_OP_RETURN_RAW_BYTES = add_op_return_to_psbt(PSBT.from_base64(BASE64_PSBT_1), random.randbytes(80))

mnemonic_12 = "forum undo fragile fade shy sign arrest garment culture tube off merit".split()
mnemonic_24 = "attack pizza motion avocado network gather crop fresh patrol unusual wild holiday candy pony ranch winter theme error hybrid van cereal salon goddess expire".split()
seed_12 = Seed(mnemonic=mnemonic_12, passphrase="cap*BRACKET3stove", wordlist_language_code=SettingsConstants.WORDLIST_LANGUAGE__ENGLISH)
seed_24 = Seed(mnemonic=mnemonic_24, passphrase="some-PASS*phrase9", wordlist_language_code=SettingsConstants.WORDLIST_LANGUAGE__ENGLISH)
seed_24_w_passphrase = Seed(mnemonic=mnemonic_24, passphrase="some-PASS*phrase9", wordlist_language_code=SettingsConstants.WORDLIST_LANGUAGE__ENGLISH)

MULTISIG_WALLET_DESCRIPTOR = """wsh(sortedmulti(1,[22bde1a9/48h/1h/0h/2h]tpubDFfsBrmpj226ZYiRszYi2qK6iGvh2vkkghfGB2YiRUVY4rqqedHCFEgw12FwDkm7rUoVtq9wLTKc6BN2sxswvQeQgp7m8st4FP8WtP8go76/{0,1}/*,[73c5da0a/48h/1h/0h/2h]tpubDFH9dgzveyD8zTbPUFuLrGmCydNvxehyNdUXKJAQN8x4aZ4j6UZqGfnqFrD4NqyaTVGKbvEW54tsvPTK2UoSbCC1PJY8iCNiwTL3RWZEheQ/{0,1}/*))#3jhtf6yx"""



def generate_screenshots(locale):
    """
        The `Renderer` class is mocked so that calls in the normal code are ignored
        (necessary to avoid having it trying to wire up hardware dependencies).

        When the `Renderer` instance is needed, we patch in our own test-only
        `ScreenshotRenderer`.
    """
    # Prep the ScreenshotRenderer that will be patched over the normal Renderer
    screenshot_root = os.path.join(os.getcwd(), "seedsigner-screenshots")
    ScreenshotRenderer.configure_instance()
    screenshot_renderer: ScreenshotRenderer = ScreenshotRenderer.get_instance()

    # Replace the core `Singleton` calls so that only our ScreenshotRenderer is used.
    Renderer.configure_instance = Mock()
    Renderer.get_instance = Mock(return_value=screenshot_renderer)


    def setup_screenshots(locale: str) -> dict[str, list[ScreenshotConfig]]:
        """ Set up some test data that we'll need in the `Controller` for certain Views """
        # Must reset the Controller so each locale gets a fresh start
        Controller.reset_instance()
        controller = Controller.get_instance()

        controller.settings.set_value(SettingsConstants.SETTING__SIG_TYPES, [attr for attr, name in SettingsConstants.ALL_SIG_TYPES])
        controller.settings.set_value(SettingsConstants.SETTING__SCRIPT_TYPES, [attr for attr, name in SettingsConstants.ALL_SCRIPT_TYPES])

        controller.storage.seeds.append(seed_12)
        controller.storage.seeds.append(seed_12b)
        controller.storage.seeds.append(seed_24)
        controller.storage.set_pending_seed(seed_24_w_passphrase)

        # Pending mnemonic for ToolsCalcFinalWordShowFinalWordView
        controller.storage.init_pending_mnemonic(num_words=12)
        for i, word in enumerate(mnemonic_12[:11]):
            controller.storage.update_pending_mnemonic(word=word, index=i)
        controller.storage.update_pending_mnemonic(word="satoshi", index=11)  # random last word; not supposed to be a valid checksum (yet)

        # Load a PSBT into memory
        decoder = DecodeQR()
        decoder.add_data(BASE64_PSBT_1)
        controller.psbt = decoder.get_psbt()
        controller.psbt_seed = seed_12b

        # Message signing data
        derivation_path = "m/84h/0h/0h/0/0"
        controller.sign_message_data = {
            "seed_num": 0,
            "derivation_path": derivation_path,
            "message": "I attest that I control this bitcoin address blah blah blah",
            "addr_format": embit_utils.parse_derivation_path(derivation_path)
        }

        # Automatically populate all Settings options Views
        settings_views_list = []
        settings_views_list.append(ScreenshotConfig(settings_views.SettingsMenuView))
        settings_views_list.append(
            ScreenshotConfig(
                settings_views.SettingsMenuView,
                dict(
                    visibility=SettingsConstants.VISIBILITY__ADVANCED,
                    selected_attr=SettingsConstants.SETTING__ELECTRUM_SEEDS,
                    initial_scroll=240,  # Just guessing how many pixels to scroll down
                ),
                screenshot_name="SettingsMenuView__Advanced"
            )
        )

        # so we get a choice for transcribe seed qr format
        controller.settings.set_value(
            attr_name=SettingsConstants.SETTING__COMPACT_SEEDQR,
            value=SettingsConstants.OPTION__ENABLED
        )
        for settings_entry in SettingsDefinition.settings_entries:
            if settings_entry.visibility == SettingsConstants.VISIBILITY__HIDDEN:
                continue

            settings_views_list.append(ScreenshotConfig(settings_views.SettingsEntryUpdateSelectionView, dict(attr_name=settings_entry.attr_name), screenshot_name=f"SettingsEntryUpdateSelectionView_{settings_entry.attr_name}"))

        settingsqr_data_persistent = f"settings::v1 name=English_noob_mode persistent=E coords=spa,spd denom=thr network=M qr_density=M xpub_export=E sigs=ss scripts=nat xpub_details=E passphrase=E camera=0 compact_seedqr=E bip85=D priv_warn=E dire_warn=E partners=E locale={locale}"
        settingsqr_data_not_persistent = f"settings::v1 name=Mode_Ephemeral persistent=D coords=spa,spd denom=thr network=M qr_density=M xpub_export=E sigs=ss scripts=nat xpub_details=E passphrase=E camera=0 compact_seedqr=E bip85=D priv_warn=E dire_warn=E partners=E locale={locale}"


        # Set up screenshot-specific callbacks to inject data before the View is run and
        # reset data after the View is run.
        def load_basic_psbt_cb():
            decoder = DecodeQR()
            decoder.add_data(BASE64_PSBT_1)
            controller.psbt = decoder.get_psbt()
            controller.psbt_seed = seed_12b
            controller.multisig_wallet_descriptor = None


        def load_multisig_wallet_descriptor_cb():
            controller.multisig_wallet_descriptor = embit.descriptor.Descriptor.from_string(MULTISIG_WALLET_DESCRIPTOR)


        def load_address_verification_data_cb():
            controller.unverified_address = dict(
                # These are all totally fake data
                address="bc1q6p00wazu4nnqac29fvky6vhjnnhku5u2g9njss62rvy7e0yuperq86f5ek",
                network=SettingsConstants.MAINNET,
                sig_type=SettingsConstants.SINGLE_SIG,
                script_type=SettingsConstants.NATIVE_SEGWIT,
                derivation_path = "m/84h/0h/0h",
                verified_index=5,
                verified_index_is_change=False
            )


        def PSBTSelectSeedView_cb_before():
            # Have to ensure this is cleared out in order to get the seed selection screen
            controller.psbt_seed = None


        def PSBTOverviewView_op_return_cb_before():
            controller.psbt_seed = seed_12b
            decoder = DecodeQR()
            decoder.add_data(BASE64_PSBT_WITH_OP_RETURN_TEXT)
            controller.psbt = decoder.get_psbt()
            controller.psbt_parser = PSBTParser(p=controller.psbt, seed=seed_12b)
        

        def PSBTOpReturnView_raw_hex_data_cb_before():
            decoder.add_data(BASE64_PSBT_WITH_OP_RETURN_RAW_BYTES)
            controller.psbt = decoder.get_psbt()
            controller.psbt_parser = PSBTParser(p=controller.psbt, seed=seed_12b)


        screenshot_sections = {
            "Main Menu Views": [
                ScreenshotConfig(OpeningSplashView, dict(is_screenshot_renderer=True, force_partner_logos=True)),
                ScreenshotConfig(OpeningSplashView, dict(is_screenshot_renderer=True, force_partner_logos=False), screenshot_name="OpeningSplashView_no_partner_logos"),
                ScreenshotConfig(MainMenuView),
                ScreenshotConfig(MainMenuView, screenshot_name='MainMenuView_SDCardStateChangeToast_removed',  toast_thread=SDCardStateChangeToastManagerThread(action=MicroSD.ACTION__REMOVED, activation_delay=0, duration=0)),
                ScreenshotConfig(MainMenuView, screenshot_name='MainMenuView_SDCardStateChangeToast_inserted', toast_thread=SDCardStateChangeToastManagerThread(action=MicroSD.ACTION__INSERTED, activation_delay=0, duration=0)),
                ScreenshotConfig(MainMenuView, screenshot_name='MainMenuView_RemoveSDCardToast',               toast_thread=RemoveSDCardToastManagerThread(activation_delay=0, duration=0)),
                ScreenshotConfig(MainMenuView, screenshot_name='MainMenuView_DefaultToast',                    toast_thread=DefaultToast("This is a default text toast!", activation_delay=0, duration=0)),
                ScreenshotConfig(MainMenuView, screenshot_name='MainMenuView_InfoToast',                       toast_thread=InfoToast("This is an info toast!", activation_delay=0, duration=0)),
                ScreenshotConfig(MainMenuView, screenshot_name='MainMenuView_SuccessToast',                    toast_thread=SuccessToast("This is a success toast!", activation_delay=0, duration=0)),
                ScreenshotConfig(MainMenuView, screenshot_name='MainMenuView_WarningToast',                    toast_thread=WarningToast("This is a warning toast!", activation_delay=0, duration=0)),
                ScreenshotConfig(MainMenuView, screenshot_name='MainMenuView_DireWarningToast',                toast_thread=DireWarningToast("This is a dire warning toast!", activation_delay=0, duration=0)),
                ScreenshotConfig(MainMenuView, screenshot_name='MainMenuView_ErrorToast',                      toast_thread=ErrorToast("This is an error toast!", activation_delay=0, duration=0)),
                ScreenshotConfig(PowerOptionsView),
                ScreenshotConfig(RestartView),
                ScreenshotConfig(PowerOffView),
            ],
            "Seed Views": [
                ScreenshotConfig(seed_views.SeedsMenuView),
                ScreenshotConfig(seed_views.LoadSeedView),
                ScreenshotConfig(seed_views.SeedMnemonicEntryView),
                ScreenshotConfig(seed_views.SeedMnemonicInvalidView),
                ScreenshotConfig(seed_views.SeedFinalizeView),
                ScreenshotConfig(seed_views.SeedAddPassphraseView, screenshot_name="SeedAddPassphraseView_lowercase"),
                ScreenshotConfig(seed_views.SeedAddPassphraseView, dict(initial_keyboard=SeedAddPassphraseScreen.KEYBOARD__UPPERCASE_BUTTON_TEXT), screenshot_name="SeedAddPassphraseView_uppercase"),
                ScreenshotConfig(seed_views.SeedAddPassphraseView, dict(initial_keyboard=SeedAddPassphraseScreen.KEYBOARD__DIGITS_BUTTON_TEXT),    screenshot_name="SeedAddPassphraseView_digits"),
                ScreenshotConfig(seed_views.SeedAddPassphraseView, dict(initial_keyboard=SeedAddPassphraseScreen.KEYBOARD__SYMBOLS_1_BUTTON_TEXT), screenshot_name="SeedAddPassphraseView_symbols_1"),
                ScreenshotConfig(seed_views.SeedAddPassphraseView, dict(initial_keyboard=SeedAddPassphraseScreen.KEYBOARD__SYMBOLS_2_BUTTON_TEXT), screenshot_name="SeedAddPassphraseView_symbols_2"),
                ScreenshotConfig(seed_views.SeedAddPassphraseExitDialogView),
                ScreenshotConfig(seed_views.SeedReviewPassphraseView),
                
                ScreenshotConfig(seed_views.SeedOptionsView, dict(seed_num=0)),
                ScreenshotConfig(seed_views.SeedBackupView, dict(seed_num=0)),
                ScreenshotConfig(seed_views.SeedExportXpubSigTypeView, dict(seed_num=0)),
                ScreenshotConfig(seed_views.SeedExportXpubScriptTypeView, dict(seed_num=0, sig_type="msig")),
                ScreenshotConfig(seed_views.SeedExportXpubCustomDerivationView, dict(seed_num=0, sig_type="ss", script_type="")),
                ScreenshotConfig(seed_views.SeedExportXpubCoordinatorView, dict(seed_num=0, sig_type="ss", script_type="nat")),
                ScreenshotConfig(seed_views.SeedExportXpubWarningView, dict(seed_num=0, sig_type="msig", script_type="nes", coordinator="spd", custom_derivation="")),
                ScreenshotConfig(seed_views.SeedExportXpubDetailsView, dict(seed_num=0, sig_type="ss", script_type="nat", coordinator="bw", custom_derivation="")),
                #ScreenshotConfig(SeedExportXpubQRDisplayView),
                ScreenshotConfig(seed_views.SeedWordsWarningView, dict(seed_num=0)),
                ScreenshotConfig(seed_views.SeedWordsView, dict(seed_num=0)),
                ScreenshotConfig(seed_views.SeedWordsView, dict(seed_num=0, page_index=2), screenshot_name="SeedWordsView_2"),
                ScreenshotConfig(seed_views.SeedBIP85ApplicationModeView, dict(seed_num=0)),
                ScreenshotConfig(seed_views.SeedBIP85SelectChildIndexView, dict(seed_num=0, num_words=24)),
                ScreenshotConfig(seed_views.SeedBIP85InvalidChildIndexView, dict(seed_num=0, num_words=12)), 
                ScreenshotConfig(seed_views.SeedWordsBackupTestPromptView, dict(seed_num=0)),
                ScreenshotConfig(seed_views.SeedWordsBackupTestView, dict(seed_num=0, rand_seed=6102)),
                ScreenshotConfig(seed_views.SeedWordsBackupTestMistakeView, dict(seed_num=0, cur_index=7, wrong_word="satoshi")),
                ScreenshotConfig(seed_views.SeedWordsBackupTestSuccessView, dict(seed_num=0)),
                ScreenshotConfig(seed_views.SeedTranscribeSeedQRFormatView, dict(seed_num=0)),
                ScreenshotConfig(seed_views.SeedTranscribeSeedQRWarningView, dict(seed_num=0)),
                ScreenshotConfig(seed_views.SeedTranscribeSeedQRWholeQRView, dict(seed_num=0, seedqr_format=QRType.SEED__COMPACTSEEDQR, num_modules=21), screenshot_name="SeedTranscribeSeedQRWholeQRView_12_Compact"),
                ScreenshotConfig(seed_views.SeedTranscribeSeedQRWholeQRView, dict(seed_num=0, seedqr_format=QRType.SEED__SEEDQR, num_modules=25),        screenshot_name="SeedTranscribeSeedQRWholeQRView_12_Standard"),
                ScreenshotConfig(seed_views.SeedTranscribeSeedQRWholeQRView, dict(seed_num=2, seedqr_format=QRType.SEED__COMPACTSEEDQR, num_modules=25), screenshot_name="SeedTranscribeSeedQRWholeQRView_24_Compact"),
                ScreenshotConfig(seed_views.SeedTranscribeSeedQRWholeQRView, dict(seed_num=2, seedqr_format=QRType.SEED__SEEDQR, num_modules=29),        screenshot_name="SeedTranscribeSeedQRWholeQRView_24_Standard"),
                ScreenshotConfig(seed_views.SeedTranscribeSeedQRZoomedInView, dict(seed_num=0, seedqr_format=QRType.SEED__COMPACTSEEDQR, initial_block_x=1, initial_block_y=1), screenshot_name="SeedTranscribeSeedQRZoomedInView_12_Compact"),
                ScreenshotConfig(seed_views.SeedTranscribeSeedQRZoomedInView, dict(seed_num=0, seedqr_format=QRType.SEED__SEEDQR, initial_block_x=2, initial_block_y=2),        screenshot_name="SeedTranscribeSeedQRZoomedInView_12_Standard"),

                ScreenshotConfig(seed_views.SeedTranscribeSeedQRConfirmQRPromptView, dict(seed_num=0)),
                ScreenshotConfig(seed_views.SeedTranscribeSeedQRConfirmWrongSeedView),
                ScreenshotConfig(seed_views.SeedTranscribeSeedQRConfirmInvalidQRView),
                ScreenshotConfig(seed_views.SeedTranscribeSeedQRConfirmSuccessView, dict(seed_num=0)),

                # Screenshot can't render live preview screens
                # ScreenshotConfig(seed_views.SeedTranscribeSeedQRConfirmScanView, dict(seed_num=0)),

                ScreenshotConfig(seed_views.SeedSelectSeedView, dict(flow=Controller.FLOW__VERIFY_SINGLESIG_ADDR), screenshot_name="SeedSelectSeedView_address_verification"),
                ScreenshotConfig(seed_views.AddressVerificationSigTypeView),
                ScreenshotConfig(seed_views.SeedAddressVerificationView, dict(seed_num=0), run_before=load_address_verification_data_cb),
                ScreenshotConfig(seed_views.SeedAddressVerificationSuccessView, dict(seed_num=0)),  # Relies on callback above

                ScreenshotConfig(seed_views.LoadMultisigWalletDescriptorView),
                ScreenshotConfig(seed_views.MultisigWalletDescriptorView, run_before=load_multisig_wallet_descriptor_cb),
                ScreenshotConfig(seed_views.SeedDiscardView, dict(seed_num=0)),

                ScreenshotConfig(seed_views.SeedSelectSeedView, dict(flow=Controller.FLOW__SIGN_MESSAGE), screenshot_name="SeedSelectSeedView_sign_message"),
                ScreenshotConfig(seed_views.SeedSignMessageConfirmMessageView),
                ScreenshotConfig(seed_views.SeedSignMessageConfirmAddressView),

                ScreenshotConfig(seed_views.SeedElectrumMnemonicStartView),
            ],
            "PSBT Views": [
                ScreenshotConfig(psbt_views.PSBTSelectSeedView, run_before=PSBTSelectSeedView_cb_before),
                ScreenshotConfig(psbt_views.PSBTOverviewView, run_before=load_basic_psbt_cb),
                ScreenshotConfig(psbt_views.PSBTUnsupportedScriptTypeWarningView),
                ScreenshotConfig(psbt_views.PSBTNoChangeWarningView),
                ScreenshotConfig(psbt_views.PSBTMathView),
                ScreenshotConfig(psbt_views.PSBTAddressDetailsView, dict(address_num=0)),

                ScreenshotConfig(psbt_views.PSBTChangeDetailsView, dict(change_address_num=0), screenshot_name="PSBTChangeDetailsView_multisig_unverified", run_before=load_basic_psbt_cb),
                ScreenshotConfig(psbt_views.PSBTChangeDetailsView, dict(change_address_num=0), screenshot_name="PSBTChangeDetailsView_multisig_verified", run_before=load_multisig_wallet_descriptor_cb),
                ScreenshotConfig(psbt_views.PSBTOverviewView, screenshot_name="PSBTOverviewView_op_return", run_before=PSBTOverviewView_op_return_cb_before),
                ScreenshotConfig(psbt_views.PSBTOpReturnView, screenshot_name="PSBTOpReturnView_text"),  # Relies on callback above
                ScreenshotConfig(psbt_views.PSBTOpReturnView, screenshot_name="PSBTOpReturnView_raw_hex_data", run_before=PSBTOpReturnView_raw_hex_data_cb_before),
                ScreenshotConfig(psbt_views.PSBTAddressVerificationFailedView, dict(is_change=True, is_multisig=False),  screenshot_name="PSBTAddressVerificationFailedView_singlesig_change"),
                ScreenshotConfig(psbt_views.PSBTAddressVerificationFailedView, dict(is_change=False, is_multisig=False), screenshot_name="PSBTAddressVerificationFailedView_singlesig_selftransfer"),
                ScreenshotConfig(psbt_views.PSBTAddressVerificationFailedView, dict(is_change=True, is_multisig=True),   screenshot_name="PSBTAddressVerificationFailedView_multisig_change"),
                ScreenshotConfig(psbt_views.PSBTAddressVerificationFailedView, dict(is_change=False, is_multisig=True),  screenshot_name="PSBTAddressVerificationFailedView_multisig_selftransfer"),
                ScreenshotConfig(psbt_views.PSBTFinalizeView),
                #ScreenshotConfig(PSBTSignedQRDisplayViewScreenshotConfig),
                ScreenshotConfig(psbt_views.PSBTSigningErrorView),
            ],
            "Tools Views": [
                ScreenshotConfig(tools_views.ToolsMenuView),
                #ScreenshotConfig(ToolsImageEntropyLivePreviewView),
                #ScreenshotConfig(ToolsImageEntropyFinalImageView),
                ScreenshotConfig(tools_views.ToolsImageEntropyMnemonicLengthView),
                ScreenshotConfig(tools_views.ToolsDiceEntropyMnemonicLengthView),
                ScreenshotConfig(tools_views.ToolsDiceEntropyEntryView, dict(total_rolls=50)),
                ScreenshotConfig(tools_views.ToolsCalcFinalWordNumWordsView),
                ScreenshotConfig(tools_views.ToolsCalcFinalWordFinalizePromptView),
                ScreenshotConfig(tools_views.ToolsCalcFinalWordCoinFlipsView),
                ScreenshotConfig(tools_views.ToolsCalcFinalWordShowFinalWordView, screenshot_name="ToolsCalcFinalWordShowFinalWordView_pick_word"),
                ScreenshotConfig(tools_views.ToolsCalcFinalWordShowFinalWordView, dict(coin_flips="0010101"), screenshot_name="ToolsCalcFinalWordShowFinalWordView_coin_flips"),
                ScreenshotConfig(tools_views.ToolsCalcFinalWordDoneView),
                ScreenshotConfig(tools_views.ToolsAddressExplorerSelectSourceView),
                ScreenshotConfig(tools_views.ToolsAddressExplorerAddressTypeView),
                ScreenshotConfig(tools_views.ToolsAddressExplorerAddressListView),
                # ScreenshotConfig(tools_views.ToolsAddressExplorerAddressView),
            ],
            "Settings Views": settings_views_list + [
                ScreenshotConfig(settings_views.IOTestView),
                ScreenshotConfig(settings_views.DonateView),
                ScreenshotConfig(settings_views.SettingsIngestSettingsQRView, dict(data=settingsqr_data_persistent), screenshot_name="SettingsIngestSettingsQRView_persistent"),
                ScreenshotConfig(settings_views.SettingsIngestSettingsQRView, dict(data=settingsqr_data_not_persistent), screenshot_name="SettingsIngestSettingsQRView_not_persistent"),
            ],
            "Misc Error Views": [
                ScreenshotConfig(NotYetImplementedView),
                ScreenshotConfig(UnhandledExceptionView, dict(error=["IndexError", "line 1, in some_buggy_code.py", "list index out of range"])),
                ScreenshotConfig(NetworkMismatchErrorView, dict(derivation_path="m/84'/1'/0'")),
                ScreenshotConfig(OptionDisabledView, dict(settings_attr=SettingsConstants.SETTING__MESSAGE_SIGNING)),
                ScreenshotConfig(scan_views.ScanInvalidQRTypeView)
            ]
        }

        return screenshot_sections


    def screencap_view(screenshot_config: ScreenshotConfig):
        # Block until we have exclusive access to the screenshot renderer. Without this
        # we were occasionally running into confusing race conditions where the next
        # screenshot would begin rendering over the previous one. Claiming the lock
        # guarantees that the previous screenshot has been fully rendered and saved.
        with screenshot_renderer.lock:
            screenshot_renderer.set_screenshot_filename(f"{screenshot_config.screenshot_name}.png")

        controller = Controller.get_instance()
        toast_thread = screenshot_config.toast_thread
        try:
            print(f"Running {screenshot_config.screenshot_name}")
            try:
                screenshot_config.run_callback_before()
                screenshot_config.View_cls(**screenshot_config.view_kwargs).run()
            except ScreenshotComplete:
                # The target View has run and its Screen has rendered what it needs to
                if toast_thread is not None:
                    # Now run the Toast so it can render on top of the current image buffer
                    controller.activate_toast(toast_thread)
                    while controller.toast_notification_thread.is_alive():
                        # Give the Toast a moment to complete its work

                        time.sleep(0.01)

                    # TODO: Necessary now that the lock is in place?
                    # Whenever possible, clean up toast thread HERE before killing the
                    # main thread with ScreenshotComplete.
                    toast_thread.stop()
                    toast_thread.join()
                raise ScreenshotComplete()
        except ScreenshotComplete:
            # Slightly hacky way to exit ScreenshotRenderer as expected
            print(f"Completed {screenshot_config.screenshot_name}")
        except Exception as e:
            # Something else went wrong
            from traceback import print_exc
            print_exc()
            raise e
        finally:
            if toast_thread and toast_thread.is_alive():
                toast_thread.stop()
                toast_thread.join()

            screenshot_config.run_callback_after()


    # Parse the main `l10n/messages.pot` for overall stats
    messages_source_path = os.path.join(pathlib.Path(__file__).parent.resolve().parent.resolve().parent.resolve(), "l10n", "messages.pot")
    with open(messages_source_path, 'r') as messages_source_file:
        num_source_messages = messages_source_file.read().count("msgid \"") - 1

    locale_tuple_list = [locale_tuple for locale_tuple in SettingsConstants.ALL_LOCALES if locale_tuple[0] == locale]
    if not locale_tuple_list:
        raise Exception(f"Invalid locale: {locale}")

    locale, display_name = locale_tuple_list[0]

    Settings.get_instance().set_value(SettingsConstants.SETTING__LOCALE, value=locale)

    locale_readme = f"""# SeedSigner Screenshots: {display_name}\n"""

    # Report the translation progress
    if locale != SettingsConstants.LOCALE__ENGLISH:
        try:
            translated_messages_path = os.path.join(pathlib.Path(__file__).parent.resolve().parent.resolve().parent.resolve(), "src", "seedsigner", "resources", "seedsigner-translations", "l10n", locale, "LC_MESSAGES", "messages.po") 
            with open(translated_messages_path, 'r') as translation_file:
                locale_translations = translation_file.read()
                num_locale_translations = locale_translations.count("msgid \"") - locale_translations.count("""msgstr ""\n\n""") - 1

                if locale != "en":
                    locale_readme += f"## Translation progress: {num_locale_translations / num_source_messages:.1%}\n\n"
                locale_readme += "---\n\n"
        except Exception as e:
            from traceback import print_exc
            print_exc()

    for section_name, screenshot_list in setup_screenshots(locale).items():
        subdir = section_name.lower().replace(" ", "_")
        screenshot_renderer.set_screenshot_path(os.path.join(screenshot_root, locale, subdir))
        locale_readme += "\n\n---\n\n"
        locale_readme += f"## {section_name}\n\n"
        locale_readme += """<table style="border: 0;">"""
        locale_readme += f"""<tr><td align="center">"""
        for screenshot_config in screenshot_list:
            screencap_view(screenshot_config)
            locale_readme += """  <table align="left" style="border: 1px solid gray;">"""
            locale_readme += f"""<tr><td align="center">{screenshot_config.screenshot_name}<br/><br/><img src="{subdir}/{screenshot_config.screenshot_name}.png"></td></tr>"""
            locale_readme += """</table>\n"""

        locale_readme += "</td></tr></table>"

    with open(os.path.join(screenshot_root, locale, "README.md"), 'w') as readme_file:
        readme_file.write(locale_readme)

    print(f"Done with locale: {locale}.")

    # Write the main README; ensure it writes all locales, not just the one that may
    # have been specified for this run.
    with open(os.path.join("tests", "screenshot_generator", "template.md"), 'r') as readme_template:
        main_readme = readme_template.read()

    for locale, display_name in SettingsConstants.ALL_LOCALES:
        main_readme += f"* [{display_name}]({locale}/README.md)\n"

    with open(os.path.join(screenshot_root, "README.md"), 'w') as readme_file:
        readme_file.write(main_readme)
