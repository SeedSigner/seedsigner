from dataclasses import dataclass
import embit
import pathlib
import pytest
import os
import random
import sys
import time
from unittest.mock import Mock, patch, MagicMock
from PIL import ImageFont

from embit import compact
from embit.psbt import PSBT, OutputScope
from embit.script import Script

# Prevent importing modules w/Raspi hardware dependencies.
# These must precede any SeedSigner imports.
sys.modules['seedsigner.hardware.displays.st7789_mpy'] = MagicMock()
sys.modules['seedsigner.hardware.displays.ili9341'] = MagicMock()
sys.modules['seedsigner.views.screensaver.ScreensaverScreen'] = MagicMock()
sys.modules['RPi'] = MagicMock()
sys.modules['RPi.GPIO'] = MagicMock()
sys.modules['seedsigner.hardware.camera.Camera'] = MagicMock()
sys.modules['seedsigner.hardware.microsd'] = MagicMock()

from seedsigner.controller import Controller
from seedsigner.gui.components import GUIConstants
from seedsigner.gui.renderer import Renderer
from seedsigner.gui.screens.screen import BaseScreen
from seedsigner.gui.screens.seed_screens import SeedAddPassphraseScreen
from seedsigner.gui.toast import RemoveSDCardToastManagerThread, SDCardStateChangeToastManagerThread
from seedsigner.gui.toast import DefaultToast, InfoToast, SuccessToast, WarningToast, ErrorToast, DireWarningToast
from seedsigner.hardware.microsd import MicroSD
from seedsigner.helpers import embit_utils
from seedsigner.models.decode_qr import DecodeQR
from seedsigner.models.encode_qr import BaseQrEncoder
from seedsigner.models.psbt_parser import OPCODES, PSBTParser
from seedsigner.models.qr_type import QRType
from seedsigner.models.seed import Seed
from seedsigner.models.settings import Settings
from seedsigner.models.settings_definition import SettingsConstants, SettingsDefinition
from seedsigner.views import (MainMenuView, PowerOptionsView, RestartView, RemoveMicroSDWarningView, NotYetImplementedView, UnhandledExceptionView, 
    psbt_views, seed_views, settings_views, tools_views, scan_views)
from seedsigner.views.screensaver import OpeningSplashView
from seedsigner.views.view import CameraConnectionErrorView, NetworkMismatchErrorView, OptionDisabledView, PowerOffView

from .utils import ScreenshotComplete, ScreenshotConfig, ScreenshotRenderer

import warnings; warnings.warn = lambda *args, **kwargs: None

# Dynamically generate a pytest test run for each locale
@pytest.mark.parametrize("locale", [x for x, y in SettingsConstants.get_detected_languages()])
def test_generate_all(locale, target_locale):
    """
    `target_locale` is a fixture created in conftest.py via the `--locale` command line arg.

    Optionally skips all other locales.
    """
    if target_locale and locale != target_locale:
        pytest.skip(f"Skipping {locale}")
    
    if not ImageFont.core.HAVE_RAQM:
        # We can't generate pixel-perfect screenshots that match what gets rendered on
        # the device if we don't have libraqm.
        pytest.fail("libraqm is not installed.")
    
    generate_screenshots(locale)



"""**************************************************************************************
    Set up global test data that will be re-used across a variety of screenshots and for
    all locales.
**************************************************************************************"""
# Single sig ("abandon" test wallet) tx; 1mil sat input, 1 external output, 1 self-transfer, 1 change output, 400 sat fee
BASE64_SINGLE_SIG_PSBT = """cHNidP8BAJACAAAAAT8SmJzLhTMNgtn9QOmBmet0nnqqIJpsgpgBN5JWNJCxAQAAAAD9////A5CfBwAAAAAAFgAULzSqHPAKU7BVopGgOn1F8KaYi1KQ0AMAAAAAABYAFGQh2ztS8DzX4kGVKUKQhFPrlNNIkNADAAAAAAAWABRvoBZQCjxqc367Jg4t3KeLqSNFWGYAAABPAQQ1h88DDvSxr4AAAAA8jCA37kwWIdoNNI21EWNwmmItDSg43ebYQZxR9jAcYgO4jg++P2RjN+2TvAwPO4Q/z30lieXsiEdU5kAgJ6iQtBBzxdoKVAAAgAEAAIAAAACAAAEAcQIAAAABF84F9MpvLC1H3Cyews1xoNZ4ch3uJMu8jonehCIqmScAAAAAAP3///8CM6/2KQEAAAAWABQQumvlzzcWsGXBNIOliqXTvr9YxEBCDwAAAAAAFgAU0MSj7wnpl7bpnjl+UY/j5BoRjKFNAAAAAQEfQEIPAAAAAAAWABTQxKPvCemXtumeOX5Rj+PkGhGMoQEDBAEAAAAiBgLnqyU3tdSelwMJquBunknzbOHJ/rvUTsjg0cygtPnDGRhzxdoKVAAAgAEAAIAAAACAAAAAAAAAAAAAIgIDXUnszVTQCZ5DZ2J3x6bUYl1hHaiKXfSb+VF6d5Gnd6UYc8XaClQAAIABAACAAAAAgAEAAAAAAAAAAAAiAgPu7SBaaQIv7UpioCRX82mbGcBr90v4AazG2a6EvBap4RhzxdoKVAAAgAEAAIAAAACAAAAAAAEAAAAA"""

BASE64_MULTISIG_PSBT = """cHNidP8BAP06AQIAAAAC5l4E3oEjI+H0im8t/K2nLmF5iJFdKEiuQs8ESveWJKcAAAAAAP3///8iBZMRhYIq4s/LmnTmKBi79M8ITirmsbO++63evK4utwAAAAAA/f///wZYQuoDAAAAACIAIAW5jm3UnC5fyjKCUZ8LTzjENtb/ioRTaBMXeSXsB3n+bK2fCgAAAAAWABReJY7akT1+d+jx475yBRWORdBd7VxbUgUAAAAAFgAU4wj9I/jB3GjNQudNZAca+7g9R16iWtYOAAAAABYAFIotPApLZlfscg8f3ppKqO3qA5nv7BnMFAAAAAAiACAs6SGc8qv4FwuNl0G0SpMZG8ODUEk5RXiWUcuzzw5iaRSfAhMAAAAAIgAgW0f5QxQIgVCGQqKzsvfkXZjUxdFop5sfez6Pt8mUbmZ1AgAAAAEAkgIAAAABAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAD/////BQIRAgEB/////wJAvkAlAAAAACIAIIRPoo2LvkrwrhrYFhLhlP43izxbA4Eo6Y6iFFiQYdXRAAAAAAAAAAAmaiSqIant4vYcP3HR3v0/qZnfo2lTdVxpBol5mWK0i+vYNpdOjPkAAAAAAQErQL5AJQAAAAAiACCET6KNi75K8K4a2BYS4ZT+N4s8WwOBKOmOohRYkGHV0QEFR1EhArGhNdUqlR4BAOLGTMrY2ZJYTQNRudp7fU7i8crRJqgEIQNDxn7PjUzvsP6KYw4s7dmoZE0qO1K6MaM+2ScRZ7hyxFKuIgYCsaE11SqVHgEA4sZMytjZklhNA1G52nt9TuLxytEmqAQcc8XaCjAAAIABAACAAAAAgAIAAIAAAAAAAwAAACIGA0PGfs+NTO+w/opjDizt2ahkTSo7Uroxoz7ZJxFnuHLEHCK94akwAACAAQAAgAAAAIACAACAAAAAAAMAAAAAAQCSAgAAAAEAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAP////8FAhACAQH/////AkC+QCUAAAAAIgAghE+ijYu+SvCuGtgWEuGU/jeLPFsDgSjpjqIUWJBh1dEAAAAAAAAAACZqJKohqe3i9hw/cdHe/T+pmd+jaVN1XGkGiXmZYrSL69g2l06M+QAAAAABAStAvkAlAAAAACIAIIRPoo2LvkrwrhrYFhLhlP43izxbA4Eo6Y6iFFiQYdXRAQVHUSECsaE11SqVHgEA4sZMytjZklhNA1G52nt9TuLxytEmqAQhA0PGfs+NTO+w/opjDizt2ahkTSo7Uroxoz7ZJxFnuHLEUq4iBgKxoTXVKpUeAQDixkzK2NmSWE0DUbnae31O4vHK0SaoBBxzxdoKMAAAgAEAAIAAAACAAgAAgAAAAAADAAAAIgYDQ8Z+z41M77D+imMOLO3ZqGRNKjtSujGjPtknEWe4csQcIr3hqTAAAIABAACAAAAAgAIAAIAAAAAAAwAAAAABAUdRIQJ5XLCBS0hdo4NANq4lNhimzhyHj7dvObmPAwNj8L2xASEC9mwwoH28/WHnxbb6z05sJ/lHuvrLs/wOooHgFn5ulI1SriICAnlcsIFLSF2jg0A2riU2GKbOHIePt285uY8DA2PwvbEBHCK94akwAACAAQAAgAAAAIACAACAAQAAAAEAAAAiAgL2bDCgfbz9YefFtvrPTmwn+Ue6+suz/A6igeAWfm6UjRxzxdoKMAAAgAEAAIAAAACAAgAAgAEAAAABAAAAAAAAAAEBR1EhAgpbWcEh7rgvRE5UaCcqzWL/TR1B/DS8UeZsKVEvuKLrIQOwLg0emiQbbxafIh69Xjtpj4eclsMhKq1y/7vYDdE7LVKuIgICCltZwSHuuC9ETlRoJyrNYv9NHUH8NLxR5mwpUS+4ouscc8XaCjAAAIABAACAAAAAgAIAAIAAAAAABQAAACICA7AuDR6aJBtvFp8iHr1eO2mPh5yWwyEqrXL/u9gN0TstHCK94akwAACAAQAAgAAAAIACAACAAAAAAAUAAAAAAQFHUSECk50GLh/YhZaLJkDq/dugU3H/WvE6rTgQuY6N57pI4ykhA/H8MdLVP9SA/Hg8l3hvibSaC1bCBzwz7kTW+rsEZ8uFUq4iAgKTnQYuH9iFlosmQOr926BTcf9a8TqtOBC5jo3nukjjKRxzxdoKMAAAgAEAAIAAAACAAgAAgAAAAAAGAAAAIgID8fwx0tU/1ID8eDyXeG+JtJoLVsIHPDPuRNb6uwRny4UcIr3hqTAAAIABAACAAAAAgAIAAIAAAAAABgAAAAA="""
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
psbt = PSBT.from_base64(BASE64_MULTISIG_PSBT)

# Simplify the output side
output = psbt.outputs[-1]
psbt.outputs.clear()
psbt.outputs.append(output)
assert len(psbt.outputs) == 1
BASE64_PSBT_WITH_OP_RETURN_TEXT = add_op_return_to_psbt(psbt, raw_payload_data)

# Prep a PSBT with a (repeatably) random 80-byte OP_RETURN
random.seed(6102)
BASE64_PSBT_WITH_OP_RETURN_RAW_BYTES = add_op_return_to_psbt(PSBT.from_base64(BASE64_MULTISIG_PSBT), random.randbytes(80))

mnemonic_12 = "forum undo fragile fade shy sign arrest garment culture tube off merit".split()
mnemonic_24 = "attack pizza motion avocado network gather crop fresh patrol unusual wild holiday candy pony ranch winter theme error hybrid van cereal salon goddess expire".split()
seed_12 = Seed(mnemonic=mnemonic_12, passphrase="cap*BRACKET3stove", wordlist_language_code=SettingsConstants.WORDLIST_LANGUAGE__ENGLISH)
seed_24 = Seed(mnemonic=mnemonic_24, passphrase="some-PASS*phrase9", wordlist_language_code=SettingsConstants.WORDLIST_LANGUAGE__ENGLISH)
seed_24_w_passphrase = Seed(mnemonic=mnemonic_24, passphrase="some-PASS*phrase9", wordlist_language_code=SettingsConstants.WORDLIST_LANGUAGE__ENGLISH)

MULTISIG_WALLET_DESCRIPTOR = """wsh(sortedmulti(1,[22bde1a9/48h/1h/0h/2h]tpubDFfsBrmpj226ZYiRszYi2qK6iGvh2vkkghfGB2YiRUVY4rqqedHCFEgw12FwDkm7rUoVtq9wLTKc6BN2sxswvQeQgp7m8st4FP8WtP8go76/{0,1}/*,[73c5da0a/48h/1h/0h/2h]tpubDFH9dgzveyD8zTbPUFuLrGmCydNvxehyNdUXKJAQN8x4aZ4j6UZqGfnqFrD4NqyaTVGKbvEW54tsvPTK2UoSbCC1PJY8iCNiwTL3RWZEheQ/{0,1}/*))#3jhtf6yx"""


# Wrap QRDisplayScreen's `render_brightness_tip` in a simple View + Screen so we
# can call it outside of its child thread and generate a screenshot.
class SeedExportXpubQR_ScreenBrightnessView(seed_views.SeedExportXpubQRDisplayView):
    @dataclass
    class QRDisplayScreenBrightnessTipScreen(BaseScreen):
        qr_encoder: BaseQrEncoder = None

        def _render(self):
            from seedsigner.gui.screens.screen import QRDisplayScreen
            image = self.qr_encoder.part_to_image(self.qr_encoder.cur_part(), 240, 240, border=2, background_color="white")
            QRDisplayScreen.QRDisplayThread.render_brightness_tip(None, image)
            self.renderer.show_image(image)

    def run(self):
        self.run_screen(
            SeedExportXpubQR_ScreenBrightnessView.QRDisplayScreenBrightnessTipScreen,
            qr_encoder=self.qr_encoder,  # initialized by SeedExportXpubQRDisplayView
        )



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
        decoder.add_data(BASE64_MULTISIG_PSBT)
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

        # so we get a choice for transcribe seed qr format
        controller.settings.set_value(
            attr_name=SettingsConstants.SETTING__COMPACT_SEEDQR,
            value=SettingsConstants.OPTION__ENABLED
        )

        # Automatically populate all Settings options Views
        settings_views_list = []
        def add_settings_entries(visibility = SettingsConstants.VISIBILITY__GENERAL):
            for settings_entry in SettingsDefinition.settings_entries:
                if settings_entry.visibility != visibility:
                    continue

                if settings_entry.attr_name == SettingsConstants.SETTING__LOCALE:
                    # Locale selection has its own dedicated View
                    settings_views_list.append(ScreenshotConfig(settings_views.LocaleSelectionView))
                else:
                    # Generic SettingsEntry selection View
                    settings_views_list.append(ScreenshotConfig(settings_views.SettingsEntryUpdateSelectionView, dict(attr_name=settings_entry.attr_name), screenshot_name=f"SettingsEntryUpdateSelectionView_{settings_entry.attr_name}"))

        # Add the top level "General" settings menu and entries
        settings_views_list.append(ScreenshotConfig(settings_views.SettingsMenuView))
        add_settings_entries(SettingsConstants.VISIBILITY__GENERAL)

        # Add the "Advanced" menu...
        settings_views_list.append(
            ScreenshotConfig(
                settings_views.SettingsMenuView,
                dict(
                    visibility=SettingsConstants.VISIBILITY__ADVANCED,
                ),
                screenshot_name="SettingsMenuView__Advanced"
            )
        )

        # ...and Advanced entries
        add_settings_entries(SettingsConstants.VISIBILITY__ADVANCED)

        # Render the nested "Advanced" -> "Hardware" submenu
        settings_views_list.append(
            ScreenshotConfig(
                settings_views.SettingsMenuView,
                dict(visibility=SettingsConstants.VISIBILITY__HARDWARE),
                screenshot_name="SettingsMenuView__Hardware"
            )
        )
        add_settings_entries(SettingsConstants.VISIBILITY__HARDWARE)

        settingsqr_data_persistent = f"settings::v1 name=English_noob_mode persistent=E xpub_qr=urca,sta denom=thr network=M qr_density=M sigs=ss scripts=nat xpub_details=E passphrase=E camera=0 compact_seedqr=E bip85=D priv_warn=E dire_warn=E partners=E locale={locale}"
        settingsqr_data_not_persistent = f"settings::v1 name=Mode_Ephemeral persistent=D xpub_qr=urca,sta denom=thr network=M qr_density=M sigs=ss scripts=nat xpub_details=E passphrase=E camera=0 compact_seedqr=E bip85=D priv_warn=E dire_warn=E partners=E locale={locale}"

        # Set up screenshot-specific callbacks to inject data before the View is run and
        # reset data after the View is run.
        def load_single_sig_psbt_cb():
            decoder = DecodeQR()
            decoder.add_data(BASE64_SINGLE_SIG_PSBT)
            controller.psbt = decoder.get_psbt()
            controller.psbt_seed = seed_12b
            controller.psbt_parser = PSBTParser(p=controller.psbt, seed=seed_12b)
            controller.multisig_wallet_descriptor = None


        def load_multisig_psbt_cb():
            decoder = DecodeQR()
            decoder.add_data(BASE64_MULTISIG_PSBT)
            controller.psbt = decoder.get_psbt()
            controller.psbt_seed = seed_12b
            controller.psbt_parser = PSBTParser(p=controller.psbt, seed=seed_12b)
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


        def PSBTaddDNSSECproof():
            controller.psbt_parser.dnssec_proof = (b'craig@sparrowwallet.com', 
            b'\x00\x00.\x00\x01\x00\x00@r\x01\x13\x000\x08\x00\x00\x02\xa3\x00h\xa6a\x80h\x8a\xb2\x00Of\x00}\x11K\xf3>m \xe7X\x8f\xdf\xde\x9a\x9e*\x8e\xbdU\x93\xce\x8b\xc0d\x19\xe1\xd1\xa4\xaf\xa8vj\xbc\x16&PN\xa6$<\xa5\xfc\x9b\xceU\xa3\xf0<\x0e~\xb4\x88@\x96\x90\xd8L;\xeb0\xf2\x99\xda\x00z\xb6\x92\x99\xd0\xe2\x03\xc5\xb4K\x942\x82Hv\x80\x89\xa9 \
            \xb6\x89\x82e\x0e\x9c\xa2\xd3u&0|\xbd\x9f\x06i\x0eX\xc3\xc4\xa1p;\x1d\x11\x93\xea\x05\x01AyD\xb97\xb5\x93)N3\x95q\xee\xc4*<p\x0c\xe0u\xd9\xc4F\xe5\xd3+\xf9y9l\x1cy5\xf6\x9b\xd7\xdf(&V\x7f\xe5\x82\xa3a]`\x956\x8b\xe9\x91\xb1\xe5\xdc9\xc0\xaf;\x0c9\xe0\xe3S\xbb\xcb\x92\x8eR\xe8\x86\x19:\xc8\x8d\xa0\xcd\x86e\xea\x99+d)u\xaaT\x86\xf2\xe6QM \
            \x0bP\x86\xc6m\xddX\xfe\x8fz\'\xec\xb1(!\x1e<\xa1\xbd\xc4\xca\xd9\x1f<\xc9\xb6<Rn\xba\xea\x86\x07S\x18\xe3;\xfcZS\xc9\x19\xe6\xf0\x12b\xb2M\x17\x8e\xb2\xcd\x04\xb1\x00\x000\x00\x01\x00\x00@r\x01\x08\x01\x00\x03\x08\x03\x01\x00\x01\xb1\x1b\x18*FL:\xdce5\xaaYa;\xdaza\xca\xc8iE\xc2\x0bw0\x95\x94\x11\x94\xf4\xb9\xf5\x16\xe8\xbd\x92K\x1eP\xe3 \
            \xfe\x83\x91\x8bQ\xe5E)\xd4\xe5\xa1\xe4S\x03\xdf\x84b$\x1d^\x05\x97\x99y\xae[\xf9\xc6\xc5\x98\xc0\x8aIn\x17\xf3\xbd72\xd5\xae\xbebf{a\xdb\x1b\xbe\x17\x8f\'\xac\x99@\x81e\xa20\xd6\xae\xe7\x83H\xe6\xc6w\x89T\x1f\x84[*\xda\x96f\x7f\x8d\xd1j\xe4O\x9e&\x0cJ\x13\x8b;\xb1\x01Ye\xeb\xe6\tCJ\x06FK\xd7\xd2\x9b\xacG\xc3\x01~\x83\xc0\xf8\x9b\xca\x1a \
            \x9e;\xdd\x08\x13q_4\x84)-\xf5\x89\xbcc.\'\xd3~\xfc\x02\x83|\xb8]w\r[\xd5:6\xed\xc9\x9a\x82\x94w\x1a\xa9<\xf2$\x06\xf5Pl\x8c\xf8P\xed\x85\xc1\xa4u\xde\xe5\xc2\xd3p\x0b?V1\xd9\x03RK\x84\x99\x95\xc2\x0c\xb4\x07\xedA\x1fp\xb4(\xae=d\'\x16\xfe#\x935\xaa\x96\x1au.g\xfbm\xca\x0b\xf7)\x00\x000\x00\x01\x00\x00@r\x01\x08\x01\x00\x03\x08\x03\x01\x00 \
            \x01\xb6\xae\xc4\xb4\x85g\xe2\x92Z-\x9cO\xa4\xc9nm\xdd\xf8b\x15\xa9\xbd\x8d\xd5y\xc3\x8c\xcb\x11\x99\xed\x1b\xe8\x99F\xa7\xf7/\xc2c9\t\xa2y-\x0e\xed\x1bZ\xfb.\xe4\xc7\x8d\x86Zv\xd6\xcd\x93i\xd9\x99\xc9j\xf6\xbe\n"t\xb8\xf2\xe9\xe0\xa0\x06[\xd2\x02WW\x0f\x08\xbc\x14\xc1oV\x16Bh\x81\xa8=\xbc\xe6\x92n9\x1c\x13\x8a.\xc3\x17\xef\xa74\x92d\xde.y\x1c \
            \x9b}J`H\xeen\xed\xf2{\xf1\xec\xe3\x98\xff\r"\x9f\x187|\xb1\xf6\xb9\x8d\x12(\xef!{\x81F\xc0\xc78Q\xb8\x9ao\xc3|b\x1c\xa1\x87\xe1d(\xa7C\xff\xea\x00r\xe1\x85\xef\x93\xe3\x95%\xce\xe3\xad\x01\xe0\xc9M.Q\x1c\x8c13"\xc2\x9a\xb9\x161\xe1\x85`I\xa3h\x98hL0V\xe5\x99ts\x81o\xb5G\xac\xb0\xbenf\x0b\xdf\xa8\x9a\\\xb2\x8b6i\xd8b_?\x01\x8c{;\x8aH`\xe7t\xee \
            \x82a\x81\x1c\xe7\xf9lF\x1b\xc1b\xc1\xa3t\xf3\x00\x000\x00\x01\x00\x00@r\x01\x08\x01\x01\x03\x08\x03\x01\x00\x01\xac\xff\xb4\t\xbc\xc99\xf81\xf7\xa1\xe5\xec\x88\xf7\xa5\x92U\xecS\x04\x0b\xe42\x02s\x90\xa4\xce\x89mo\x90\x86\xf3\xc5\xe1w\xfb\xfe\x11\x81c\xaa\xecz\xf1F,G\x94YD\xc4\xe2\xc0&\xbe^\x98\xbb\xcd\xed%\x97\x82r\xe1\xe3\xe0y\xc5\tMW?\x0e \
            \x83\xc9/\x02\xb3-5\x13\xb1U\x0b\x82i)\xc8\r\xd0\xf9,\xac\x96m\x17v\x9f\xd5\x86{d|?8\x02\x9a\xbd\xc4\x81R\xeb\x8f qY\xec\xc5\xd22\xc7\xc1S|y\xf4\xb7\xac(\xff\x11h/!h\x1b\xf6\xd6\xab\xa5U\x03+\xf6\xf9\xf06\xbe\xb2\xaa\xa5\xb3w\x8dn\xeb\xfb\xa6\xbf\x9e\xa1\x91\xbeJ\xb0\xca\xeau\x9e/w:\x1f\x90)\xc7>\xcb\x8dW5\xb92\x1d\xb0\x85\xf1\xb8\xe2\xd8\x03 \
            \x8f\xe2\x94\x19\x92T\x8c\xee\rg\xddEG\xe1\x1d\xd6:\xf9\xc9\xfc\x1cTf\xfbhL\xf0\t\xd7\x19|,\xf7\x9ey*\xb5\x01\xe6\xa8\xa1\xcaQ\x9a\xf2\xcb\x9b_cg\xe9L\rGP$Q5{\xe1\xb5\x00\x000\x00\x01\x00\x00@r\x01\x08\x01\x01\x03\x08\x03\x01\x00\x01\xafz\x8d\xeb\xa4\x9d\x99Zy*\xef\xc8\x02c\xe9\x91\xef\xdb\xc8a8\xa91\xde\xb2\xc6]V\x82\xea\xb5\xd3\xb078\xe3\xdf \
            \xdc\x89\xd9m\xa6L\x86\xc0"M\x9c\xe0%\x14\xd2\x85\xda0h\xb1\x90T\xe5\xe7\x87\xb2\x96\x90X\xe9\x8e\x12Vl\x8c\x80\x8c@\xc0\xb7i\xe1\xdb\x1a$\xa1\xbd\x9b1\xe3\x03\x18J1\xfc{\xb5k\x85\xbb\xba\x8a\xbc\x02\xcdP@\xa4D\xa3mGiYi\x84\x9e\x16\xad\x85k\xb5\x8e\x8f\xac\x88U"D\x001\x9b\xda\xb2$\xd8?\xc0\xe6j\xab2\xfft\xbf\xea\xf0\xf9\x1cENhP\xa1)R\x07\xbb\xd4 \
            \xcd\xde\x8fo\xfb\x08\xfa\xa9u\\.2\x84\xef\xa0\x1f\x999>\x18xl\xb12\xf1\xe6n\xbce\x171\x8e\x1c\xe8\xa3\xb73~\xbbT\xd05\xabW\xd9pn\xcd\x93P\xd4\xaf\xac\xd8%\xe4<\x86h\xee\xce\x89\x81\x9c\xafh\x17\xafb\xdcO\xbd\x82\xf0\xe3?fG\xb2\xb6\xbd\xa1u\xf1F\x07\xf5\x9fF5E\x1ek\'\xdf(.\xf7=\x87\x03com\x00\x00+\x00\x01\x00\x00\xb0R\x00$M\x06\r\x02\x8a\xcb\xb0 \
            \xcd(\xf4\x12P\xa8\nI\x13\x89BM4\x15"\xd9F\xb0\xda\x0c\x02\x91\xf2\xd3\xd7q\xd7\x80Z\x03com\x00\x00.\x00\x01\x00\x00\xb0R\x01\x13\x00+\x08\x01\x00\x01Q\x80h\x9c\xfc\xd0h\x8b\xcb@\xb5i\x00\x92\xd8;\xb6#\x9d\x1b\xa6\xde\xd5\x9bO~\xe5/,\x15\x94\x8eO\x86\xc9\x9d\xdc\xd93\x16p\x99|\xbc\xd9\xbc\xa2\xab\x88%\x18\xb3\x8b~\xdf\xce\x82\x02/\xdcj\x0e\xde\x88Q} \
            \rL\xddp\x0b\xa8a:\xa9\xc0*\xee\xd6\x8c\xdb\xab\xe1LZ\x8c\n\xb2d\xcb\xb07P\xca\xd1\xd4\xcco\xb9\x83G\xf4\x98\x9b\xd7cc\xe8\xa0\xe4D\x96\x94@\xa0\x08;\x9c\xe6>Eau\xb0\n\xa1\xaeR\t\x96\x0b\xe2\xb1N \xec\xf4v\x17A\xe9\x80\xbf\xa0-\xd8\xc4*gh\xd1\xa3\xc2\xd4\x1e&\x86\x10L40Q\xe3_\x91\xdf\xdb9Xi!\x04\xe4\xcc\x0e:\xb1\x9f\x08\xf9\x88\x1d\xb4)1\xa7\xb7*\xa9 \
            \x9ahT\x8e\xbd[E\xa4\x17\xe7\x81\x84A\xe3\x18,b\xbf\x94\xce\x8f\x189\x85P\x9d}r\xd7-\xcc\xcf\xd8\x0cm\x85\x17\x9e:\xbc\x03\xc3-\xe8\xc4\xd5-w\x02\xda\xdf-\xe0;co\x89\xb694\xba\xe6\xca-AWZ\xd3\xfd\xa4\xe4\x8e]\xee\xac\xe4N\x17\xab\x19\x03com\x00\x00.\x00\x01\x00\x00\x19\xb8\x00W\x000\r\x01\x00\x01Q\x80h\x9f=\xfbh\x8bvOM\x06\x03com\x00\xd8ss\xf3\xd5\xd4 \
            \x04\xf7\xcd\xc3\xaa\xcec<\x965{\xc6\x06\xce\xd6 y%\x97\xe10\x8b\x1dlY\x02f\x8cM<\x1a7\xba\xb8Hk\xa2D\x85\xd5z\x9d\x98\x15\x7f\xe7\x06BK C\xbf\xb4\x03\x06\xd0\x14\x84\x03com\x00\x000\x00\x01\x00\x00\x19\xb8\x00D\x01\x00\x03\r\xf1{`\xfbV\xd5"\xf8cAS\xe7\x85\xc0\xa9xS.\xa7m\xe3\x9d4\xbb5m=\x04.\x07\xf2\x9f{\x99!v\xcc\x83\xac\xef{x\xeau\x04% ;\x18\xf2\xb8" \
            \x8b<\xdd+\xc7\xeb\x13\xc3\xe3\x03Z~\x03com\x00\x000\x00\x01\x00\x00\x19\xb8\x00D\x01\x01\x03\r\xb7\x1f\x04e\x10\x1d\xdb\xe2\xbf\x0c\x94U\xd1/\xa1l\x1c\xdaD\xf4\xbf\x1b\xa2U4\x18\xad\x1f:\xa9\xb0is\xf2\x1b\x84\xebS,\xf4\x03^\xe8\xd4\x83,\xa2m\x890j}2V\x0c\x0c\xb0\x12\x9dE\n\xc1\x085\rsparrowwallet\x03com\x00\x00+\x00\x01\x00\x00T_\x00$=\xc4\r\x02V\x04\r \
            \x99\x1c\x10u\xc4\xa8UTE\xf9\xa5\xceR\xceh\x01\xaa\xf4]>\x87f>\x7f\xbdh\xbc1+\rsparrowwallet\x03com\x00\x00+\x00\x01\x00\x00T_\x00$\xcf;\r\x02em\xa5\x986B/^\x19\x8es\xfc5\xe6\xa8\x9b\xc0\x83\x8d\xea\xacV^q\xa1\x98\x04\xfc\x12P\xe4\xce\rsparrowwallet\x03com\x00\x00.\x00\x01\x00\x00T_\x00W\x00+\r\x02\x00\x01Q\x80h\x95a\x02h\x8c\x16\x1aPA\x03com\x00\xf4\xc4 \
            \nX5#\xa7\xd4%P_2\x8a\xfe\x10\xe8\x16\xed\xe3\xf01\xd1Wr\xd87i\xec\x84\x90\xd0\x82\x16r\xe4\xee\xfbu\xfb\x0b\xe4\xff\xe8g\x15\xfb\xec)l\x109\x03h\xb3\x12\x08<kYu\xeb\xf7\xfc\xe6\rsparrowwallet\x03com\x00\x00.\x00\x01\x00\x00\x0e\x0f\x00e\x000\r\x02\x00\x00\x0e\x10h\x91\xef\xe0h~)`=\xc4\rsparrowwallet\x03com\x00+\x96\xadL\xdc\x86\x19\xf8\x9dt1ss\xff\x0b@\xb9 \
            \xde12\xcf\x95~\xe5|e< M\x1d6\x11\xd6&Mk\xae\xfb\x1cE\xc1\xfe-I\x9c\xc7u\x87\x18?I\x00\xa1\xf0Q+\x04x\xa6\x0eID\xc0A\rsparrowwallet\x03com\x00\x000\x00\x01\x00\x00\x0e\x0f\x00D\x01\x00\x03\r$\xc86K?\x94+\x00b\xf1\xc68\x80\xb9Y\xb2\xe7\x82\x7f\x1c\xff\xff\x8d^8\xf7\xfd\xe1\xb2-b\x1d\x1cJ\x0c\xd9\xa9\xb0\xc6\xc7\x0b\x1c\x94T<\xcd\xc5P$\x81\xae\xbdn+Del\x9e\xa39 \
            \xac\x81\xe8;\rsparrowwallet\x03com\x00\x000\x00\x01\x00\x00\x0e\x0f\x00D\x01\x00\x03\r\x95gl{%\xe7yJ\x8a~K\x19\xedc\x8eG\xac\xa75\xd0,\xe2\xdd\x08\xb2\x88l \xc3\x1a,\xb9\xe7\xcc\x8b\x85\x02:F\xee\xb67\x02\x01\x19\xdc\xaak\xbc\x07G\xe1#@\xfa\x811\x99y\x9d\xe5y\xde\x8a\rsparrowwallet\x03com\x00\x000\x00\x01\x00\x00\x0e\x0f\x00D\x01\x01\x03\r\xb07%!3\x7f\xd5m \
            \x8bb\xe9\x17\xb7\x86k\x7f\xaau=%2.\x12\xb5*>\xb5\xff\x9fL\x9ff"\x7fP\x8f\xe3;\xa19\xf2\xf15O\xe3\xde\xd6\xd3\xdav\xd4\x9b\xe9&\x19\x8d\xc2\x94\x0f,R\x82\xc7\xfe\rsparrowwallet\x03com\x00\x000\x00\x01\x00\x00\x0e\x0f\x00D\x01\x01\x03\r\xdd\xf9\x17t?2\nI\xf6!\x8dpb\x18\xb6\xca\xe5t\xf1\xdbv\x88U^\r_\x04U@]he\x99?\x01G\xfbK3\xba\xa2\x07\xb2\x8d#,\x9epA\x9d\xdc \
            \xaer\x05\x03\x11\t\x8c\xd4\xcf\xaa\x07\x96\x9b\x05craig\x04user\x10_bitcoin-payment\rsparrowwallet\x03com\x00\x00\x10\x00\x01\x00\x00\x0e\x0f\x0032bitcoin:bc1qwthe43xeuasklclq4kvhreluv3hu92rzej42js\x05craig\x04user\x10_bitcoin-payment\rsparrowwallet\x03com\x00\x00.\x00\x01\x00\x00\x0e\x0f\x00e\x00\x10\r\x05\x00\x00\x0e\x10h\x91\xef\xe0h~)`\xbb&\rsparrowwallet \
            \x03com\x00\xe7\xae\x93\xd2;tw7ULMR\xdd\x1e\xc0\xf5\x8cA\x1cjGM\xa4l<$\xd0\xdb\x97\r\x86\xe9\x1b\xf9\x1b^\xab\xeb\x1e\xd5\x91!g\x8e\xf54\xa2Zou\xce\x05\x88\xe6RD9\xc1\x1d \x8f0\x1dF')

        def PSBTaddwrongDNSSECproof():
            controller.psbt_parser.dnssec_proof = (b'craig@sparrowwallet.com', 
            b'\x00\x00.\x00\x01\x00\x00@r\x01\x13\x000\x08\x00\x00\x02\xa3\x00h\xa6a\x80h\x8a\xb2\x00Of\x00}\x11K\xf3>m \xe7X\x8f\xdf\xde\x9a\x9e*\x8e\xbdU\x93\xce\x8b\xc0d\x19\xe1\xd1\xa4\xaf\xa8vj\xbc\x16&PN\xa6$<\xa5\xfc\x9b\xceU\xa3\xf0<\x0e~\xb4\x88@\x96\x90\xd8L;\xeb0\xf2\x99\xda\x00z\xb6\x92\x99\xd0\xe2\x03\xc5\xb4K\x942\x82Hv\x80\x89\xa9\xb6\x89\x82e\x0e\x9c\xa2\xd3u&0|\xbd\x9f\x06i\x0eX\xc3\xc4\xa1p;\x1d\x11\x93\xea\x05\x01AyD\xb97\xb5\x93)N3\x95q\xee\xc4*<p\x0c\xe0u\xd9\xc4F\xe5\xd3+\xf9y9l\x1cy5\xf6\x9b\xd7\xdf(&V\x7f\xe5\x82\xa3a]`\x956\x8b\xe9\x91\xb1\xe5\xdc9\xc0\xaf;\x0c9\xe0\xe3S\xbb\xcb\x92\x8eR\xe8\x86\x19:\xc8\x8d\xa0\xcd\x86e\xea\x99+d)u\xaaT\x86\xf2\xe6QM\x0bP\x86\xc6m\xddX\xfe\x8fz\'\xec\xb1(!\x1e<\xa1\xbd\xc4\xca\xd9\x1f<\xc9\xb6<Rn\xba\xea\x86\x07S\x18\xe3;\xfcZS\xc9\x19\xe6\xf0\x12b\xb2M\x17\x8e\xb2\xcd\x04\xb1\x00\x000\x00\x01\x00\x00@r\x01\x08\x01\x00\x03\x08\x03\x01\x00\x01\xb1\x1b\x18*FL:\xdce5\xaaYa;\xdaza\xca\xc8iE\xc2\x0bw0\x95\x94\x11\x94\xf4\xb9\xf5\x16\xe8\xbd\x92K\x1eP\xe3\xfe\x83\x91\x8bQ\xe5E)\xd4\xe5\xa1\xe4S\x03\xdf\x84b$\x1d^\x05\x97\x99y\xae[\xf9\xc6\xc5\x98\xc0\x8aIn\x17\xf3\xbd72\xd5\xae\xbebf{a\xdb\x1b\xbe\x17\x8f\'\xac\x99@\x81e\xa20\xd6\xae\xe7\x83H\xe6\xc6w\x89T\x1f\x84[*\xda\x96f\x7f\x8d\xd1j\xe4O\x9e&\x0cJ\x13\x8b;\xb1\x01Ye\xeb\xe6\tCJ\x06FK\xd7\xd2\x9b\xacG\xc3\x01~\x83\xc0\xf8\x9b\xca\x1a\x9e;\xdd\x08\x13q_4\x84)-\xf5\x89\xbcc.\'\xd3~\xfc\x02\x83|\xb8]w\r[\xd5:6\xed\xc9\x9a\x82\x94w\x1a\xa9<\xf2$\x06\xf5Pl\x8c\xf8P\xed\x85\xc1\xa4u\xde\xe5\xc2\xd3p\x0b?V1\xd9\x03RK\x84\x99\x95\xc2\x0c\xb4\x07\xedA\x1fp\xb4(\xae=d\'\x16\xfe#\x935\xaa\x96\x1au.g\xfbm\xca\x0b\xf7)\x00\x000\x00\x01\x00\x00@r\x01\x08\x01\x00\x03\x08\x03\x01\x00\x01\xb6\xae\xc4\xb4\x85g\xe2\x92Z-\x9cO\xa4\xc9nm\xdd\xf8b\x15\xa9\xbd\x8d\xd5y\xc3\x8c\xcb\x11\x99\xed\x1b\xe8\x99F\xa7\xf7/\xc2c9\t\xa2y-\x0e\xed\x1bZ\xfb.\xe4\xc7\x8d\x86Zv\xd6\xcd\x93i\xd9\x99\xc9j\xf6\xbe\n"t\xb8\xf2\xe9\xe0\xa0\x06[\xd2\x02WW\x0f\x08\xbc\x14\xc1oV\x16Bh\x81\xa8=\xbc\xe6\x92n9\x1c\x13\x8a.\xc3\x17\xef\xa74\x92d\xde.y\x1c\x9b}J`H\xeen\xed\xf2{\xf1\xec\xe3\x98\xff\r"\x9f\x187|\xb1\xf6\xb9\x8d\x12(\xef!{\x81F\xc0\xc78Q\xb8\x9ao\xc3|b\x1c\xa1\x87\xe1d(\xa7C\xff\xea\x00r\xe1\x85\xef\x93\xe3\x95%\xce\xe3\xad\x01\xe0\xc9M.Q\x1c\x8c13"\xc2\x9a\xb9\x161\xe1\x85`I\xa3h\x98hL0V\xe5\x99ts\x81o\xb5G\xac\xb0\xbenf\x0b\xdf\xa8\x9a\\\xb2\x8b6i\xd8b_?\x01\x8c{;\x8aH`\xe7t\xee\x82a\x81\x1c\xe7\xf9lF\x1b\xc1b\xc1\xa3t\xf3\x00\x000\x00\x01\x00\x00@r\x01\x08\x01\x01\x03\x08\x03\x01\x00\x01\xac\xff\xb4\t\xbc\xc99\xf81\xf7\xa1\xe5\xec\x88\xf7\xa5\x92U\xecS\x04\x0b\xe42\x02s\x90\xa4\xce\x89mo\x90\x86\xf3\xc5\xe1w\xfb\xfe\x11\x81c\xaa\xecz\xf1F,G\x94YD\xc4\xe2\xc0&\xbe^\x98\xbb\xcd\xed%\x97\x82r\xe1\xe3\xe0y\xc5\tMW?\x0e\x83\xc9/\x02\xb3-5\x13\xb1U\x0b\x82i)\xc8\r\xd0\xf9,\xac\x96m\x17v\x9f\xd5\x86{d|?8\x02\x9a\xbd\xc4\x81R\xeb\x8f qY\xec\xc5\xd22\xc7\xc1S|y\xf4\xb7\xac(\xff\x11h/!h\x1b\xf6\xd6\xab\xa5U\x03+\xf6\xf9\xf06\xbe\xb2\xaa\xa5\xb3w\x8dn\xeb\xfb\xa6\xbf\x9e\xa1\x91\xbeJ\xb0\xca\xeau\x9e/w:\x1f\x90)\xc7>\xcb\x8dW5\xb92\x1d\xb0\x85\xf1\xb8\xe2\xd8\x03\x8f\xe2\x94\x19\x92T\x8c\xee\rg\xddEG\xe1\x1d\xd6:\xf9\xc9\xfc\x1cTf\xfbhL\xf0\t\xd7\x19|,\xf7\x9ey*\xb5\x01\xe6\xa8\xa1\xcaQ\x9a\xf2\xcb\x9b_cg\xe9L\rGP$Q5{\xe1\xb5\x00\x000\x00\x01\x00\x00#r\x01\x08\x01\x01\x03\x08\x03\x01\x00\x01\xafz\x8d\xeb\xa4\x9d\x99Zy*\xef\xc8\x02c\xe9\x91\xef\xdb\xc8a8\xa91\xde\xb2\xc6]V\x82\xea\xb5\xd3\xb078\xe3\xdf\xdc\x89\xd9m\xa6L\x86\xc0"M\x9c\xe0%\x14\xd2\x85\xda0h\xb1\x90T\xe5\xe7\x87\xb2\x96\x90X\xe9\x8e\x12Vl\x8c\x80\x8c@\xc0\xb7i\xe1\xdb\x1a$\xa1\xbd\x9b1\xe3\x03\x18J1\xfc{\xb5k\x85\xbb\xba\x8a\xbc\x02\xcdP@\xa4D\xa3mGiYi\x84\x9e\x16\xad\x85k\xb5\x8e\x8f\xac\x88U"D\x001\x9b\xda\xb2$\xd8?\xc0\xe6j\xab2\xfft\xbf\xea\xf0\xf9\x1cENhP\xa1)R\x07\xbb\xd4\xcd\xde\x8fo\xfb\x08\xfa\xa9u\\.2\x84\xef\xa0\x1f\x999>\x18xl\xb12\xf1\xe6n\xbce\x171\x8e\x1c\xe8\xa3\xb73~\xbbT\xd05\xabW\xd9pn\xcd\x93P\xd4\xaf\xac\xd8%\xe4<\x86h\xee\xce\x89\x81\x9c\xafh\x17\xafb\xdcO\xbd\x82\xf0\xe3?fG\xb2\xb6\xbd\xa1u\xf1F\x07\xf5\x9fF5E\x1ek\'\xdf(.\xf7=\x87\x03com\x00\x00+\x00\x01\x00\x00\xb0R\x00$M\x06\r\x02\x8a\xcb\xb0\xcd(\xf4\x12P\xa8\nI\x13\x89BM4\x15"\xd9F\xb0\xda\x0c\x02\x91\xf2\xd3\xd7q\xd7\x80Z\x03com\x00\x00.\x00\x01\x00\x00\xb0R\x01\x13\x00+\x08\x01\x00\x01Q\x80h\x9c\xfc\xd0h\x8b\xcb@\xb5i\x00\x92\xd8;\xb6#\x9d\x1b\xa6\xde\xd5\x9bO~\xe5/,\x15\x94\x8eO\x86\xc9\x9d\xdc\xd93\x16p\x99|\xbc\xd9\xbc\xa2\xab\x88%\x18\xb3\x8b~\xdf\xce\x82\x02/\xdcj\x0e\xde\x88Q}\rL\xddp\x0b\xa8a:\xa9\xc0*\xee\xd6\x8c\xdb\xab\xe1LZ\x8c\n\xb2d\xcb\xb07P\xca\xd1\xd4\xcco\xb9\x83G\xf4\x98\x9b\xd7cc\xe8\xa0\xe4D\x96\x94@\xa0\x08;\x9c\xe6>Eau\xb0\n\xa1\xaeR\t\x96\x0b\xe2\xb1N \xec\xf4v\x17A\xe9\x80\xbf\xa0-\xd8\xc4*gh\xd1\xa3\xc2\xd4\x1e&\x86\x10L40Q\xe3_\x91\xdf\xdb9Xi!\x04\xe4\xcc\x0e:\xb1\x9f\x08\xf9\x88\x1d\xb4)1\xa7\xb7*\xa9\x9ahT\x8e\xbd[E\xa4\x17\xe7\x81\x84A\xe3\x18,b\xbf\x94\xce\x8f\x189\x85P\x9d}r\xd7-\xcc\xcf\xd8\x0cm\x85\x17\x9e:\xbc\x03\xc3-\xe8\xc4\xd5-w\x02\xda\xdf-\xe0;co\x89\xb694\xba\xe6\xca-AWZ\xd3\xfd\xa4\xe4\x8e]\xee\xac\xe4N\x17\xab\x19\x03com\x00\x00.\x00\x01\x00\x00\x19\xb8\x00W\x000\r\x01\x00\x01Q\x80h\x9f=\xfbh\x8bvOM\x06\x03com\x00\xd8ss\xf3\xd5\xd4\x04\xf7\xcd\xc3\xaa\xcec<\x965{\xc6\x06\xce\xd6 y%\x97\xe10\x8b\x1dlY\x02f\x8cM<\x1a7\xba\xb8Hk\xa2D\x85\xd5z\x9d\x98\x15\x7f\xe7\x06BK C\xbf\xb4\x03\x06\xd0\x14\x84\x03com\x00\x000\x00\x01\x00\x00\x19\xb8\x00D\x01\x00\x03\r\xf1{`\xfbV\xd5"\xf8cAS\xe7\x85\xc0\xa9xS.\xa7m\xe3\x9d4\xbb5m=\x04.\x07\xf2\x9f{\x99!v\xcc\x83\xac\xef{x\xeau\x04% ;\x18\xf2\xb8"\x8b<\xdd+\xc7\xeb\x13\xc3\xe3\x03Z~\x03com\x00\x000\x00\x01\x00\x00\x19\xb8\x00D\x01\x01\x03\r\xb7\x1f\x04e\x10\x1d\xdb\xe2\xbf\x0c\x94U\xd1/\xa1l\x1c\xdaD\xf4\xbf\x1b\xa2U4\x18\xad\x1f:\xa9\xb0is\xf2\x1b\x84\xebS,\xf4\x03^\xe8\xd4\x83,\xa2m\x890j}2V\x0c\x0c\xb0\x12\x9dE\n\xc1\x085\rsparrowwallet\x03com\x00\x00+\x00\x01\x00\x00T_\x00$=\xc4\r\x02V\x04\r\x99\x1c\x10u\xc4\xa8UTE\xf9\xa5\xceR\xceh\x01\xaa\xf4]>\x87f>\x7f\xbdh\xbc1+\rsparrowwallet\x03com\x00\x00+\x00\x01\x00\x00T_\x00$\xcf;\r\x02em\xa5\x986B/^\x19\x8es\xfc5\xe6\xa8\x9b\xc0\x83\x8d\xea\xacV^q\xa1\x98\x04\xfc\x12P\xe4\xce\rsparrowwallet\x03com\x00\x00.\x00\x01\x00\x00T_\x00W\x00+\r\x02\x00\x01Q\x80h\x95a\x02h\x8c\x16\x1aPA\x03com\x00\xf4\xc4\nX5#\xa7\xd4%P_2\x8a\xfe\x10\xe8\x16\xed\xe3\xf01\xd1Wr\xd87i\xec\x84\x90\xd0\x82\x16r\xe4\xee\xfbu\xfb\x0b\xe4\xff\xe8g\x15\xfb\xec)l\x109\x03h\xb3\x12\x08<kYu\xeb\xf7\xfc\xe6\rsparrowwallet\x03com\x00\x00.\x00\x01\x00\x00\x0e\x0f\x00e\x000\r\x02\x00\x00\x0e\x10h\x91\xef\xe0h~)`=\xc4\rsparrowwallet\x03com\x00+\x96\xadL\xdc\x86\x19\xf8\x9dt1ss\xff\x0b@\xb9\xde12\xcf\x95~\xe5|e< M\x1d6\x11\xd6&Mk\xae\xfb\x1cE\xc1\xfe-I\x9c\xc7u\x87\x18?I\x00\xa1\xf0Q+\x04x\xa6\x0eID\xc0A\rsparrowwallet\x03com\x00\x000\x00\x01\x00\x00\x0e\x0f\x00D\x01\x00\x03\r$\xc86K?\x94+\x00b\xf1\xc68\x80\xb9Y\xb2\xe7\x82\x7f\x1c\xff\xff\x8d^8\xf7\xfd\xe1\xb2-b\x1d\x1cJ\x0c\xd9\xa9\xb0\xc6\xc7\x0b\x1c\x94T<\xcd\xc5P$\x81\xae\xbdn+Del\x9e\xa39\xac\x81\xe8;\rsparrowwallet\x03com\x00\x000\x00\x01\x00\x00\x0e\x0f\x00D\x01\x00\x03\r\x95gl{%\xe7yJ\x8a~K\x19\xedc\x8eG\xac\xa75\xd0,\xe2\xdd\x08\xb2\x88l \xc3\x1a,\xb9\xe7\xcc\x8b\x85\x02:F\xde\xb67\x02\x01\x19\xdc\xaak\xbc\x07G\xe1#@\xfa\x811\x99y\x9d\xe5y\xde\x8a\rsparrowwallet\x03com\x00\x000\x00\x01\x00\x00\x0e\x0f\x00D\x01\x01\x03\r\xb07%!3\x7f\xd5m\x8bb\xe9\x17\xb7\x86k\x7f\xaau=%2.\x12\xb5*>\xb5\xff\x9fL\x9ff"\x7fP\x8f\xe3;\xa19\xf2\xf15O\xe3\xde\xd6\xd3\xdav\xd4\x9b\xe9&\x19\x8d\xc2\x94\x0f,R\x82\xc7\xfe\rsparrowwallet\x03com\x00\x000\x00\x01\x00\x00\x0e\x0f\x00D\x01\x01\x03\r\xdd\xf9\x17t?2\nI\xf6!\x8dpb\x18\xb6\xca\xe5t\xf1\xdbv\x88U^\r_\x04U@]he\x99?\x01G\xfbK3\xba\xa2\x07\xb2\x8d#,\x9epA\x9d\xdc\xaer\x05\x03\x11\t\x8c\xd4\xcf\xaa\x07\x96\x9b\x05craig\x04user\x10_bitcoin-payment\rsparrowwallet\x03com\x00\x00\x10\x00\x01\x00\x00\x0e\x0f\x0032bitcoin:bc1qwthe43xeuasklclq4kvhreluv3hu92rzej42js\x05craig\x04user\x10_bitcoin-payment\rsparrowwallet\x03com\x00\x00.\x00\x01\x00\x00\x0e\x0f\x00e\x00\x10\r\x05\x00\x00\x0e\x10h\x91\xef\xe0h~)`\xbb&\rsparrowwallet\x03com\x00\xe7\xae\x93\xd2;tw7ULMR\xdd\x1e\xc0\xf5\x8cA\x1cjGM\xa4l<$\xd0\xdb\x97\r\x86\xe9\x1b\xf9\x1b^\xab\xeb\x1e\xd5\x91!g\x8e\xf54\xa2Zou\xce\x05\x88\xe6RD9\xc1\x1d \x8f0\x1dF')

        screenshot_sections = {
            "Main Menu Views": [
                ScreenshotConfig(OpeningSplashView, dict(force_partner_logos=True)),
                ScreenshotConfig(OpeningSplashView, dict(force_partner_logos=False), screenshot_name="OpeningSplashView_no_partner_logos"),
                ScreenshotConfig(MainMenuView),
                ScreenshotConfig(MainMenuView, screenshot_name='MainMenuView_SDCardStateChangeToast_removed',  toast_thread=SDCardStateChangeToastManagerThread(action=MicroSD.ACTION__REMOVED, activation_delay=0, duration=0)),
                ScreenshotConfig(MainMenuView, screenshot_name='MainMenuView_SDCardStateChangeToast_inserted', toast_thread=SDCardStateChangeToastManagerThread(action=MicroSD.ACTION__INSERTED, activation_delay=0, duration=0)),
                ScreenshotConfig(MainMenuView, screenshot_name='MainMenuView_RemoveSDCardToast',               toast_thread=RemoveSDCardToastManagerThread(activation_delay=0, duration=0)),
                ScreenshotConfig(RemoveMicroSDWarningView),
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
                ScreenshotConfig(seed_views.SeedExportXpubQRFormatView, dict(seed_num=0, sig_type="ss", script_type="nat")),
                ScreenshotConfig(seed_views.SeedExportXpubWarningView, dict(seed_num=0, sig_type="msig", script_type="nes", xpub_qr_format="urca", custom_derivation="")),
                ScreenshotConfig(seed_views.SeedExportXpubDetailsView, dict(seed_num=0, sig_type="ss", script_type="nat", xpub_qr_format="urca", custom_derivation="")),
                ScreenshotConfig(SeedExportXpubQR_ScreenBrightnessView, dict(seed_num=0, xpub_qr_format="urca", derivation_path="m/84'/0'/0'")),

                ScreenshotConfig(seed_views.SeedWordsWarningView, dict(seed_num=0)),
                ScreenshotConfig(seed_views.SeedWordsView, dict(seed_num=0)),
                ScreenshotConfig(seed_views.SeedWordsView, dict(seed_num=0, page_index=2), screenshot_name="SeedWordsView_2"),
                ScreenshotConfig(seed_views.SeedBIP85SelectNumWordsView, dict(seed_num=0)),
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
                ScreenshotConfig(seed_views.SeedTranscribeSeedQRZoomedInView, dict(seed_num=0, seedqr_format=QRType.SEED__COMPACTSEEDQR, initial_zone_x=1, initial_zone_y=1), screenshot_name="SeedTranscribeSeedQRZoomedInView_12_Compact"),
                ScreenshotConfig(seed_views.SeedTranscribeSeedQRZoomedInView, dict(seed_num=0, seedqr_format=QRType.SEED__SEEDQR, initial_zone_x=2, initial_zone_y=2),        screenshot_name="SeedTranscribeSeedQRZoomedInView_12_Standard"),

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
                ScreenshotConfig(psbt_views.PSBTOverviewView, run_before=load_multisig_psbt_cb),
                ScreenshotConfig(psbt_views.PSBTUnsupportedScriptTypeWarningView),
                ScreenshotConfig(psbt_views.PSBTNoChangeWarningView),
                ScreenshotConfig(psbt_views.PSBTMathView),
                ScreenshotConfig(psbt_views.PSBTDnsNameView, run_before= PSBTaddDNSSECproof),
                ScreenshotConfig(psbt_views.PSBTDnsNameView, run_before= PSBTaddwrongDNSSECproof, screenshot_name= 'PSBTDnsNameView_unverified'),
                ScreenshotConfig(psbt_views.PSBTAddressDetailsView, dict(address_num=0)),

                ScreenshotConfig(psbt_views.PSBTChangeDetailsView, dict(change_address_num=0), screenshot_name="PSBTChangeDetailsView_single_sig_change_verified", run_before=load_single_sig_psbt_cb),
                ScreenshotConfig(psbt_views.PSBTChangeDetailsView, dict(change_address_num=1), screenshot_name="PSBTChangeDetailsView_single_sig_self_transfer_verified", run_before=load_single_sig_psbt_cb),
                ScreenshotConfig(psbt_views.PSBTChangeDetailsView, dict(change_address_num=0), screenshot_name="PSBTChangeDetailsView_multisig_unverified", run_before=load_multisig_psbt_cb),
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
                ScreenshotConfig(settings_views.SettingsSelectionRequiredWarningView, dict(attr_name=SettingsConstants.SETTING__SCRIPT_TYPES)),
            ],
            "Misc Error Views": [
                ScreenshotConfig(NotYetImplementedView),
                ScreenshotConfig(UnhandledExceptionView, dict(error=["IndexError", "line 1, in some_buggy_code.py", "list index out of range"])),
                ScreenshotConfig(CameraConnectionErrorView),
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
                cur_count = screenshot_renderer.render_count

                # Set up and run the target View
                screenshot_config.run_callback_before()
                screenshot_config.View_cls(**screenshot_config.view_kwargs).run()

                if screenshot_renderer.render_count == cur_count:
                    # The View didn't actually render anything
                    raise Exception(f"{screenshot_config.screenshot_name} did not render a screenshot. Verify that its `run_screen()` is reachable by the screenshot generator.")

            except ScreenshotComplete:
                # The target View has run and its Screen has rendered what it needs to
                if toast_thread is not None:
                    # Now run the Toast so it can render on top of the current image buffer
                    controller.activate_toast(toast_thread)
                    while controller.toast_notification_thread.is_alive():
                        # Give the Toast a moment to complete its work
                        time.sleep(0.01)

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

    locale_tuple_list = [locale_tuple for locale_tuple in SettingsConstants.get_detected_languages() if locale_tuple[0] == locale]
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

    for locale, display_name in SettingsConstants.get_detected_languages():
        main_readme += f"* [{display_name}]({locale}/README.md)\n"

    with open(os.path.join(screenshot_root, "README.md"), 'w') as readme_file:
        readme_file.write(main_readme)

    print(f"Screenshots rendered: {screenshot_renderer.render_count}")
