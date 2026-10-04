"""
SeedSigner Views for Legacy Encryption

Flow:
  MainMenu → LegacyMainMenuView
    ├── Encrypt: LegacyEncryptInputMethodView
    │    ├── Scan Seed QR → LegacyEncryptScanSeedView
    │    │                → EnterBenefactorKey → EnterBeneficiaryKey
    │    │                → ConfirmEncrypt → EncryptingView → ShowEncryptedQRView
    │    └── Enter Manually → LegacyManualSeedWordCountView
    │                       → LegacyEnterSeedWordView (×12 or ×24)
    │                       → EnterBenefactorKey → EnterBeneficiaryKey
    │                       → ConfirmEncrypt → EncryptingView → ShowEncryptedQRView
    └── Decrypt: ScanEncryptedQR → EnterBenefactorKey → EnterBeneficiaryKey
                 → DecryptingView → ShowDecryptedSeedView → ShowSeedWordsView
"""

import time
import signal as _signal
import threading

from seedsigner.views.view import View, Destination, BackStackView
from seedsigner.gui.screens.screen import (
    ButtonListScreen,
    ButtonOption,
    QRDisplayScreen,
    WarningScreen,
    LargeIconStatusScreen,
    LoadingScreenThread,
    RET_CODE__BACK_BUTTON,
)
from seedsigner.gui.screens.scan_screens import ScanScreen
from seedsigner.models.decode_qr import DecodeQR, DecodeQRStatus
from seedsigner.models.settings import SettingsConstants
from seedsigner.gui.components import FontAwesomeIconConstants
from seedsigner.helpers.legacy_encryption import (
    encrypt_seed_phrase,
    decrypt_seed_phrase,
    validate_seed_phrase,
    encrypted_to_qr_data,
    qr_data_to_encrypted,
)
from seedsigner.models.encode_qr import GenericStaticQrEncoder

import logging
_log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# SIGALRM pyzbar timeout — prevents the main thread from hanging if libzbar
# locks up under memory pressure on the Pi Zero.  SIGALRM is Linux-only but
# the code degrades gracefully on other platforms (just no timeout).
# ---------------------------------------------------------------------------
_HAS_SIGALRM = hasattr(_signal, 'SIGALRM')
_DECODE_TIMEOUT = 2  # seconds


def _sync_loading_frame(text: str) -> None:
    """Push one loading frame to the display synchronously.

    LoadingScreenThread runs in a daemon thread, so PBKDF2 (a CPU-bound C
    extension) can starve it before it renders a single frame.  Calling this
    first guarantees the user sees *something* on screen before the 30-second
    wait begins.
    """
    try:
        from PIL import Image, ImageDraw
        from seedsigner.gui.renderer import Renderer
        from seedsigner.gui.components import GUIConstants, Fonts
        r = Renderer.get_instance()
        img = Image.new("RGBA", (r.canvas_width, r.canvas_height), "black")
        draw = ImageDraw.Draw(img)
        font = Fonts.get_font(GUIConstants.get_body_font_name(), GUIConstants.get_body_font_size())
        draw.text(
            (r.canvas_width // 2, r.canvas_height // 2),
            text,
            fill="white",
            font=font,
            anchor="mm",
        )
        with r.lock:
            r.show_image(img, show_direct=True)
    except Exception:
        pass  # Never block the encrypt/decrypt flow


def _sigalrm_call(seconds, fn):
    """Call fn() and raise TimeoutError if it takes more than `seconds`."""
    if not _HAS_SIGALRM:
        return fn()

    def _handler(signum, frame):
        raise TimeoutError("pyzbar decode timeout")

    old = _signal.signal(_signal.SIGALRM, _handler)
    _signal.alarm(seconds)
    try:
        return fn()
    finally:
        _signal.alarm(0)
        _signal.signal(_signal.SIGALRM, old)


class _RawQRDecoder(DecodeQR):
    """
    Accepts any QR as raw text — used for scanning the Legacy encrypted payload.

    DecodeQR classifies our base64 blob as INVALID so we bypass its type-detection
    and call pyzbar directly.

    Pi Zero freeze fix — run pyzbar in a daemon thread:
      SIGALRM cannot interrupt a CPU-bound C extension (libzbar) because Python
      only processes signals between bytecodes, and libzbar never returns to Python
      while it is stuck.  The daemon-thread approach keeps the main thread free at
      all times: we launch a decode thread and return FALSE immediately; on the next
      frame we check whether the thread finished.  If libzbar hangs forever the
      daemon thread hangs but the UI stays alive and the user can press back.

    One thread is allowed at a time — if a thread is still running when the next
    eligible frame arrives we skip that frame rather than pile up threads.
    """

    def __init__(self):
        super().__init__(wordlist_language_code="en")
        self._raw_text = None
        self._frame_count = 0
        self._worker = None          # active daemon decode thread
        self._worker_result = None   # written by thread, read by main thread

    def add_image(self, image):
        self._frame_count += 1

        # Check whether the previous worker finished
        if self._worker is not None:
            if not self._worker.is_alive():
                result = self._worker_result
                self._worker = None
                self._worker_result = None
                if result is not None:
                    self._raw_text = result
                    self.complete = True
                    return DecodeQRStatus.COMPLETE
                # Thread finished but found nothing — fall through to maybe try again
            else:
                # Still running — don't block, skip this frame
                return DecodeQRStatus.FALSE

        # Rate-limit: only launch a new decode every 3rd frame
        if self._frame_count % 3 != 0:
            return DecodeQRStatus.FALSE

        if image is None:
            return DecodeQRStatus.FALSE

        # Downsample 2x + green channel only: 12x less data than 480×480 RGB
        small = image[::2, ::2, 1].copy()

        def _decode():
            try:
                data = DecodeQR.extract_qr_data(small, is_binary=True)
                if data is not None:
                    try:
                        self._worker_result = data.decode("utf-8").strip()
                    except Exception:
                        self._worker_result = data.decode("latin-1").strip()
            except Exception:
                pass

        self._worker = threading.Thread(target=_decode, daemon=True)
        self._worker.start()
        return DecodeQRStatus.FALSE

    def get_percent_complete(self, weight_mixed_frames: bool = False) -> int:
        return 100 if self.complete else 0

    def get_raw_text(self):
        return self._raw_text


class _TimeoutDecodeQR(DecodeQR):
    """DecodeQR with SIGALRM watchdog and frame-rate limiting.

    Skips 2 of every 3 frames and downsamples 2x before passing to pyzbar,
    keeping ZBar calls to ~1 fps and reducing pixels 4x — same mitigations as
    _RawQRDecoder.  Without this, every frame at 6 fps goes to ZBar, which
    blocks the main thread long enough to freeze the UI on Pi Zero.
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._frame_count = 0

    def add_image(self, image):
        self._frame_count += 1
        if self._frame_count % 3 != 0:
            return DecodeQRStatus.FALSE

        if image is not None:
            image = image[::2, ::2].copy()

        try:
            return _sigalrm_call(
                _DECODE_TIMEOUT,
                lambda: DecodeQR.add_image(self, image),
            )
        except TimeoutError:
            _log.warning("_TimeoutDecodeQR: pyzbar timeout, skipping frame")
            return DecodeQRStatus.FALSE
        except Exception:
            return DecodeQRStatus.FALSE


def _make_key_entry_screen(label: str):
    """
    Returns a SeedAddPassphraseScreen subclass with a custom title.
    Returns the class (not an instance) so run_screen() instantiates it.
    """
    from dataclasses import dataclass
    from seedsigner.gui.screens.seed_screens import SeedAddPassphraseScreen
    from seedsigner.gui.components import TopNav, GUIConstants

    @dataclass
    class KeyEntryScreen(SeedAddPassphraseScreen):
        def __post_init__(self):
            super().__post_init__()
            old = self.top_nav
            self.top_nav = TopNav(
                text=label,
                width=self.canvas_width,
                height=GUIConstants.TOP_NAV_HEIGHT,
                show_back_button=old.show_back_button,
                show_power_button=old.show_power_button,
            )
            idx = self.components.index(old)
            self.components[idx] = self.top_nav

    return KeyEntryScreen


# ===================================================================
# Main menu
# ===================================================================

class LegacyMainMenuView(View):
    ENCRYPT = ButtonOption("Encrypt Seed Phrase", FontAwesomeIconConstants.LOCK)
    DECRYPT = ButtonOption("Decrypt Seed Phrase", FontAwesomeIconConstants.UNLOCK)

    def run(self) -> Destination:
        button_data = [self.ENCRYPT, self.DECRYPT]

        selected = self.run_screen(
            ButtonListScreen,
            title="Legacy Encryption",
            is_button_text_centered=False,
            button_data=button_data,
        )

        if selected == RET_CODE__BACK_BUTTON:
            return Destination(BackStackView)

        if button_data[selected] == self.ENCRYPT:
            return Destination(LegacyEncryptInputMethodView)

        if button_data[selected] == self.DECRYPT:
            return Destination(LegacyDecryptScanQRView)


# ===================================================================
# ENCRYPT input method selection
# ===================================================================

class LegacyEncryptInputMethodView(View):
    SCAN_QR = ButtonOption("Scan Seed QR")
    ENTER_MANUALLY = ButtonOption("Enter Manually")

    def run(self) -> Destination:
        button_data = [self.SCAN_QR, self.ENTER_MANUALLY]

        selected = self.run_screen(
            ButtonListScreen,
            title="Encrypt Seed",
            is_button_text_centered=False,
            button_data=button_data,
        )

        if selected == RET_CODE__BACK_BUTTON:
            return Destination(BackStackView)

        if button_data[selected] == self.SCAN_QR:
            return Destination(LegacyEncryptScanSeedView)

        return Destination(LegacyManualSeedWordCountView)


class LegacyManualSeedWordCountView(View):
    TWELVE = ButtonOption("12 words")
    TWENTY_FOUR = ButtonOption("24 words")

    def run(self) -> Destination:
        button_data = [self.TWELVE, self.TWENTY_FOUR]

        selected = self.run_screen(
            ButtonListScreen,
            title="Seed Length",
            is_button_text_centered=True,
            button_data=button_data,
        )

        if selected == RET_CODE__BACK_BUTTON:
            return Destination(BackStackView)

        num_words = 12 if button_data[selected] == self.TWELVE else 24
        self.controller.storage.init_pending_mnemonic(num_words=num_words)
        return Destination(
            LegacyEnterSeedWordView,
            view_args={"cur_word_index": 0, "num_words": num_words},
        )


class LegacyEnterSeedWordView(View):
    OK = ButtonOption("OK")

    def __init__(self, cur_word_index: int = 0, num_words: int = 12):
        super().__init__()
        self.cur_word_index = cur_word_index
        self.num_words = num_words
        self.cur_word = self.controller.storage.get_pending_mnemonic_word(cur_word_index)

    def run(self) -> Destination:
        from seedsigner.gui.screens import seed_screens
        from seedsigner.models.seed import Seed

        wordlist_lang = self.settings.get_value(SettingsConstants.SETTING__WORDLIST_LANGUAGE)
        wordlist = Seed.get_wordlist(wordlist_language_code=wordlist_lang)

        ret = self.run_screen(
            seed_screens.SeedMnemonicEntryScreen,
            title=f"Word {self.cur_word_index + 1} of {self.num_words}",
            initial_letters=list(self.cur_word) if self.cur_word else ["a"],
            wordlist=wordlist,
        )

        if ret == RET_CODE__BACK_BUTTON:
            if self.cur_word_index == 0:
                self.controller.storage.discard_pending_mnemonic()
            return Destination(BackStackView)

        self.controller.storage.update_pending_mnemonic(ret, self.cur_word_index)

        if self.cur_word_index < self.num_words - 1:
            return Destination(
                LegacyEnterSeedWordView,
                view_args={"cur_word_index": self.cur_word_index + 1, "num_words": self.num_words},
            )

        # All words entered — collect, validate, and discard from storage
        words = [
            self.controller.storage.get_pending_mnemonic_word(i)
            for i in range(self.num_words)
        ]
        seed_phrase = " ".join(words)
        self.controller.storage.discard_pending_mnemonic()

        if not validate_seed_phrase(seed_phrase):
            self.run_screen(
                WarningScreen,
                title="Invalid Seed",
                status_headline="Bad Checksum",
                text="The last word doesn't match the checksum. Check all words carefully and try again.",
                button_data=[self.OK],
            )
            return Destination(LegacyManualSeedWordCountView)

        return Destination(
            LegacyEnterBenefactorKeyView,
            view_args={"seed_phrase": seed_phrase, "mode": "encrypt"},
        )


# ===================================================================
# ENCRYPT flow
# ===================================================================

class LegacyEncryptScanSeedView(View):
    OK = ButtonOption("OK")

    def run(self) -> Destination:
        _log.info("LegacyEncryptScanSeedView: starting seed QR scan")
        import gc; gc.collect()
        wordlist_lang = self.settings.get_value(SettingsConstants.SETTING__WORDLIST_LANGUAGE)
        decoder = _TimeoutDecodeQR(wordlist_language_code=wordlist_lang)

        self.run_screen(
            ScanScreen,
            instructions_text="Scan your SeedQR",
            decoder=decoder,
        )

        if not decoder.is_complete:
            return Destination(BackStackView)

        if not decoder.is_seed:
            self.run_screen(
                WarningScreen,
                title="Wrong QR Type",
                status_headline="Not a SeedQR",
                text="Scan the QR that represents your seed phrase — not an encrypted Legacy QR.",
                button_data=[self.OK],
            )
            return Destination(BackStackView)

        seed_phrase = " ".join(decoder.get_seed_phrase())

        if not validate_seed_phrase(seed_phrase):
            self.run_screen(
                WarningScreen,
                title="Invalid Seed",
                status_headline="Error",
                text="The scanned QR does not contain a valid 12 or 24-word BIP-39 seed phrase.",
                button_data=[self.OK],
            )
            return Destination(BackStackView)

        return Destination(
            LegacyEnterBenefactorKeyView,
            view_args={"seed_phrase": seed_phrase, "mode": "encrypt"},
        )


class LegacyEnterBenefactorKeyView(View):
    def __init__(self, seed_phrase: str = "", mode: str = "encrypt",
                 encrypted_data: str = ""):
        super().__init__()
        self.seed_phrase = seed_phrase
        self.mode = mode
        self.encrypted_data = encrypted_data

    def run(self) -> Destination:
        ret = self.run_screen(_make_key_entry_screen("Benefactor Key"))

        if ret == RET_CODE__BACK_BUTTON or (isinstance(ret, dict) and ret.get("is_back_button")):
            return Destination(BackStackView)

        key = ret["passphrase"] if isinstance(ret, dict) else ret

        return Destination(
            LegacyEnterBeneficiaryKeyView,
            view_args={
                "seed_phrase": self.seed_phrase,
                "mode": self.mode,
                "encrypted_data": self.encrypted_data,
                "benefactor_key": key,
            },
        )


class LegacyEnterBeneficiaryKeyView(View):
    def __init__(self, seed_phrase: str = "", mode: str = "encrypt",
                 encrypted_data: str = "", benefactor_key: str = ""):
        super().__init__()
        self.seed_phrase = seed_phrase
        self.mode = mode
        self.encrypted_data = encrypted_data
        self.benefactor_key = benefactor_key

    def run(self) -> Destination:
        ret = self.run_screen(_make_key_entry_screen("Beneficiary Key"))

        if ret == RET_CODE__BACK_BUTTON or (isinstance(ret, dict) and ret.get("is_back_button")):
            return Destination(BackStackView)

        key = ret["passphrase"] if isinstance(ret, dict) else ret

        if self.mode == "encrypt":
            return Destination(
                LegacyConfirmEncryptView,
                view_args={
                    "seed_phrase": self.seed_phrase,
                    "benefactor_key": self.benefactor_key,
                    "beneficiary_key": key,
                },
            )
        else:
            return Destination(
                LegacyDecryptingView,
                view_args={
                    "encrypted_data": self.encrypted_data,
                    "benefactor_key": self.benefactor_key,
                    "beneficiary_key": key,
                },
            )


class LegacyConfirmEncryptView(View):
    CANCEL = ButtonOption("Cancel")

    def __init__(self, seed_phrase: str = "", benefactor_key: str = "",
                 beneficiary_key: str = ""):
        super().__init__()
        self.seed_phrase = seed_phrase
        self.benefactor_key = benefactor_key
        self.beneficiary_key = beneficiary_key

    def run(self) -> Destination:
        word_count = len(self.seed_phrase.split())
        confirm = ButtonOption(f"Encrypt {word_count}-word seed")
        button_data = [confirm, self.CANCEL]

        selected = self.run_screen(
            ButtonListScreen,
            title="Confirm Encrypt",
            is_button_text_centered=True,
            button_data=button_data,
        )

        if selected == RET_CODE__BACK_BUTTON or button_data[selected] == self.CANCEL:
            return Destination(BackStackView)

        return Destination(
            LegacyEncryptingView,
            view_args={
                "seed_phrase": self.seed_phrase,
                "benefactor_key": self.benefactor_key,
                "beneficiary_key": self.beneficiary_key,
            },
        )


class LegacyEncryptingView(View):
    OK = ButtonOption("OK")

    def __init__(self, seed_phrase: str = "", benefactor_key: str = "",
                 beneficiary_key: str = ""):
        super().__init__()
        self.seed_phrase = seed_phrase
        self.benefactor_key = benefactor_key
        self.beneficiary_key = beneficiary_key

    def run(self) -> Destination:
        _log.info("LegacyEncryptingView: begin encrypt")
        from seedsigner.hardware.camera import Camera
        Camera.get_instance().stop_video_stream_mode()

        _sync_loading_frame("Encrypting...  (15-30 sec)")
        loading = LoadingScreenThread(text="Encrypting...  (15-30 sec)")
        loading.start()

        error = None
        try:
            _log.info("LegacyEncryptingView: PBKDF2 start")
            encrypted = encrypt_seed_phrase(
                self.seed_phrase,
                self.benefactor_key,
                self.beneficiary_key,
            )
            _log.info("LegacyEncryptingView: PBKDF2 done")
        except Exception as e:
            error = e
        finally:
            loading.stop()
            _log.info("LegacyEncryptingView: loading screen stopped")

        if error is not None:
            self.run_screen(
                WarningScreen,
                title="Encryption Failed",
                status_headline="Error",
                text=str(error),
                button_data=[self.OK],
            )
            return Destination(BackStackView)

        import gc
        gc.collect()

        return Destination(
            LegacyShowEncryptedQRView,
            view_args={"encrypted": encrypted},
        )


class LegacyShowEncryptedQRView(View):
    READY = ButtonOption("Show QR Code")
    SAVED = ButtonOption("I've saved it")

    def __init__(self, encrypted: str = ""):
        super().__init__()
        self.encrypted = encrypted

    def run(self) -> Destination:
        _log.info("LegacyShowEncryptedQRView: run start")
        qr_data = encrypted_to_qr_data(self.encrypted)
        qr_encoder = GenericStaticQrEncoder(data=qr_data)
        _log.info("LegacyShowEncryptedQRView: QR encoder created")

        # Warn before showing QR so user has camera ready
        _log.info("LegacyShowEncryptedQRView: showing Get Camera Ready screen")
        self.run_screen(
            LargeIconStatusScreen,
            title="Get Camera Ready",
            status_headline="Next screen: QR code",
            text="Get ready to photograph the encrypted QR. You cannot recover your seed without it and BOTH keys.",
            button_data=[self.READY],
        )
        _log.info("LegacyShowEncryptedQRView: Get Camera Ready dismissed")

        # Loop: back from confirmation returns to QR so they can re-photograph
        while True:
            _log.info("LegacyShowEncryptedQRView: showing QR display screen")
            self.run_screen(QRDisplayScreen, qr_encoder=qr_encoder)
            _log.info("LegacyShowEncryptedQRView: QR dismissed, showing saved confirmation")
            ret = self.run_screen(
                LargeIconStatusScreen,
                title="Saved?",
                status_headline="Got the photo?",
                text="If you need another look, press back to return to the QR.",
                button_data=[self.SAVED],
            )
            if ret != RET_CODE__BACK_BUTTON:
                break

        _log.info("LegacyShowEncryptedQRView: done")
        return Destination(LegacyMainMenuView, clear_history=True)


# ===================================================================
# DECRYPT flow
# ===================================================================

class LegacyDecryptScanQRView(View):
    OK = ButtonOption("OK")

    def run(self) -> Destination:
        _log.info("LegacyDecryptScanQRView: starting encrypted QR scan")
        import gc; gc.collect()
        decoder = _RawQRDecoder()

        # Use default resolution (480×480) and framerate (6) — the same settings
        # as every other ScanScreen in SeedSigner. PiVideoStream.stop() is a
        # busy-wait spin that can stall indefinitely on Pi Zero at non-standard
        # resolutions. _RawQRDecoder's grayscale conversion + 3x frame skipping
        # keep ZBar fast enough without needing to change the camera settings.
        try:
            self.run_screen(
                ScanScreen,
                instructions_text="Scan Legacy encrypted QR",
                decoder=decoder,
            )
        except Exception:
            # start_video_stream_mode() raises RuntimeError if the camera
            # produces no frames within 5 s (MMAL stuck on second open).
            self.run_screen(
                WarningScreen,
                title="Camera Error",
                status_headline="Please Restart",
                text="The camera failed to start. Power the device off and back on to reset it.",
                button_data=[self.OK],
            )
            return Destination(LegacyMainMenuView, clear_history=True)

        if not decoder.complete:
            return Destination(BackStackView)

        raw_text = decoder.get_raw_text()

        if not raw_text:
            self.run_screen(
                WarningScreen,
                title="Scan Failed",
                status_headline="Try Again",
                text="Could not read the QR code. Make sure it is well-lit and fills the frame.",
                button_data=[self.OK],
            )
            return Destination(BackStackView)

        encrypted_data = qr_data_to_encrypted(raw_text)

        if not encrypted_data:
            self.run_screen(
                WarningScreen,
                title="Wrong QR",
                status_headline="Not a Legacy QR",
                text="This doesn't look like a Legacy Encryption QR. Scan the encrypted QR, not the original SeedQR.",
                button_data=[self.OK],
            )
            return Destination(BackStackView)

        return Destination(
            LegacyEnterBenefactorKeyView,
            view_args={
                "seed_phrase": "",
                "mode": "decrypt",
                "encrypted_data": encrypted_data,
            },
        )


class LegacyDecryptingView(View):
    OK = ButtonOption("OK")

    def __init__(self, encrypted_data: str = "", benefactor_key: str = "",
                 beneficiary_key: str = ""):
        super().__init__()
        self.encrypted_data = encrypted_data
        self.benefactor_key = benefactor_key
        self.beneficiary_key = beneficiary_key

    def run(self) -> Destination:
        _log.info("LegacyDecryptingView: begin decrypt")
        from seedsigner.hardware.camera import Camera
        Camera.get_instance().stop_video_stream_mode()

        _sync_loading_frame("Decrypting...  (15-30 sec)")
        loading = LoadingScreenThread(text="Decrypting...  (15-30 sec)")
        loading.start()
        time.sleep(0.1)  # let LoadingScreenThread render its first frame before PBKDF2 grabs CPU

        error = None
        try:
            _log.info("LegacyDecryptingView: PBKDF2 start")
            seed_phrase = decrypt_seed_phrase(
                self.encrypted_data,
                self.benefactor_key,
                self.beneficiary_key,
            )
            _log.info("LegacyDecryptingView: PBKDF2 done")
        except Exception as e:
            error = e
        finally:
            loading.stop()
            _log.info("LegacyDecryptingView: loading screen stopped")

        if error is not None:
            msg = str(error)
            if any(k in msg.lower() for k in ("tag", "authentication", "invalid")):
                msg = "Decryption failed. Check that both keys are correct — spelling, capitalization, and spaces all matter."
            self.run_screen(
                WarningScreen,
                title="Decryption Failed",
                status_headline="Wrong Keys?",
                text=msg,
                button_data=[self.OK],
            )
            return Destination(BackStackView)

        if not validate_seed_phrase(seed_phrase):
            self.run_screen(
                WarningScreen,
                title="Bad Result",
                status_headline="Check Your Keys",
                text="Decryption ran but the result is not a valid BIP-39 seed phrase. Double-check both keys and try again.",
                button_data=[self.OK],
            )
            return Destination(BackStackView)

        import gc
        gc.collect()

        return Destination(
            LegacyShowDecryptedSeedView,
            view_args={"seed_phrase": seed_phrase},
        )


class LegacyShowDecryptedSeedView(View):
    SHOW_WORDS = ButtonOption("Read Seed Words")
    EXPORT_QR  = ButtonOption("Export as SeedQR")
    DONE       = ButtonOption("Done  (clears memory)")

    def __init__(self, seed_phrase: str = ""):
        super().__init__()
        self.seed_phrase = seed_phrase

    def run(self) -> Destination:
        _log.info("LegacyShowDecryptedSeedView: run start")
        word_count = len(self.seed_phrase.split())
        button_data = [self.SHOW_WORDS, self.EXPORT_QR, self.DONE]

        selected = self.run_screen(
            ButtonListScreen,
            title=f"Decrypted  ({word_count} words)",
            button_data=button_data,
            is_button_text_centered=True,
            show_back_button=False,
        )
        _log.info("LegacyShowDecryptedSeedView: button pressed index=%s", selected)

        if selected == RET_CODE__BACK_BUTTON:
            # Physical back button still fires even with show_back_button=False.
            # Loop back to the same screen — user must press Done to exit.
            return Destination(LegacyShowDecryptedSeedView, view_args={"seed_phrase": self.seed_phrase})

        if button_data[selected] == self.SHOW_WORDS:
            return Destination(
                LegacyShowSeedWordsView,
                view_args={"seed_phrase": self.seed_phrase, "page_index": 0},
            )

        if button_data[selected] == self.EXPORT_QR:
            from seedsigner.models.encode_qr import SeedQrEncoder
            qr_encoder = SeedQrEncoder(mnemonic=self.seed_phrase.split())
            self.run_screen(QRDisplayScreen, qr_encoder=qr_encoder)
            return Destination(LegacyShowDecryptedSeedView, view_args={"seed_phrase": self.seed_phrase})

        self.seed_phrase = ""
        return Destination(LegacyMainMenuView, clear_history=True)


class LegacyShowSeedWordsView(View):
    NEXT = ButtonOption("Next")
    DONE = ButtonOption("Done")

    def __init__(self, seed_phrase: str = "", page_index: int = 0):
        super().__init__()
        self.seed_phrase = seed_phrase
        self.page_index = page_index

    def run(self) -> Destination:
        _log.info("LegacyShowSeedWordsView: run start page=%s", self.page_index)
        from seedsigner.gui.screens.seed_screens import SeedWordsScreen

        words = self.seed_phrase.split()
        words_per_page = 4
        num_pages = (len(words) + words_per_page - 1) // words_per_page
        page_words = words[self.page_index * words_per_page:(self.page_index + 1) * words_per_page]
        is_last_page = self.page_index >= num_pages - 1
        button_data = [self.DONE if is_last_page else self.NEXT]

        selected = self.run_screen(
            SeedWordsScreen,
            words=page_words,
            page_index=self.page_index,
            num_pages=num_pages,
            button_data=button_data,
        )

        if selected == RET_CODE__BACK_BUTTON:
            return Destination(BackStackView)

        if button_data[selected] == self.NEXT:
            return Destination(
                LegacyShowSeedWordsView,
                view_args={"seed_phrase": self.seed_phrase, "page_index": self.page_index + 1},
            )

        return Destination(LegacyShowDecryptedSeedView, view_args={"seed_phrase": self.seed_phrase})
