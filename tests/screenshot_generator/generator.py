import embit
import os
import sys
from mock import Mock, patch, MagicMock

# Prevent importing modules w/Raspi hardware dependencies.
# These must precede any SeedSigner imports.
sys.modules['seedsigner.hardware.ST7789'] = MagicMock()
sys.modules['seedsigner.gui.screens.screensaver'] = MagicMock()
sys.modules['seedsigner.views.screensaver'] = MagicMock()
sys.modules['seedsigner.hardware.buttons'] = MagicMock()
sys.modules['seedsigner.hardware.camera'] = MagicMock()
sys.modules['seedsigner.hardware.microsd'] = MagicMock()


from seedsigner.controller import Controller
from seedsigner.gui.renderer import Renderer
from seedsigner.hardware.buttons import HardwareButtons
from seedsigner.hardware.camera import Camera
from seedsigner.models.decode_qr import DecodeQR
from seedsigner.models.qr_type import QRType
from seedsigner.models.seed import Seed
from seedsigner.models.settings import Settings
from seedsigner.models.settings_definition import SettingsConstants, SettingsDefinition
from seedsigner.views import (MainMenuView, PowerOptionsView, RestartView, NotYetImplementedView, UnhandledExceptionView, RemoveMicroSDWarningView,
    psbt_views, scan_views, seed_views, settings_views, tools_views)
from seedsigner.views.view import View

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

    controller = Controller.get_instance()

    # Set up some test data that we'll need in the `Controller` for certain Views
    mnemonic_12 = "forum undo fragile fade shy sign arrest garment culture tube off merit".split()
    mnemonic_24 = "attack pizza motion avocado network gather crop fresh patrol unusual wild holiday candy pony ranch winter theme error hybrid van cereal salon goddess expire".split()
    mnemonic_12b = ["abandon"] * 11 + ["about"]
    seed_12 = Seed(mnemonic=mnemonic_12, passphrase="cap*BRACKET3stove", wordlist_language_code=SettingsConstants.WORDLIST_LANGUAGE__ENGLISH)
    seed_12b = Seed(mnemonic=mnemonic_12b, wordlist_language_code=SettingsConstants.WORDLIST_LANGUAGE__ENGLISH)
    seed_24 = Seed(mnemonic=mnemonic_24, passphrase="some-PASS*phrase9", wordlist_language_code=SettingsConstants.WORDLIST_LANGUAGE__ENGLISH)
    controller.storage.seeds.append(seed_12)
    controller.storage.seeds.append(seed_12b)
    controller.storage.set_pending_seed(seed_24)
    UnhandledExceptionViewFood = ["IndexError", "line 1, in some_buggy_code.py", "list index out of range"]

    # Load a PSBT into memory
    BASE64_PSBT_1 = """cHNidP8BAP06AQIAAAAC5l4E3oEjI+H0im8t/K2nLmF5iJFdKEiuQs8ESveWJKcAAAAAAP3///8iBZMRhYIq4s/LmnTmKBi79M8ITirmsbO++63evK4utwAAAAAA/f///wZYQuoDAAAAACIAIAW5jm3UnC5fyjKCUZ8LTzjENtb/ioRTaBMXeSXsB3n+bK2fCgAAAAAWABReJY7akT1+d+jx475yBRWORdBd7VxbUgUAAAAAFgAU4wj9I/jB3GjNQudNZAca+7g9R16iWtYOAAAAABYAFIotPApLZlfscg8f3ppKqO3qA5nv7BnMFAAAAAAiACAs6SGc8qv4FwuNl0G0SpMZG8ODUEk5RXiWUcuzzw5iaRSfAhMAAAAAIgAgW0f5QxQIgVCGQqKzsvfkXZjUxdFop5sfez6Pt8mUbmZ1AgAAAAEAkgIAAAABAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAD/////BQIRAgEB/////wJAvkAlAAAAACIAIIRPoo2LvkrwrhrYFhLhlP43izxbA4Eo6Y6iFFiQYdXRAAAAAAAAAAAmaiSqIant4vYcP3HR3v0/qZnfo2lTdVxpBol5mWK0i+vYNpdOjPkAAAAAAQErQL5AJQAAAAAiACCET6KNi75K8K4a2BYS4ZT+N4s8WwOBKOmOohRYkGHV0QEFR1EhArGhNdUqlR4BAOLGTMrY2ZJYTQNRudp7fU7i8crRJqgEIQNDxn7PjUzvsP6KYw4s7dmoZE0qO1K6MaM+2ScRZ7hyxFKuIgYCsaE11SqVHgEA4sZMytjZklhNA1G52nt9TuLxytEmqAQcc8XaCjAAAIABAACAAAAAgAIAAIAAAAAAAwAAACIGA0PGfs+NTO+w/opjDizt2ahkTSo7Uroxoz7ZJxFnuHLEHCK94akwAACAAQAAgAAAAIACAACAAAAAAAMAAAAAAQCSAgAAAAEAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAP////8FAhACAQH/////AkC+QCUAAAAAIgAghE+ijYu+SvCuGtgWEuGU/jeLPFsDgSjpjqIUWJBh1dEAAAAAAAAAACZqJKohqe3i9hw/cdHe/T+pmd+jaVN1XGkGiXmZYrSL69g2l06M+QAAAAABAStAvkAlAAAAACIAIIRPoo2LvkrwrhrYFhLhlP43izxbA4Eo6Y6iFFiQYdXRAQVHUSECsaE11SqVHgEA4sZMytjZklhNA1G52nt9TuLxytEmqAQhA0PGfs+NTO+w/opjDizt2ahkTSo7Uroxoz7ZJxFnuHLEUq4iBgKxoTXVKpUeAQDixkzK2NmSWE0DUbnae31O4vHK0SaoBBxzxdoKMAAAgAEAAIAAAACAAgAAgAAAAAADAAAAIgYDQ8Z+z41M77D+imMOLO3ZqGRNKjtSujGjPtknEWe4csQcIr3hqTAAAIABAACAAAAAgAIAAIAAAAAAAwAAAAABAUdRIQJ5XLCBS0hdo4NANq4lNhimzhyHj7dvObmPAwNj8L2xASEC9mwwoH28/WHnxbb6z05sJ/lHuvrLs/wOooHgFn5ulI1SriICAnlcsIFLSF2jg0A2riU2GKbOHIePt285uY8DA2PwvbEBHCK94akwAACAAQAAgAAAAIACAACAAQAAAAEAAAAiAgL2bDCgfbz9YefFtvrPTmwn+Ue6+suz/A6igeAWfm6UjRxzxdoKMAAAgAEAAIAAAACAAgAAgAEAAAABAAAAAAAAAAEBR1EhAgpbWcEh7rgvRE5UaCcqzWL/TR1B/DS8UeZsKVEvuKLrIQOwLg0emiQbbxafIh69Xjtpj4eclsMhKq1y/7vYDdE7LVKuIgICCltZwSHuuC9ETlRoJyrNYv9NHUH8NLxR5mwpUS+4ouscc8XaCjAAAIABAACAAAAAgAIAAIAAAAAABQAAACICA7AuDR6aJBtvFp8iHr1eO2mPh5yWwyEqrXL/u9gN0TstHCK94akwAACAAQAAgAAAAIACAACAAAAAAAUAAAAAAQFHUSECk50GLh/YhZaLJkDq/dugU3H/WvE6rTgQuY6N57pI4ykhA/H8MdLVP9SA/Hg8l3hvibSaC1bCBzwz7kTW+rsEZ8uFUq4iAgKTnQYuH9iFlosmQOr926BTcf9a8TqtOBC5jo3nukjjKRxzxdoKMAAAgAEAAIAAAACAAgAAgAAAAAAGAAAAIgID8fwx0tU/1ID8eDyXeG+JtJoLVsIHPDPuRNb6uwRny4UcIr3hqTAAAIABAACAAAAAgAIAAIAAAAAABgAAAAA="""
    decoder = DecodeQR()
    decoder.add_data(BASE64_PSBT_1)
    controller.psbt = decoder.get_psbt()
    controller.psbt_seed = seed_12b

    # Multisig wallet descriptor for the multisig in the above PSBT
    MULTISIG_WALLET_DESCRIPTOR = """wsh(sortedmulti(1,[22bde1a9/48h/1h/0h/2h]tpubDFfsBrmpj226ZYiRszYi2qK6iGvh2vkkghfGB2YiRUVY4rqqedHCFEgw12FwDkm7rUoVtq9wLTKc6BN2sxswvQeQgp7m8st4FP8WtP8go76/{0,1}/*,[73c5da0a/48h/1h/0h/2h]tpubDFH9dgzveyD8zTbPUFuLrGmCydNvxehyNdUXKJAQN8x4aZ4j6UZqGfnqFrD4NqyaTVGKbvEW54tsvPTK2UoSbCC1PJY8iCNiwTL3RWZEheQ/{0,1}/*))#3jhtf6yx"""
    controller.multisig_wallet_descriptor = embit.descriptor.Descriptor.from_string(MULTISIG_WALLET_DESCRIPTOR)

    def screencap_view(view_cls: View, view_name: str, view_args: dict={}):
        screenshot_renderer.set_screenshot_filename(f"{view_name}.png")
        try:
            print(f"Running {view_name}")
            view_cls(**view_args).run()
        except ScreenshotComplete:
            # Slightly hacky way to exit ScreenshotRenderer as expected
            pass
            print(f"Completed {view_name}")
        except Exception as e:
            # Something else went wrong
            print(repr(e))
            raise e
    
    # Automatically populate all Settings options Views
    settings_views_list = []
    settings_views_list.append(settings_views.SettingsMenuView)
    # so we get a choice for transcribe seed qr format
    controller.settings.set_value(
        attr_name=SettingsConstants.SETTING__COMPACT_SEEDQR,
        value=SettingsConstants.OPTION__ENABLED
    )
    for settings_entry in SettingsDefinition.settings_entries:
        if settings_entry.visibility == SettingsConstants.VISIBILITY__HIDDEN:
            continue

        settings_views_list.append((settings_views.SettingsEntryUpdateSelectionView, dict(attr_name=settings_entry.attr_name), f"SettingsEntryUpdateSelectionView_{settings_entry.attr_name}"))
    settings_views_list.append(settings_views.IOTestView)
    settings_views_list.append(settings_views.DonateView)
    

    screenshot_sections = {
        "Main Menu Views": [
            MainMenuView,
            PowerOptionsView,
            RestartView,
            #PowerOffView # this test is too real; pi will power-off
            NotYetImplementedView,
            (RemoveMicroSDWarningView, dict(next_view=seed_views.SeedsMenuView)),
            (RemoveMicroSDWarningView, dict(required=True, next_view=seed_views.SeedsMenuView), 'RemoveMicroSDWarningViewRequired'),
            (UnhandledExceptionView, dict(error=UnhandledExceptionViewFood)),
            (settings_views.SettingsIngestSettingsQRView, dict(data="settings::v1 name=factory_reset")),

        ],
        "Seed Views": [
            seed_views.SeedsMenuView,
            seed_views.LoadSeedView,
            seed_views.SeedMnemonicEntryView,
            seed_views.SeedMnemonicInvalidView,
            seed_views.SeedFinalizeView,
            seed_views.SeedAddPassphraseView,
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
            (seed_views.SeedTranscribeSeedQRWholeQRView, dict(seed_num=0, seedqr_format=QRType.SEED__SEEDQR, num_modules=25), "SeedTranscribeSeedQRWholeQRView_12_Standard"),
            (seed_views.SeedTranscribeSeedQRWholeQRView, dict(seed_num=0, seedqr_format=QRType.SEED__COMPACTSEEDQR, num_modules=21), "SeedTranscribeSeedQRWholeQRView_12_Compact"),

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
        ],
        "PSBT Views": [
            psbt_views.PSBTSelectSeedView, # this will fail, be rerun below
            psbt_views.PSBTOverviewView,
            psbt_views.PSBTUnsupportedScriptTypeWarningView,
            psbt_views.PSBTNoChangeWarningView,
            psbt_views.PSBTMathView,
            (psbt_views.PSBTAddressDetailsView, dict(address_num=0)),

            # TODO: Render Multisig change w/ and w/out the multisig wallet descriptor onboard
            (psbt_views.PSBTChangeDetailsView, dict(change_address_num=0)),
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
            #(tools_views.ToolsCalcFinalWordShowFinalWordView, dict(coin_flips=3)),
            #tools_views.ToolsCalcFinalWordDoneView,
            tools_views.ToolsAddressExplorerSelectSourceView,
            tools_views.ToolsAddressExplorerAddressTypeView,
            tools_views.ToolsAddressExplorerAddressListView,
            #tools_views.ToolsAddressExplorerAddressView,
        ],
        "Settings Views": settings_views_list,
    }


    screenshot_renderer.set_screenshot_path(screenshot_root)

    readme = f"""# SeedSigner Screenshots\n"""

    for section_name, screenshot_list in screenshot_sections.items():
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
            else:
                view_cls = screenshot
                view_args = {}
                view_name = view_cls.__name__

            screencap_view(view_cls, view_name, view_args)
            readme += """  <table align="left" style="border: 1px solid gray;">"""
            readme += f"""<tr><td align="center">{view_name}<br/><br/><img src="{view_name}.png"></td></tr>"""
            readme += """</table>\n"""

        readme += "</td></tr></table>"

    # many screens don't work, leaving a missing image, re-run here for now
    controller.psbt_seed = None
    screencap_view(psbt_views.PSBTSelectSeedView, 'PSBTSelectSeedView', {})

    with open(os.path.join(screenshot_renderer.screenshot_path, "README.md"), 'w') as readme_file:
       readme_file.write(readme)
