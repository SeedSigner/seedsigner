import hashlib
import os
import time

from PIL import Image
from PIL.ImageOps import autocontrast
from stellar_sdk import Keypair

from lumensigner.controller import Controller
from lumensigner.gui.components import (
    FontAwesomeIconConstants,
    GUIConstants,
    SeedSignerCustomIconConstants,
)
from lumensigner.gui.screens import RET_CODE__BACK_BUTTON, ButtonListScreen
from lumensigner.gui.screens.screen import LoadingScreenThread, QRDisplayScreen
from lumensigner.gui.screens.tools_screens import (
    ToolsCalcFinalWordDoneScreen,
    ToolsCalcFinalWordFinalizePromptScreen,
    ToolsCalcFinalWordScreen,
    ToolsCoinFlipEntryScreen,
    ToolsDiceEntropyEntryScreen,
    ToolsImageEntropyFinalImageScreen,
    ToolsImageEntropyLivePreviewScreen,
    ToolsAddressDetailsScreen,
)
from lumensigner.hardware.camera import Camera
from lumensigner.helpers import mnemonic_generation
from lumensigner.helpers.dev_tools import SEED_SIGNER_DEV_MODE_ENABLED
from lumensigner.models.encode_qr import EncodeQR
from lumensigner.models.qr_type import QRType
from lumensigner.models.seed import Seed
from lumensigner.models.settings_definition import SettingsConstants
from lumensigner.views.seed_views import (
    SeedDiscardView,
    SeedFinalizeView,
    SeedMnemonicEntryView,
    SeedWordsWarningView,
    AddressExporterView,
)
from lumensigner.views.view import View, Destination, BackStackView


class ToolsMenuView(View):
    def run(self):
        IMAGE = (" New seed", FontAwesomeIconConstants.CAMERA)
        DICE = ("New seed", FontAwesomeIconConstants.DICE)
        KEYBOARD = ("Calc 12th/24th word", FontAwesomeIconConstants.KEYBOARD)
        RANDOM = (" Random seed", FontAwesomeIconConstants.LOCK)
        EXPLORER = "Address Explorer"
        if SEED_SIGNER_DEV_MODE_ENABLED:
            button_data = [IMAGE, DICE, KEYBOARD, RANDOM, EXPLORER]
        else:
            button_data = [IMAGE, DICE, KEYBOARD, EXPLORER]
        screen = ButtonListScreen(
            title="Tools", is_button_text_centered=False, button_data=button_data
        )
        selected_menu_num = screen.display()

        if selected_menu_num == RET_CODE__BACK_BUTTON:
            return Destination(BackStackView)

        elif button_data[selected_menu_num] == IMAGE:
            return Destination(ToolsImageEntropyLivePreviewView)

        elif button_data[selected_menu_num] == DICE:
            return Destination(ToolsDiceEntropyMnemonicLengthView)

        elif button_data[selected_menu_num] == KEYBOARD:
            return Destination(ToolsCalcFinalWordNumWordsView)

        elif button_data[selected_menu_num] == RANDOM:
            return Destination(ToolsRandomSeedView)

        elif button_data[selected_menu_num] == EXPLORER:
            return Destination(ToolsAddressExplorerSelectSourceView)


"""****************************************************************************
    Image entropy Views
****************************************************************************"""


class ToolsImageEntropyLivePreviewView(View):
    def run(self):
        self.controller.image_entropy_preview_frames = None
        ret = ToolsImageEntropyLivePreviewScreen().display()

        if ret == RET_CODE__BACK_BUTTON:
            return Destination(BackStackView)

        self.controller.image_entropy_preview_frames = ret
        return Destination(ToolsImageEntropyFinalImageView)


class ToolsImageEntropyFinalImageView(View):
    def run(self):
        if not self.controller.image_entropy_final_image:
            # Take the final full-res image
            camera = Camera.get_instance()
            camera.start_single_frame_mode(resolution=(720, 480))
            time.sleep(0.25)
            self.controller.image_entropy_final_image = camera.capture_frame()
            camera.stop_single_frame_mode()

        # Prep a copy of the image for display. The actual image data is 720x480
        # Present just a center crop and resize it to fit the screen and to keep some of
        #   the data hidden.
        display_version = (
            autocontrast(self.controller.image_entropy_final_image, cutoff=2)
            .crop((120, 0, 600, 480))
            .resize((self.canvas_width, self.canvas_height), Image.BICUBIC)
        )

        ret = ToolsImageEntropyFinalImageScreen(final_image=display_version).display()

        if ret == RET_CODE__BACK_BUTTON:
            # Go back to live preview and reshoot
            self.controller.image_entropy_final_image = None
            return Destination(BackStackView)

        return Destination(ToolsImageEntropyMnemonicLengthView)


class ToolsImageEntropyMnemonicLengthView(View):
    def run(self):
        TWELVE_WORDS = "12 words"
        TWENTYFOUR_WORDS = "24 words"
        button_data = [TWELVE_WORDS, TWENTYFOUR_WORDS]

        selected_menu_num = ButtonListScreen(
            title="Mnemonic Length?",
            button_data=button_data,
        ).display()

        if selected_menu_num == RET_CODE__BACK_BUTTON:
            return Destination(BackStackView)

        if button_data[selected_menu_num] == TWELVE_WORDS:
            mnemonic_length = 12
        else:
            mnemonic_length = 24

        preview_images = self.controller.image_entropy_preview_frames
        seed_entropy_image = self.controller.image_entropy_final_image

        # Build in some hardware-level uniqueness via CPU unique Serial num
        try:
            stream = os.popen("cat /proc/cpuinfo | grep Serial")
            output = stream.read()
            serial_num = output.split(":")[-1].strip().encode("utf-8")
            serial_hash = hashlib.sha256(serial_num)
            hash_bytes = serial_hash.digest()
        except Exception as e:
            print(repr(e))
            hash_bytes = b"0"

        # Build in modest entropy via millis since power on
        millis_hash = hashlib.sha256(hash_bytes + str(time.time()).encode("utf-8"))
        hash_bytes = millis_hash.digest()

        # Build in better entropy by chaining the preview frames
        for frame in preview_images:
            img_hash = hashlib.sha256(hash_bytes + frame.tobytes())
            hash_bytes = img_hash.digest()

        # Finally build in our headline entropy via the new full-res image
        final_hash = hashlib.sha256(hash_bytes + seed_entropy_image.tobytes()).digest()

        if mnemonic_length == 12:
            # 12-word mnemonic only uses the first 128 bits / 16 bytes of entropy
            final_hash = final_hash[:16]

        # Generate the mnemonic
        mnemonic = mnemonic_generation.generate_mnemonic_from_bytes(final_hash)

        # Image should never get saved nor stick around in memory
        seed_entropy_image = None
        preview_images = None
        final_hash = None
        hash_bytes = None
        self.controller.image_entropy_preview_frames = None
        self.controller.image_entropy_final_image = None

        # Add the mnemonic as an in-memory Seed
        seed = Seed(
            mnemonic,
            wordlist_language_code=self.settings.get_value(
                SettingsConstants.SETTING__WORDLIST_LANGUAGE
            ),
        )
        self.controller.storage.set_pending_seed(seed)

        # Cannot return BACK to this View
        return Destination(
            SeedWordsWarningView, view_args={"seed_num": None}, clear_history=True
        )


"""****************************************************************************
    Dice rolls Views
****************************************************************************"""


class ToolsDiceEntropyMnemonicLengthView(View):
    def run(self):
        TWELVE = "12 words (50 rolls)"
        TWENTY_FOUR = "24 words (99 rolls)"

        button_data = [TWELVE, TWENTY_FOUR]
        selected_menu_num = ButtonListScreen(
            title="Mnemonic Length",
            is_bottom_list=True,
            is_button_text_centered=True,
            button_data=button_data,
        ).display()

        if selected_menu_num == RET_CODE__BACK_BUTTON:
            return Destination(BackStackView)

        elif button_data[selected_menu_num] == TWELVE:
            return Destination(
                ToolsDiceEntropyEntryView, view_args=dict(total_rolls=50)
            )

        elif button_data[selected_menu_num] == TWENTY_FOUR:
            return Destination(
                ToolsDiceEntropyEntryView, view_args=dict(total_rolls=99)
            )


class ToolsDiceEntropyEntryView(View):
    def __init__(self, total_rolls: int):
        super().__init__()
        self.total_rolls = total_rolls

    def run(self):
        ret = ToolsDiceEntropyEntryScreen(
            return_after_n_chars=self.total_rolls,
        ).display()

        if ret == RET_CODE__BACK_BUTTON:
            return Destination(BackStackView)

        print(f"Dice rolls: {ret}")
        dice_seed_phrase = mnemonic_generation.generate_mnemonic_from_dice(ret)
        print(f"""Mnemonic: "{dice_seed_phrase}" """)

        # Add the mnemonic as an in-memory Seed
        seed = Seed(
            dice_seed_phrase,
            wordlist_language_code=self.settings.get_value(
                SettingsConstants.SETTING__WORDLIST_LANGUAGE
            ),
        )
        self.controller.storage.set_pending_seed(seed)

        # Cannot return BACK to this View
        return Destination(
            SeedWordsWarningView, view_args={"seed_num": None}, clear_history=True
        )


"""****************************************************************************
    Calc final word Views
****************************************************************************"""


class ToolsCalcFinalWordNumWordsView(View):
    def run(self):
        TWELVE = "12 words"
        TWENTY_FOUR = "24 words"

        button_data = [TWELVE, TWENTY_FOUR]
        selected_menu_num = ButtonListScreen(
            title="Mnemonic Length",
            is_bottom_list=True,
            is_button_text_centered=True,
            button_data=button_data,
        ).display()

        if selected_menu_num == RET_CODE__BACK_BUTTON:
            return Destination(BackStackView)

        elif button_data[selected_menu_num] == TWELVE:
            self.controller.storage.init_pending_mnemonic(12)

            # return Destination(SeedMnemonicEntryView, view_args=dict(is_calc_final_word=True))
            return Destination(
                SeedMnemonicEntryView, view_args=dict(is_calc_final_word=True)
            )

        elif button_data[selected_menu_num] == TWENTY_FOUR:
            self.controller.storage.init_pending_mnemonic(24)

            # return Destination(SeedMnemonicEntryView, view_args=dict(is_calc_final_word=True))
            return Destination(
                SeedMnemonicEntryView, view_args=dict(is_calc_final_word=True)
            )


class ToolsCalcFinalWordFinalizePromptView(View):
    def run(self):
        mnemonic = self.controller.storage.pending_mnemonic
        mnemonic_length = len(mnemonic)
        if mnemonic_length == 12:
            num_entropy_bits = 7
        else:
            num_entropy_bits = 3

        COIN_FLIPS = "Coin flip entropy"
        SELECT_WORD = f"Word selection entropy"
        ZEROS = "Finalize with zeros"

        button_data = [COIN_FLIPS, SELECT_WORD, ZEROS]
        selected_menu_num = ToolsCalcFinalWordFinalizePromptScreen(
            mnemonic_length=mnemonic_length,
            num_entropy_bits=num_entropy_bits,
            button_data=button_data,
        ).display()

        if selected_menu_num == RET_CODE__BACK_BUTTON:
            return Destination(BackStackView)

        elif button_data[selected_menu_num] == COIN_FLIPS:
            return Destination(ToolsCalcFinalWordCoinFlipsView)

        elif button_data[selected_menu_num] == SELECT_WORD:
            # Clear the final word slot, just in case we're returning via BACK button
            self.controller.storage.update_pending_mnemonic(None, mnemonic_length - 1)
            return Destination(
                SeedMnemonicEntryView,
                view_args=dict(
                    is_calc_final_word=True, cur_word_index=mnemonic_length - 1
                ),
            )

        elif button_data[selected_menu_num] == ZEROS:
            # User skipped the option to select a final word to provide last bits of
            # entropy. We'll insert all zeros and piggy-back on the coin flip attr
            wordlist_language_code = self.settings.get_value(
                SettingsConstants.SETTING__WORDLIST_LANGUAGE
            )
            self.controller.storage.update_pending_mnemonic(
                Seed.get_wordlist(wordlist_language_code)[0], mnemonic_length - 1
            )
            return Destination(
                ToolsCalcFinalWordShowFinalWordView,
                view_args=dict(coin_flips="0" * num_entropy_bits),
            )


class ToolsCalcFinalWordCoinFlipsView(View):
    def run(self):
        mnemonic = self.controller.storage.pending_mnemonic
        mnemonic_length = len(mnemonic)

        if mnemonic_length == 12:
            total_flips = 7
        else:
            total_flips = 3

        ret_val = ToolsCoinFlipEntryScreen(
            return_after_n_chars=total_flips,
        ).display()

        if ret_val == RET_CODE__BACK_BUTTON:
            return Destination(BackStackView)

        else:
            print(ret_val)
            binary_string = ret_val + "0" * (11 - total_flips)
            wordlist_index = int(binary_string, 2)
            wordlist = Seed.get_wordlist(
                self.controller.settings.get_value(
                    SettingsConstants.SETTING__WORDLIST_LANGUAGE
                )
            )
            word = wordlist[wordlist_index]
            self.controller.storage.update_pending_mnemonic(word, mnemonic_length - 1)

            return Destination(
                ToolsCalcFinalWordShowFinalWordView, view_args=dict(coin_flips=ret_val)
            )


class ToolsCalcFinalWordShowFinalWordView(View):
    def __init__(self, coin_flips=None):
        super().__init__()
        self.coin_flips = coin_flips

    def run(self):
        # Construct the actual final word. The user's selected_final_word
        # contributes:
        #   * 3 bits to a 24-word seed (plus 8-bit checksum)
        #   * 7 bits to a 12-word seed (plus 4-bit checksum)
        from lumensigner.helpers import mnemonic_generation

        mnemonic = self.controller.storage.pending_mnemonic
        mnemonic_length = len(mnemonic)
        wordlist_language_code = self.settings.get_value(
            SettingsConstants.SETTING__WORDLIST_LANGUAGE
        )
        wordlist = Seed.get_wordlist(wordlist_language_code)

        final_mnemonic = mnemonic_generation.calculate_checksum(
            mnemonic=self.controller.storage.pending_mnemonic,
            wordlist_language_code=wordlist_language_code,
        )
        self.controller.storage.update_pending_mnemonic(
            final_mnemonic[-1], mnemonic_length - 1
        )

        # Prep the user's selected word (if there was one) and the actual final word for
        # the display.
        if self.coin_flips:
            selected_final_word = None
            selected_final_bits = self.coin_flips
        else:
            # Convert the user's final word selection into its binary index equivalent
            selected_final_word = mnemonic[-1]
            selected_final_bits = format(wordlist.index(selected_final_word), "011b")

        # And grab the actual final word's checksum bits
        actual_final_word = self.controller.storage.pending_mnemonic[-1]
        if mnemonic_length == 12:
            checksum_bits = format(wordlist.index(actual_final_word), "011b")[-4:]
        else:
            checksum_bits = format(wordlist.index(actual_final_word), "011b")[-8:]

        NEXT = "Next"
        button_data = [NEXT]
        selected_menu_num = ToolsCalcFinalWordScreen(
            title="Final Word Calc",
            button_data=button_data,
            selected_final_word=selected_final_word,
            selected_final_bits=selected_final_bits,
            checksum_bits=checksum_bits,
            actual_final_word=actual_final_word,
        ).display()

        if selected_menu_num == RET_CODE__BACK_BUTTON:
            return Destination(BackStackView)

        elif button_data[selected_menu_num] == NEXT:
            return Destination(ToolsCalcFinalWordDoneView)


class ToolsCalcFinalWordDoneView(View):
    def run(self):
        mnemonic = self.controller.storage.pending_mnemonic
        mnemonic_word_length = len(mnemonic)
        final_word = mnemonic[-1]

        LOAD = "Load seed"
        DISCARD = ("Discard", None, None, "red")
        button_data = [LOAD, DISCARD]

        selected_menu_num = ToolsCalcFinalWordDoneScreen(
            final_word=final_word,
            mnemonic_word_length=mnemonic_word_length,
            fingerprint=self.controller.storage.get_pending_mnemonic_fingerprint(),
            button_data=button_data,
        ).display()

        if selected_menu_num == RET_CODE__BACK_BUTTON:
            return Destination(BackStackView)

        self.controller.storage.convert_pending_mnemonic_to_pending_seed()

        if button_data[selected_menu_num] == LOAD:
            return Destination(SeedFinalizeView)

        elif button_data[selected_menu_num] == DISCARD:
            return Destination(SeedDiscardView)


"""****************************************************************************
    Random Seed Views
****************************************************************************"""


class ToolsRandomSeedView(View):
    def run(self):
        TWELVE = "12 words"
        TWENTY_FOUR = "24 words"

        button_data = [TWELVE, TWENTY_FOUR]
        selected_menu_num = ButtonListScreen(
            title="Mnemonic Length",
            is_bottom_list=True,
            is_button_text_centered=True,
            button_data=button_data,
        ).display()

        if selected_menu_num == RET_CODE__BACK_BUTTON:
            return Destination(BackStackView)

        elif button_data[selected_menu_num] == TWELVE:
            return Destination(
                ToolsRandomSeedCalcMnemonicView, view_args=dict(word_count=12)
            )

        elif button_data[selected_menu_num] == TWENTY_FOUR:
            return Destination(
                ToolsRandomSeedCalcMnemonicView, view_args=dict(word_count=24)
            )


class ToolsRandomSeedCalcMnemonicView(View):
    def __init__(self, word_count: int):
        super().__init__()
        if word_count not in [12, 24]:
            raise ValueError("word_count must be 12 or 24")
        self.word_count = word_count

    def run(self):
        random_bytes = os.urandom(16 if self.word_count == 12 else 32)
        # Generate the mnemonic
        mnemonic = mnemonic_generation.generate_mnemonic_from_bytes(random_bytes)
        # Add the mnemonic as an in-memory Seed
        seed = Seed(
            mnemonic,
            wordlist_language_code=self.settings.get_value(
                SettingsConstants.SETTING__WORDLIST_LANGUAGE
            ),
        )
        self.controller.storage.set_pending_seed(seed)

        # Cannot return BACK to this View
        return Destination(
            SeedWordsWarningView, view_args={"seed_num": None}, clear_history=True
        )


"""****************************************************************************
    Address Explorer Views
****************************************************************************"""


class ToolsAddressExplorerSelectSourceView(View):
    def run(self):
        SCAN_SEED = ("Scan a seed", FontAwesomeIconConstants.QRCODE)
        TYPE_12WORD = ("Enter 12-word seed", FontAwesomeIconConstants.KEYBOARD)
        TYPE_24WORD = ("Enter 24-word seed", FontAwesomeIconConstants.KEYBOARD)
        button_data = []

        seeds = self.controller.storage.seeds
        for seed in seeds:
            button_str = seed.get_fingerprint()
            button_data.append(
                (button_str, SeedSignerCustomIconConstants.FINGERPRINT, "blue")
            )

        button_data.append(SCAN_SEED)
        button_data.append(TYPE_12WORD)
        button_data.append(TYPE_24WORD)

        selected_menu_num = ButtonListScreen(
            title="Address Explorer",
            button_data=button_data,
            is_button_text_centered=False,
            is_bottom_list=True,
        ).display()

        self.controller.resume_main_flow = Controller.FLOW__ADDRESS_EXPLORER

        if selected_menu_num == RET_CODE__BACK_BUTTON:
            return Destination(BackStackView)

        if len(seeds) > 0 and selected_menu_num < len(seeds):
            # User selected one of the n seeds
            return Destination(
                AddressExporterView, view_args=dict(seed_num=selected_menu_num)
            )

        elif button_data[selected_menu_num] in [SCAN_SEED]:
            from lumensigner.views.scan_views import ScanView

            return Destination(ScanView)

        elif button_data[selected_menu_num] in [TYPE_12WORD, TYPE_24WORD]:
            from lumensigner.views.seed_views import SeedMnemonicEntryView

            if button_data[selected_menu_num] == TYPE_12WORD:
                self.controller.storage.init_pending_mnemonic(num_words=12)
            else:
                self.controller.storage.init_pending_mnemonic(num_words=24)
            return Destination(SeedMnemonicEntryView)


class ToolsAddressExplorerAddressListView(View):
    def __init__(
        self,
        start_index: int = 0,
        selected_button_index: int = 0,
        initial_scroll: int = 0,
    ):
        super().__init__()
        self.start_index = start_index
        self.selected_button_index = selected_button_index
        self.initial_scroll = initial_scroll

    def run(self):
        self.loading_screen = None
        try:
            addresses = []
            button_data = []
            data = self.controller.address_explorer_data
            addrs_per_screen = 10
            addr_storage_key = "addrs"

            if (
                addr_storage_key in data
                and len(data[addr_storage_key]) >= self.start_index + addrs_per_screen
            ):
                # We already calculated this range addresses; just retrieve them
                addresses = data[addr_storage_key][
                    self.start_index : self.start_index + addrs_per_screen
                ]

            else:
                self.loading_screen = LoadingScreenThread(text="Calculating addrs...")
                self.loading_screen.start()

                if addr_storage_key not in data:
                    data[addr_storage_key] = []
                # TODO: data["seed"] is not defined?
                mnemonic_str = data["seed"].mnemonic_str
                passphrase = data["seed"].passphrase

                for i in range(self.start_index, self.start_index + addrs_per_screen):
                    address = Keypair.from_mnemonic_phrase(
                        mnemonic_str, passphrase=passphrase, index=i
                    ).public_key
                    addresses.append(address)
                    data[addr_storage_key].append(address)

            for i, address in enumerate(addresses):
                cur_index = i + self.start_index
                if cur_index < 10:
                    end_digits = -7
                elif cur_index < 100:
                    end_digits = -6
                else:
                    end_digits = -5
                button_data.append(
                    f"{cur_index}:{address[:7]}...{address[end_digits:]}"
                )

            button_data.append(
                (
                    "Next {}".format(addrs_per_screen),
                    None,
                    None,
                    None,
                    SeedSignerCustomIconConstants.SMALL_CHEVRON_RIGHT,
                )
            )

            screen = ButtonListScreen(
                title="Accounts",
                button_data=button_data,
                button_font_name=GUIConstants.FIXED_WIDTH_EMPHASIS_FONT_NAME,
                button_font_size=GUIConstants.BUTTON_FONT_SIZE + 4,
                is_button_text_centered=False,
                is_bottom_list=True,
                selected_button=self.selected_button_index,
                scroll_y_initial_offset=self.initial_scroll,
            )
        finally:
            # Everything is set. Stop the loading screen
            if self.loading_screen:
                self.loading_screen.stop()

        selected_menu_num = screen.display()

        if selected_menu_num == RET_CODE__BACK_BUTTON:
            return Destination(BackStackView)

        if selected_menu_num == len(addresses):
            # User clicked NEXT
            return Destination(
                ToolsAddressExplorerAddressListView,
                view_args=dict(
                    start_index=self.start_index + addrs_per_screen,
                ),
            )

        # Preserve the list's current scroll so we can return to the same spot
        initial_scroll = screen.buttons[0].scroll_y

        index = selected_menu_num + self.start_index
        return Destination(
            ToolsAddressExplorerAddressDetailsView,
            view_args=dict(
                index=index,
                address=addresses[selected_menu_num],
                start_index=self.start_index,
                parent_initial_scroll=initial_scroll,
            ),
            skip_current_view=True,
        )


class ToolsAddressExplorerAddressDetailsView(View):
    def __init__(
        self,
        index: int,
        address: str,
        start_index: int,
        parent_initial_scroll: int = 0,
    ):
        super().__init__()
        self.index = index
        self.address = address
        self.start_index = start_index
        self.parent_initial_scroll = parent_initial_scroll

    def run(self):
        ADDRESS_QRCODE = "Address QRCode"
        CONNECT_QRCODE = "Connect QRCode"
        button_data = [ADDRESS_QRCODE, CONNECT_QRCODE]
        selected_menu_num = ToolsAddressDetailsScreen(
            address=self.address,
            derivation_index_id=self.index,
            button_data=button_data,
        ).display()

        print("selected_menu_num: ", selected_menu_num)

        if selected_menu_num == RET_CODE__BACK_BUTTON:
            # Exiting/Cancelling the QR display screen always returns to the list
            return Destination(
                ToolsAddressExplorerAddressListView,
                view_args=dict(
                    start_index=self.start_index,
                    selected_button_index=self.index - self.start_index,
                    initial_scroll=self.parent_initial_scroll,
                ),
                skip_current_view=True,
            )

        elif selected_menu_num in (0, 1):
            return Destination(
                ToolsAddressExplorerAddressQRCodeView,
                view_args=dict(
                    index=self.index,
                    address=self.address,
                    start_index=self.start_index,
                    parent_initial_scroll=self.parent_initial_scroll,
                    is_connect=selected_menu_num == 1,
                ),
            )


class ToolsAddressExplorerAddressQRCodeView(View):
    def __init__(
        self,
        index: int,
        address: str,
        start_index: int,
        parent_initial_scroll: int = 0,
        is_connect: bool = False,
    ):
        super().__init__()
        self.index = index
        self.address = address
        self.start_index = start_index
        self.parent_initial_scroll = parent_initial_scroll
        self.is_connect = is_connect

    def run(self):
        if self.is_connect:
            qr_encoder = EncodeQR(
                qr_type=QRType.STELLAR_ADDRESS,
                stellar_address=self.address,
                derivation=f"m/44'/148'/{self.index}'",
            )
        else:
            qr_encoder = EncodeQR(
                qr_type=QRType.STELLAR_ADDRESS_NO_PREFIX, stellar_address=self.address
            )

        QRDisplayScreen(
            qr_encoder=qr_encoder,
        ).display()

        return Destination(BackStackView)
