import embit
import os
import random
import sys
import time
from unittest.mock import Mock, patch, MagicMock
from seedsigner.helpers import embit_utils

from embit import compact
from embit.psbt import PSBT, OutputScope
from embit.script import Script

from seedsigner.helpers import embit_utils
from seedsigner.models.psbt_parser import OPCODES, PSBTParser


# Prevent importing modules w/Raspi hardware dependencies.
# These must precede any SeedSigner imports.
sys.modules['seedsigner.hardware.ST7789'] = MagicMock()
sys.modules['seedsigner.gui.screens.screensaver'] = MagicMock()
sys.modules['seedsigner.views.screensaver'] = MagicMock()
sys.modules['RPi'] = MagicMock()
sys.modules['RPi.GPIO'] = MagicMock()
sys.modules['seedsigner.hardware.camera'] = MagicMock()
sys.modules['seedsigner.hardware.microsd'] = MagicMock()


from seedsigner.controller import Controller
from seedsigner.gui.renderer import Renderer
from seedsigner.gui.toast import BaseToastOverlayManagerThread, RemoveSDCardToastManagerThread, SDCardStateChangeToastManagerThread
from seedsigner.hardware.microsd import MicroSD
from seedsigner.models.decode_qr import DecodeQR
from seedsigner.models.qr_type import QRType
from seedsigner.models.seed import Seed
from seedsigner.models.settings_definition import SettingsConstants, SettingsDefinition
from seedsigner.views import (MainMenuView, PowerOptionsView, RestartView, NotYetImplementedView, UnhandledExceptionView, 
    psbt_views, seed_views, settings_views, tools_views)
from seedsigner.views.view import ErrorView, NetworkMismatchErrorView, OptionDisabledView, PowerOffView, View

from .utils import ScreenshotComplete, ScreenshotRenderer



def test_generate_screenshots(target_locale):
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

    # Additional mocks needed
    PowerOffView.PowerOffThread = Mock()  # Don't let this View actually send the `shutdown` command!

    controller = Controller.get_instance()

    # Set up some test data that we'll need in the `Controller` for certain Views
    mnemonic_12 = "forum undo fragile fade shy sign arrest garment culture tube off merit".split()
    mnemonic_24 = "attack pizza motion avocado network gather crop fresh patrol unusual wild holiday candy pony ranch winter theme error hybrid van cereal salon goddess expire".split()
    mnemonic_12b = ["abandon"] * 11 + ["about"]
    seed_12 = Seed(mnemonic=mnemonic_12, passphrase="cap*BRACKET3stove", wordlist_language_code=SettingsConstants.WORDLIST_LANGUAGE__ENGLISH)
    seed_12b = Seed(mnemonic=mnemonic_12b, wordlist_language_code=SettingsConstants.WORDLIST_LANGUAGE__ENGLISH)
    seed_24 = Seed(mnemonic=mnemonic_24, wordlist_language_code=SettingsConstants.WORDLIST_LANGUAGE__ENGLISH)
    seed_24_w_passphrase = Seed(mnemonic=mnemonic_24, passphrase="some-PASS*phrase9", wordlist_language_code=SettingsConstants.WORDLIST_LANGUAGE__ENGLISH)
    controller.storage.seeds.append(seed_12)
    controller.storage.seeds.append(seed_12b)
    controller.storage.seeds.append(seed_24)
    controller.storage.set_pending_seed(seed_24_w_passphrase)
    UnhandledExceptionViewFood = ["IndexError", "line 1, in some_buggy_code.py", "list index out of range"]

    # Pending mnemonic for ToolsCalcFinalWordShowFinalWordView
    controller.storage.init_pending_mnemonic(num_words=12)
    for i, word in enumerate(mnemonic_12[:11]):
        controller.storage.update_pending_mnemonic(word=word, index=i)
    controller.storage.update_pending_mnemonic(word="satoshi", index=11)  # random last word; not supposed to be a valid checksum (yet)

    # Load a PSBT into memory
    BASE64_PSBT_1 = """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"""
    decoder = DecodeQR()
    decoder.add_data(BASE64_PSBT_1)
    controller.psbt = decoder.get_psbt()
    controller.psbt_seed = seed_12b

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


    # Multisig wallet descriptor for the multisig in the above PSBT
    MULTISIG_WALLET_DESCRIPTOR = """wsh(sortedmulti(1,[22bde1a9/48h/1h/0h/2h]tpubDFfsBrmpj226ZYiRszYi2qK6iGvh2vkkghfGB2YiRUVY4rqqedHCFEgw12FwDkm7rUoVtq9wLTKc6BN2sxswvQeQgp7m8st4FP8WtP8go76/{0,1}/*,[73c5da0a/48h/1h/0h/2h]tpubDFH9dgzveyD8zTbPUFuLrGmCydNvxehyNdUXKJAQN8x4aZ4j6UZqGfnqFrD4NqyaTVGKbvEW54tsvPTK2UoSbCC1PJY8iCNiwTL3RWZEheQ/{0,1}/*))#3jhtf6yx"""
    controller.multisig_wallet_descriptor = embit.descriptor.Descriptor.from_string(MULTISIG_WALLET_DESCRIPTOR)
    
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
    settings_views_list.append(settings_views.SettingsMenuView)
    settings_views_list.append((
        settings_views.SettingsMenuView,
        dict(
            visibility=SettingsConstants.VISIBILITY__ADVANCED,
            selected_attr=SettingsConstants.SETTING__ELECTRUM_SEEDS,
            initial_scroll=240,  # Just guessing how many pixels to scroll down
        ),
        "SettingsMenuView__Advanced"
    ))

    # so we get a choice for transcribe seed qr format
    controller.settings.set_value(
        attr_name=SettingsConstants.SETTING__COMPACT_SEEDQR,
        value=SettingsConstants.OPTION__ENABLED
    )
    for settings_entry in SettingsDefinition.settings_entries:
        if settings_entry.visibility == SettingsConstants.VISIBILITY__HIDDEN:
            continue

        settings_views_list.append((settings_views.SettingsEntryUpdateSelectionView, dict(attr_name=settings_entry.attr_name), f"SettingsEntryUpdateSelectionView_{settings_entry.attr_name}"))
    

    settingsqr_data_persistent = "settings::v1 name=Total_noob_mode persistent=E coords=spa,spd denom=thr network=M qr_density=M xpub_export=E sigs=ss scripts=nat xpub_details=E passphrase=E camera=0 compact_seedqr=E bip85=D priv_warn=E dire_warn=E partners=E"
    settingsqr_data_not_persistent = "settings::v1 name=Ephemeral_noob_mode persistent=D coords=spa,spd denom=thr network=M qr_density=M xpub_export=E sigs=ss scripts=nat xpub_details=E passphrase=E camera=0 compact_seedqr=E bip85=D priv_warn=E dire_warn=E partners=E"

    screenshot_sections = {
        "Main Menu Views": [
            MainMenuView,
            (MainMenuView, {}, 'MainMenuView_SDCardStateChangeToast_removed', SDCardStateChangeToastManagerThread(action=MicroSD.ACTION__REMOVED)),
            (MainMenuView, {}, 'MainMenuView_SDCardStateChangeToast_inserted', SDCardStateChangeToastManagerThread(action=MicroSD.ACTION__INSERTED)),
            (MainMenuView, {}, 'MainMenuView_RemoveSDCardToast', RemoveSDCardToastManagerThread(activation_delay=0)),
            PowerOptionsView,
            RestartView,
            PowerOffView,
        ],
        "Seed Views": [
            seed_views.SeedsMenuView,
            seed_views.LoadSeedView,
            seed_views.SeedMnemonicEntryView,
            seed_views.SeedMnemonicInvalidView,
            seed_views.SeedFinalizeView,
            seed_views.SeedAddPassphraseView,
            seed_views.SeedAddPassphraseExitDialogView,
            seed_views.SeedReviewPassphraseView,
            
            (seed_views.SeedOptionsView, dict(seed_num=0)),
            (seed_views.SeedBackupView, dict(seed_num=0)),
            (seed_views.SeedExportXpubSigTypeView, dict(seed_num=0)),
            (seed_views.SeedExportXpubScriptTypeView, dict(seed_num=0, sig_type="msig")),
            (seed_views.SeedExportXpubCustomDerivationView, dict(seed_num=0, sig_type="ss", script_type="")),
            (seed_views.SeedExportXpubCoordinatorView, dict(seed_num=0, sig_type="ss", script_type="nat")),
            (seed_views.SeedExportXpubWarningView, dict(seed_num=0, sig_type="msig", script_type="nes", coordinator="spd", custom_derivation="")),
            (seed_views.SeedExportXpubDetailsView, dict(seed_num=0, sig_type="ss", script_type="nat", coordinator="bw", custom_derivation="")),
            #SeedExportXpubQRDisplayView,
            (seed_views.SeedWordsWarningView, dict(seed_num=0)),
            (seed_views.SeedWordsView, dict(seed_num=0)),
            (seed_views.SeedWordsView, dict(seed_num=0, page_index=2), "SeedWordsView_2"),
            (seed_views.SeedBIP85ApplicationModeView, dict(seed_num=0)),
            (seed_views.SeedBIP85SelectChildIndexView, dict(seed_num=0, num_words=24)),
            (seed_views.SeedBIP85InvalidChildIndexView, dict(seed_num=0, num_words=12)), 
            (seed_views.SeedWordsBackupTestPromptView, dict(seed_num=0)),
            (seed_views.SeedWordsBackupTestView, dict(seed_num=0)),
            (seed_views.SeedWordsBackupTestMistakeView, dict(seed_num=0, cur_index=7, wrong_word="unlucky")),
            (seed_views.SeedWordsBackupTestSuccessView, dict(seed_num=0)),
            (seed_views.SeedTranscribeSeedQRFormatView, dict(seed_num=0)),
            (seed_views.SeedTranscribeSeedQRWarningView, dict(seed_num=0)),
            (seed_views.SeedTranscribeSeedQRWholeQRView, dict(seed_num=0, seedqr_format=QRType.SEED__COMPACTSEEDQR, num_modules=21), "SeedTranscribeSeedQRWholeQRView_12_Compact"),
            (seed_views.SeedTranscribeSeedQRWholeQRView, dict(seed_num=0, seedqr_format=QRType.SEED__SEEDQR, num_modules=25), "SeedTranscribeSeedQRWholeQRView_12_Standard"),
            (seed_views.SeedTranscribeSeedQRWholeQRView, dict(seed_num=2, seedqr_format=QRType.SEED__COMPACTSEEDQR, num_modules=25), "SeedTranscribeSeedQRWholeQRView_24_Compact"),
            (seed_views.SeedTranscribeSeedQRWholeQRView, dict(seed_num=2, seedqr_format=QRType.SEED__SEEDQR, num_modules=29), "SeedTranscribeSeedQRWholeQRView_24_Standard"),

            # Screenshot doesn't render properly due to how the transparency mask is pre-rendered
            # (seed_views.SeedTranscribeSeedQRZoomedInView, dict(seed_num=0, seedqr_format=QRType.SEED__SEEDQR)),

            (seed_views.SeedTranscribeSeedQRConfirmQRPromptView, dict(seed_num=0)),

            # Screenshot can't render live preview screens
            # (seed_views.SeedTranscribeSeedQRConfirmScanView, dict(seed_num=0)),

            #(seed_views.AddressVerificationStartView, dict(address=, script_type="nat", network="M")),
            #seed_views.AddressVerificationSigTypeView,
            #seed_views.SeedSingleSigAddressVerificationSelectSeedView,
            #seed_views.SeedAddressVerificationView,
            #seed_views.AddressVerificationSuccessView,

            seed_views.LoadMultisigWalletDescriptorView,
            seed_views.MultisigWalletDescriptorView,
            (seed_views.SeedDiscardView, dict(seed_num=0)),

            seed_views.SeedSignMessageConfirmMessageView,
            seed_views.SeedSignMessageConfirmAddressView,

            seed_views.SeedElectrumMnemonicStartView,
        ],
        "PSBT Views": [
            psbt_views.PSBTSelectSeedView, # this will fail, be rerun below
            psbt_views.PSBTOverviewView,
            psbt_views.PSBTUnsupportedScriptTypeWarningView,
            psbt_views.PSBTNoChangeWarningView,
            psbt_views.PSBTMathView,
            (psbt_views.PSBTAddressDetailsView, dict(address_num=0)),

            (NotYetImplementedView, {}, "PSBTChangeDetailsView_multisig_unverified"),  # Must manually re-run this below
            (psbt_views.PSBTChangeDetailsView, dict(change_address_num=0), "PSBTChangeDetailsView_multisig_verified"),

            (NotYetImplementedView, {}, "PSBTOverviewView_op_return"),  # Placeholder
            (NotYetImplementedView, {}, "PSBTOpReturnView_text"),       # Placeholder
            (NotYetImplementedView, {}, "PSBTOpReturnView_raw_hex_data"),  # Placeholder

            (psbt_views.PSBTAddressVerificationFailedView, dict(is_change=True, is_multisig=False), "PSBTAddressVerificationFailedView_singlesig_change"),
            (psbt_views.PSBTAddressVerificationFailedView, dict(is_change=False, is_multisig=False), "PSBTAddressVerificationFailedView_singlesig_selftransfer"),
            (psbt_views.PSBTAddressVerificationFailedView, dict(is_change=True, is_multisig=True), "PSBTAddressVerificationFailedView_multisig_change"),
            (psbt_views.PSBTAddressVerificationFailedView, dict(is_change=False, is_multisig=True), "PSBTAddressVerificationFailedView_multisig_selftransfer"),
            psbt_views.PSBTFinalizeView,
            #PSBTSignedQRDisplayView
            psbt_views.PSBTSigningErrorView,
        ],
        "Tools Views": [
            tools_views.ToolsMenuView,
            #ToolsImageEntropyLivePreviewView
            #ToolsImageEntropyFinalImageView
            tools_views.ToolsImageEntropyMnemonicLengthView,
            tools_views.ToolsDiceEntropyMnemonicLengthView,
            (tools_views.ToolsDiceEntropyEntryView, dict(total_rolls=50)),
            tools_views.ToolsCalcFinalWordNumWordsView,
            tools_views.ToolsCalcFinalWordFinalizePromptView,
            tools_views.ToolsCalcFinalWordCoinFlipsView,
            (tools_views.ToolsCalcFinalWordShowFinalWordView, {}, "ToolsCalcFinalWordShowFinalWordView_pick_word"),
            (tools_views.ToolsCalcFinalWordShowFinalWordView, dict(coin_flips="0010101"), "ToolsCalcFinalWordShowFinalWordView_coin_flips"),
            #tools_views.ToolsCalcFinalWordDoneView,
            tools_views.ToolsAddressExplorerSelectSourceView,
            tools_views.ToolsAddressExplorerAddressTypeView,
            tools_views.ToolsAddressExplorerAddressListView,
            #tools_views.ToolsAddressExplorerAddressView,
        ],
        "Settings Views": settings_views_list + [
            settings_views.IOTestView,
            settings_views.DonateView,
            (settings_views.SettingsIngestSettingsQRView, dict(data=settingsqr_data_persistent), "SettingsIngestSettingsQRView_persistent"),
            (settings_views.SettingsIngestSettingsQRView, dict(data=settingsqr_data_not_persistent), "SettingsIngestSettingsQRView_not_persistent"),
        ],
        "Misc Error Views": [
            NotYetImplementedView,
            (UnhandledExceptionView, dict(error=UnhandledExceptionViewFood)),
            NetworkMismatchErrorView,
            (OptionDisabledView, dict(settings_attr=SettingsConstants.SETTING__MESSAGE_SIGNING)),
            (ErrorView, dict(
                title="Error",
                status_headline="Unknown QR Type",
                text="QRCode is invalid or is a data format not yet supported.",
                button_text="Back",
            )),
        ]
    }

    readme = f"""# SeedSigner Screenshots\n"""

    def screencap_view(view_cls: View, view_args: dict = {}, view_name: str = None, toast_thread: BaseToastOverlayManagerThread = None):
        if not view_name:
            view_name = view_cls.__name__
        screenshot_renderer.set_screenshot_filename(f"{view_name}.png")
        try:
            print(f"Running {view_name}")
            try:
                view_cls(**view_args).run()
            except ScreenshotComplete:
                if toast_thread is not None:
                    controller.activate_toast(toast_thread)
                    while controller.toast_notification_thread.is_alive():
                        time.sleep(0.1)
                raise ScreenshotComplete()
        except ScreenshotComplete:
            # Slightly hacky way to exit ScreenshotRenderer as expected
            pass
            print(f"Completed {view_name}")
        except Exception as e:
            # Something else went wrong
            from traceback import print_exc
            print_exc()
            raise e
        finally:
            if toast_thread:
                toast_thread.stop()

    for section_name, screenshot_list in screenshot_sections.items():
        subdir = section_name.lower().replace(" ", "_")
        screenshot_renderer.set_screenshot_path(os.path.join(screenshot_root, subdir))
        readme += "\n\n---\n\n"
        readme += f"## {section_name}\n\n"
        readme += """<table style="border: 0;">"""
        readme += f"""<tr><td align="center">\n"""
        for screenshot in screenshot_list:
            if type(screenshot) == tuple:
                if len(screenshot) == 2:
                    view_cls, view_args = screenshot
                    view_name = view_cls.__name__
                elif len(screenshot) == 3:
                    view_cls, view_args, view_name = screenshot
                elif len(screenshot) == 4:
                    view_cls, view_args, view_name, toast_thread = screenshot
            else:
                view_cls = screenshot
                view_args = {}
                view_name = view_cls.__name__
                toast_thread = None

            screencap_view(view_cls, view_args=view_args, view_name=view_name, toast_thread=toast_thread)
            readme += """  <table align="left" style="border: 1px solid gray;">"""
            readme += f"""<tr><td align="center">{view_name}<br/><br/><img src="{subdir}/{view_name}.png"></td></tr>"""
            readme += """</table>\n"""

        readme += "</td></tr></table>"

    # Re-render some screens that require more manual intervention / setup than the above
    # scripting can support.
    screenshot_renderer.set_screenshot_path(os.path.join(screenshot_root, "psbt_views"))

    # Render the PSBTChangeDetailsView_multisig_unverified screenshot
    decoder = DecodeQR()
    decoder.add_data(BASE64_PSBT_1)
    controller.psbt = decoder.get_psbt()
    controller.psbt_seed = seed_12b
    controller.multisig_wallet_descriptor = None
    screencap_view(psbt_views.PSBTChangeDetailsView, view_name='PSBTChangeDetailsView_multisig_unverified', view_args=dict(change_address_num=0))

    controller.psbt_seed = None
    screencap_view(psbt_views.PSBTSelectSeedView, view_name='PSBTSelectSeedView')

    # Render OP_RETURN screens for real
    controller.psbt_seed = seed_12b
    decoder = DecodeQR()
    decoder.add_data(BASE64_PSBT_WITH_OP_RETURN_TEXT)
    controller.psbt = decoder.get_psbt()
    controller.psbt_parser = PSBTParser(p=controller.psbt, seed=seed_12b)
    screencap_view(psbt_views.PSBTOverviewView, view_name='PSBTOverviewView_op_return')
    screencap_view(psbt_views.PSBTOpReturnView, view_name="PSBTOpReturnView_text")

    decoder.add_data(BASE64_PSBT_WITH_OP_RETURN_RAW_BYTES)
    controller.psbt = decoder.get_psbt()
    controller.psbt_parser = PSBTParser(p=controller.psbt, seed=seed_12b)
    screencap_view(psbt_views.PSBTOpReturnView, view_name="PSBTOpReturnView_raw_hex_data")

    with open(os.path.join(screenshot_root, "README.md"), 'w') as readme_file:
       readme_file.write(readme)
