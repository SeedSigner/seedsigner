from dataclasses import dataclass
from typing import Any, List

from seedsigner.helpers.l10n import mark_for_translation as _mft


class SettingsConstants:
    # Basic defaults
    OPTION__ENABLED = "E"
    OPTION__DISABLED = "D"
    OPTION__PROMPT = "P"
    OPTION__REQUIRED = "R"
    OPTIONS__ENABLED_DISABLED = [
        (OPTION__ENABLED, _mft("Enabled")),
        (OPTION__DISABLED, _mft("Disabled")),
    ]
    OPTIONS__ONLY_DISABLED = [
        (OPTION__DISABLED, _mft("Disabled")),
    ]
    OPTIONS__PROMPT_REQUIRED_DISABLED = [
        (OPTION__PROMPT, _mft("Prompt")),
        (OPTION__REQUIRED, _mft("Required")),
        (OPTION__DISABLED, _mft("Disabled")),
    ]
    OPTIONS__ENABLED_DISABLED_REQUIRED = OPTIONS__ENABLED_DISABLED +[
        (OPTION__REQUIRED, _mft("Required")),
    ]
    OPTIONS__ENABLED_DISABLED_PROMPT = OPTIONS__ENABLED_DISABLED + [
        (OPTION__PROMPT, _mft("Prompt")),
    ]
    ALL_OPTIONS = OPTIONS__ENABLED_DISABLED_PROMPT + [
        (OPTION__REQUIRED, _mft("Required")),
    ]

    # User-facing selection options
    COORDINATOR__BLUE_WALLET = "bw"
    COORDINATOR__NUNCHUK = "nun"
    COORDINATOR__SPARROW = "spa"
    COORDINATOR__SPECTER_DESKTOP = "spd"
    COORDINATOR__KEEPER = "kpr"
    ALL_COORDINATORS = [
        (COORDINATOR__BLUE_WALLET, "BlueWallet"),
        (COORDINATOR__NUNCHUK, "Nunchuk"),
        (COORDINATOR__SPARROW, "Sparrow"),
        (COORDINATOR__SPECTER_DESKTOP, "Specter Desktop"),
        (COORDINATOR__KEEPER, "Keeper"),
    ]

    LOCALE__ARABIC = "ar"
    LOCALE__CZECH = "cs"
    LOCALE__ENGLISH = "en"
    LOCALE__FRENCH = "fr"
    LOCALE__GERMAN = "de"
    LOCALE__HEBREW = "he"
    LOCALE__JAPANESE = "ja"
    LOCALE__KOREAN = "kr"
    LOCALE__PORTUGUESE = "pt"
    LOCALE__RUSSIAN = "ru"
    LOCALE__SPANISH = "es"
    # Do not wrap for translation; always present each language in its native form
    ALL_LOCALES = [
        # (LOCALE__ARABIC, "Arabic"),
        # (LOCALE__CZECH, "čeština"),
        (LOCALE__ENGLISH, "English"),
        # (LOCALE__FRENCH, "Français"),
        # (LOCALE__GERMAN, "Deutsch"),
        # (LOCALE__HEBREW, "Hebrew"),
        # (LOCALE__JAPANESE, "Japanese"),
        # (LOCALE__KOREAN, "Korean"),
        # (LOCALE__PORTUGUESE, "Português"),
        # (LOCALE__RUSSIAN, "русский"),
        (LOCALE__SPANISH, "Español"),
    ]

    BTC_DENOMINATION__BTC = "btc"
    BTC_DENOMINATION__SATS = "sats"
    BTC_DENOMINATION__THRESHOLD = "thr"
    BTC_DENOMINATION__BTCSATSHYBRID = "hyb"
    ALL_BTC_DENOMINATIONS = [
        (BTC_DENOMINATION__BTC, _mft("BTC")),
        (BTC_DENOMINATION__SATS, _mft("sats")),
        (BTC_DENOMINATION__THRESHOLD, _mft("Threshold at 0.01")),
        (BTC_DENOMINATION__BTCSATSHYBRID, _mft("BTC | sats hybrid")),
    ]

    CAMERA_ROTATION__0 = 0
    CAMERA_ROTATION__90 = 90
    CAMERA_ROTATION__180 = 180
    CAMERA_ROTATION__270 = 270
    ALL_CAMERA_ROTATIONS = [
        (CAMERA_ROTATION__0, _mft("0°")),
        (CAMERA_ROTATION__90, _mft("90°")),
        (CAMERA_ROTATION__180, _mft("180°")),
        (CAMERA_ROTATION__270, _mft("270°")),
    ]

    # QR code constants
    DENSITY__LOW = "L"
    DENSITY__MEDIUM = "M"
    DENSITY__HIGH = "H"
    # TRANSLATOR_NOTE: QR code density option: Low, Medium, High
    density_low = _mft("Low")
    # TRANSLATOR_NOTE: QR code density option: Low, Medium, High
    density_medium = _mft("Medium")
    # TRANSLATOR_NOTE: QR code density option: Low, Medium, High
    density_high = _mft("High")
    ALL_DENSITIES = [
        (DENSITY__LOW, density_low),
        (DENSITY__MEDIUM, density_medium),
        (DENSITY__HIGH, density_high),
    ]

    # Seed-related constants
    MAINNET = "M"
    TESTNET = "T"
    REGTEST = "R"
    ALL_NETWORKS = [
        (MAINNET, _mft("Mainnet")),
        (TESTNET, _mft("Testnet")),
        (REGTEST, _mft("Regtest"))
    ]

    @classmethod
    def map_network_to_embit(cls, network) -> str:
        # Note these are `embit` constants; do not wrap for translation
        if network == SettingsConstants.MAINNET:
            return "main"
        elif network == SettingsConstants.TESTNET:
            return "test"
        if network == SettingsConstants.REGTEST:
            return "regtest"
    
    PERSISTENT_SETTINGS__SD_INSERTED__HELP_TEXT = _mft("Store Settings on SD card")
    PERSISTENT_SETTINGS__SD_REMOVED__HELP_TEXT = _mft("Insert SD card to enable")

    SINGLE_SIG = "ss"
    MULTISIG = "ms"
    ALL_SIG_TYPES = [
        (SINGLE_SIG, _mft("Single Sig")),
        (MULTISIG, _mft("Multisig")),
    ]

    LEGACY_P2PKH = "leg"
    NATIVE_SEGWIT = "nat"
    NESTED_SEGWIT = "nes"
    TAPROOT = "tr"
    CUSTOM_DERIVATION = "cus"
    ALL_SCRIPT_TYPES = [
        (NATIVE_SEGWIT, _mft("Native Segwit")),
        (NESTED_SEGWIT, _mft("Nested Segwit")),
        (LEGACY_P2PKH, _mft("Legacy")),
        (TAPROOT, _mft("Taproot")),
        (CUSTOM_DERIVATION, _mft("Custom Derivation")),
    ]

    WORDLIST_LANGUAGE__ENGLISH = "en"
    WORDLIST_LANGUAGE__CHINESE_SIMPLIFIED = "zh_Hans_CN"
    WORDLIST_LANGUAGE__CHINESE_TRADITIONAL = "zh_Hant_TW"
    WORDLIST_LANGUAGE__FRENCH = "fr"
    WORDLIST_LANGUAGE__ITALIAN = "it"
    WORDLIST_LANGUAGE__JAPANESE = "jp"
    WORDLIST_LANGUAGE__KOREAN = "kr"
    WORDLIST_LANGUAGE__PORTUGUESE = "pt"
    ALL_WORDLIST_LANGUAGES = [
        (WORDLIST_LANGUAGE__ENGLISH, "English"),
        # (WORDLIST_LANGUAGE__CHINESE_SIMPLIFIED, "简体中文"),
        # (WORDLIST_LANGUAGE__CHINESE_TRADITIONAL, "繁體中文"),
        # (WORDLIST_LANGUAGE__FRENCH, "Français"),
        # (WORDLIST_LANGUAGE__ITALIAN, "Italiano"),
        # (WORDLIST_LANGUAGE__JAPANESE, "日本語"),
        # (WORDLIST_LANGUAGE__KOREAN, "한국어"),
        # (WORDLIST_LANGUAGE__PORTUGUESE, "Português"),
    ]

    
    # Individual SettingsEntry attr_names
    # Note: attr_names are internal constants; do not wrap for translation
    SETTING__LOCALE = "locale"
    SETTING__WORDLIST_LANGUAGE = "wordlist_language"
    SETTING__PERSISTENT_SETTINGS = "persistent_settings"
    SETTING__COORDINATORS = "coordinators"
    SETTING__BTC_DENOMINATION = "denomination"

    SETTING__NETWORK = "network"
    SETTING__QR_DENSITY = "qr_density"
    SETTING__XPUB_EXPORT = "xpub_export"
    SETTING__SIG_TYPES = "sig_types"
    SETTING__SCRIPT_TYPES = "script_types"
    SETTING__XPUB_DETAILS = "xpub_details"
    SETTING__PASSPHRASE = "passphrase"
    SETTING__CAMERA_ROTATION = "camera_rotation"
    SETTING__COMPACT_SEEDQR = "compact_seedqr"
    SETTING__BIP85_CHILD_SEEDS = "bip85_child_seeds"
    SETTING__ELECTRUM_SEEDS = "electrum_seeds"
    SETTING__MESSAGE_SIGNING = "message_signing"
    SETTING__PRIVACY_WARNINGS = "privacy_warnings"
    SETTING__DIRE_WARNINGS = "dire_warnings"
    SETTING__QR_BRIGHTNESS_TIPS = "qr_brightness_tips"
    SETTING__PARTNER_LOGOS = "partner_logos"

    SETTING__DEBUG = "debug"

    # Hidden settings
    SETTING__QR_BRIGHTNESS = "qr_background_color"


    # Structural constants
    # TODO: Not using these for display purposes yet (ever?)
    CATEGORY__SYSTEM = "system"
    CATEGORY__DISPLAY = "display"
    CATEGORY__WALLET = "wallet"
    CATEGORY__FEATURES = "features"

    VISIBILITY__GENERAL = "general"
    VISIBILITY__ADVANCED = "advanced"
    VISIBILITY__DEVELOPER = "developer"
    VISIBILITY__HIDDEN = "hidden"   # For data-only (e.g. custom_derivation), not configurable by the user

    # TODO: Is there really a difference between ENABLED and PROMPT?
    TYPE__ENABLED_DISABLED = "enabled_disabled"
    TYPE__ENABLED_DISABLED_PROMPT = "enabled_disabled_prompt"
    TYPE__ENABLED_DISABLED_PROMPT_REQUIRED = "enabled_disabled_prompt_required"
    TYPE__SELECT_1 = "select_1"
    TYPE__MULTISELECT = "multiselect"
    TYPE__FREE_ENTRY = "free_entry"

    ALL_ENABLED_DISABLED_TYPES = [
        TYPE__ENABLED_DISABLED,
        TYPE__ENABLED_DISABLED_PROMPT,
        TYPE__ENABLED_DISABLED_PROMPT_REQUIRED,
    ]

    # Electrum seed constants
    ELECTRUM_SEED_STANDARD = "01"
    ELECTRUM_SEED_SEGWIT = "100"
    ELECTRUM_SEED_2FA = "101"
    ELECTRUM_PBKDF2_ROUNDS=2048

    # Label strings
    LABEL__BIP39_PASSPHRASE = _mft("BIP-39 Passphrase")
    # TRANSLATOR_NOTE: Terminology used by Electrum seeds; equivalent to bip39 passphrase
    custom_extension = _mft("Custom Extension")
    LABEL__CUSTOM_EXTENSION = custom_extension



@dataclass
class SettingsEntry:
    """
        Defines all the parameters for a single settings entry.

        * category: Mostly for organizational purposes when displaying options in the
            SettingsQR UI. Potentially an additional sub-level breakout in the menus
            on the device itself, too.
        
        * selection_options: May be specified as a List(Any) or List(tuple(Any, str)).
            The tuple form is to provide a human-readable display_name. Probably all
            entries should shift to using the tuple form.
    """
    # TODO: Handle multi-language `display_name` and `help_text`
    category: str
    attr_name: str
    display_name: str
    abbreviated_name: str = None
    visibility: str = SettingsConstants.VISIBILITY__GENERAL
    type: str = SettingsConstants.TYPE__ENABLED_DISABLED
    help_text: str = None
    selection_options: list[tuple[str | int], str] = None
    default_value: Any = None

    def __post_init__(self):
        if self.type == SettingsConstants.TYPE__ENABLED_DISABLED:
            self.selection_options = SettingsConstants.OPTIONS__ENABLED_DISABLED

        elif self.type == SettingsConstants.TYPE__ENABLED_DISABLED_PROMPT:
            self.selection_options = SettingsConstants.OPTIONS__ENABLED_DISABLED_PROMPT

        elif self.type == SettingsConstants.TYPE__ENABLED_DISABLED_PROMPT_REQUIRED:
            self.selection_options = SettingsConstants.ALL_OPTIONS

        # Account for List[tuple] and tuple formats as default_value        
        if type(self.default_value) == list and type(self.default_value[0]) == tuple:
            self.default_value = [v[0] for v in self.default_value]
        elif type(self.default_value) == tuple:
            self.default_value = self.default_value[0]


    @property
    def selection_options_display_names(self) -> List[str]:
        if type(self.selection_options[0]) == tuple:
            return [v[1] for v in self.selection_options]
        else:
            # Always return a copy so the original can't be altered
            return list(self.selection_options)


    def get_selection_option_value(self, i: int):
        """ Returns the value of the selection option at index `i` """
        value = self.selection_options[i]
        if type(value) == tuple:
            value = value[0]
        return value

    
    def get_selection_option_display_name_by_value(self, value) -> str:
        for option in self.selection_options:
            if type(option) == tuple:
                option_value = option[0]
                display_name = option[1]
            else:
                option_value = option
                display_name = option
            if option_value == value:
                return _mft(display_name)


    def get_selection_option_value_by_display_name(self, display_name: str):
        for option in self.selection_options:
            if type(option) == tuple:
                option_value = option[0]
                option_display_name = option[1]
            else:
                option_value = option
                option_display_name = option
            if option_display_name == display_name:
                return option_value


    def to_dict(self) -> dict:
        if self.selection_options:
            selection_options = []
            for option in self.selection_options:
                if type(option) == tuple:
                    value = option[0]
                    display_name = option[1]
                else:
                    display_name = option
                    value = option
                selection_options.append({
                    "display_name": display_name,
                    "value": value
                })
        else:
            selection_options = None

        return {
            "category": self.category,
            "attr_name": self.attr_name,
            "abbreviated_name": self.abbreviated_name,
            "display_name": self.display_name,
            "visibility": self.visibility,
            "type": self.type,
            "help_text": self.help_text,
            "selection_options": selection_options,
            "default_value": self.default_value,
        }



class SettingsDefinition:
    """
        Master list of all settings, their possible options, their defaults, on-device
        display strings, and enriched SettingsQR UI options.

        Used to auto-build the Settings UI menuing with no repetitive boilerplate code.

        Defines the on-disk persistent storage structure and can read that format back
        and validate the values.

        Used to generate a master json file that documents all these params which can
        then be read in by the SettingsQR UI to auto-generate the necessary html inputs.
    """
    # Increment if there are any breaking changes; write migrations to bridge from
    # incompatible prior versions.
    version: int = 1

    settings_entries: List[SettingsEntry] = [
        # General options

        SettingsEntry(category=SettingsConstants.CATEGORY__SYSTEM,
                      attr_name=SettingsConstants.SETTING__LOCALE,
                      abbreviated_name="lang",
                      display_name=_mft("Language"),
                      type=SettingsConstants.TYPE__SELECT_1,
                      selection_options=SettingsConstants.ALL_LOCALES,
                      default_value=SettingsConstants.LOCALE__ENGLISH),

        # TODO: Support other bip-39 wordlist languages! Until then, type == HIDDEN
        SettingsEntry(category=SettingsConstants.CATEGORY__SYSTEM,
                      attr_name=SettingsConstants.SETTING__WORDLIST_LANGUAGE,
                      abbreviated_name="wordlist_lang",
                      display_name=_mft("Mnemonic language"),
                      type=SettingsConstants.TYPE__SELECT_1,
                      visibility=SettingsConstants.VISIBILITY__HIDDEN,
                      selection_options=SettingsConstants.ALL_WORDLIST_LANGUAGES,
                      default_value=SettingsConstants.WORDLIST_LANGUAGE__ENGLISH),

        SettingsEntry(category=SettingsConstants.CATEGORY__SYSTEM,
                      attr_name=SettingsConstants.SETTING__PERSISTENT_SETTINGS,
                      abbreviated_name="persistent",
                      display_name=_mft("Persistent settings"),
                      help_text=SettingsConstants.PERSISTENT_SETTINGS__SD_INSERTED__HELP_TEXT,
                      default_value=SettingsConstants.OPTION__DISABLED),

        SettingsEntry(category=SettingsConstants.CATEGORY__WALLET,
                      attr_name=SettingsConstants.SETTING__COORDINATORS,
                      abbreviated_name="coords",
                      display_name=_mft("Coordinator software"),
                      type=SettingsConstants.TYPE__MULTISELECT,
                      selection_options=SettingsConstants.ALL_COORDINATORS,
                      default_value=[
                          SettingsConstants.COORDINATOR__BLUE_WALLET,
                          SettingsConstants.COORDINATOR__NUNCHUK,
                          SettingsConstants.COORDINATOR__SPARROW,
                          SettingsConstants.COORDINATOR__SPECTER_DESKTOP,
                      ]),

        SettingsEntry(category=SettingsConstants.CATEGORY__SYSTEM,
                      attr_name=SettingsConstants.SETTING__BTC_DENOMINATION,
                      abbreviated_name="denom",
                      display_name=_mft("Denomination display"),
                      type=SettingsConstants.TYPE__SELECT_1,
                      selection_options=SettingsConstants.ALL_BTC_DENOMINATIONS,
                      default_value=SettingsConstants.BTC_DENOMINATION__THRESHOLD),
     

        # Advanced options
        SettingsEntry(category=SettingsConstants.CATEGORY__FEATURES,
                      attr_name=SettingsConstants.SETTING__NETWORK,
                      display_name=_mft("Bitcoin network"),
                      type=SettingsConstants.TYPE__SELECT_1,
                      visibility=SettingsConstants.VISIBILITY__ADVANCED,
                      selection_options=SettingsConstants.ALL_NETWORKS,
                      default_value=SettingsConstants.MAINNET),

        SettingsEntry(category=SettingsConstants.CATEGORY__FEATURES,
                      attr_name=SettingsConstants.SETTING__QR_DENSITY,
                      display_name=_mft("QR code density"),
                      type=SettingsConstants.TYPE__SELECT_1,
                      visibility=SettingsConstants.VISIBILITY__ADVANCED,
                      selection_options=SettingsConstants.ALL_DENSITIES,
                      default_value=SettingsConstants.DENSITY__MEDIUM),

        SettingsEntry(category=SettingsConstants.CATEGORY__FEATURES,
                      attr_name=SettingsConstants.SETTING__XPUB_EXPORT,
                      display_name=_mft("Xpub export"),
                      visibility=SettingsConstants.VISIBILITY__ADVANCED,
                      default_value=SettingsConstants.OPTION__ENABLED),

        SettingsEntry(category=SettingsConstants.CATEGORY__FEATURES,
                      attr_name=SettingsConstants.SETTING__SIG_TYPES,
                      abbreviated_name="sigs",
                      display_name=_mft("Sig types"),
                      type=SettingsConstants.TYPE__MULTISELECT,
                      visibility=SettingsConstants.VISIBILITY__ADVANCED,
                      selection_options=SettingsConstants.ALL_SIG_TYPES,
                      default_value=SettingsConstants.ALL_SIG_TYPES),

        SettingsEntry(category=SettingsConstants.CATEGORY__FEATURES,
                      attr_name=SettingsConstants.SETTING__SCRIPT_TYPES,
                      abbreviated_name="scripts",
                      display_name=_mft("Script types"),
                      type=SettingsConstants.TYPE__MULTISELECT,
                      visibility=SettingsConstants.VISIBILITY__ADVANCED,
                      selection_options=SettingsConstants.ALL_SCRIPT_TYPES,
                      default_value=[SettingsConstants.NATIVE_SEGWIT, SettingsConstants.NESTED_SEGWIT, SettingsConstants.TAPROOT]),

        SettingsEntry(category=SettingsConstants.CATEGORY__FEATURES,
                      attr_name=SettingsConstants.SETTING__XPUB_DETAILS,
                      display_name=_mft("Show xpub details"),
                      visibility=SettingsConstants.VISIBILITY__ADVANCED,
                      default_value=SettingsConstants.OPTION__ENABLED),

        SettingsEntry(category=SettingsConstants.CATEGORY__FEATURES,
                      attr_name=SettingsConstants.SETTING__PASSPHRASE,
                      display_name=_mft("BIP-39 passphrase"),
                      type=SettingsConstants.TYPE__SELECT_1,
                      visibility=SettingsConstants.VISIBILITY__ADVANCED,
                      selection_options=SettingsConstants.OPTIONS__ENABLED_DISABLED_REQUIRED,
                      default_value=SettingsConstants.OPTION__ENABLED),

        SettingsEntry(category=SettingsConstants.CATEGORY__FEATURES,
                      attr_name=SettingsConstants.SETTING__CAMERA_ROTATION,
                      abbreviated_name="camera",
                      display_name=_mft("Camera rotation"),
                      type=SettingsConstants.TYPE__SELECT_1,
                      visibility=SettingsConstants.VISIBILITY__ADVANCED,
                      selection_options=SettingsConstants.ALL_CAMERA_ROTATIONS,
                      default_value=SettingsConstants.CAMERA_ROTATION__180),

        SettingsEntry(category=SettingsConstants.CATEGORY__FEATURES,
                      attr_name=SettingsConstants.SETTING__COMPACT_SEEDQR,
                      display_name=_mft("Compact SeedQR"),
                      visibility=SettingsConstants.VISIBILITY__ADVANCED,
                      default_value=SettingsConstants.OPTION__ENABLED),

        SettingsEntry(category=SettingsConstants.CATEGORY__FEATURES,
                      attr_name=SettingsConstants.SETTING__BIP85_CHILD_SEEDS,
                      abbreviated_name="bip85",
                      display_name=_mft("BIP-85 child seeds"),
                      visibility=SettingsConstants.VISIBILITY__ADVANCED,
                      default_value=SettingsConstants.OPTION__DISABLED),

        SettingsEntry(category=SettingsConstants.CATEGORY__FEATURES,
                      attr_name=SettingsConstants.SETTING__ELECTRUM_SEEDS,
                      abbreviated_name="electrum",
                      display_name=_mft("Electrum seeds"),
                      help_text=_mft("Native Segwit only"),
                      visibility=SettingsConstants.VISIBILITY__ADVANCED,
                      default_value=SettingsConstants.OPTION__DISABLED),

        SettingsEntry(category=SettingsConstants.CATEGORY__FEATURES,
                      attr_name=SettingsConstants.SETTING__MESSAGE_SIGNING,
                      display_name=_mft("Message signing"),
                      visibility=SettingsConstants.VISIBILITY__ADVANCED,
                      default_value=SettingsConstants.OPTION__DISABLED),

        SettingsEntry(category=SettingsConstants.CATEGORY__FEATURES,
                      attr_name=SettingsConstants.SETTING__PRIVACY_WARNINGS,
                      abbreviated_name="priv_warn",
                      display_name=_mft("Show privacy warnings"),
                      visibility=SettingsConstants.VISIBILITY__ADVANCED,
                      default_value=SettingsConstants.OPTION__ENABLED),

        SettingsEntry(category=SettingsConstants.CATEGORY__FEATURES,
                      attr_name=SettingsConstants.SETTING__DIRE_WARNINGS,
                      abbreviated_name="dire_warn",
                      display_name=_mft("Show dire warnings"),
                      visibility=SettingsConstants.VISIBILITY__ADVANCED,
                      default_value=SettingsConstants.OPTION__ENABLED),

        SettingsEntry(category=SettingsConstants.CATEGORY__FEATURES,
                      attr_name=SettingsConstants.SETTING__QR_BRIGHTNESS_TIPS,
                      display_name=_mft("Show QR brightness tips"),
                      visibility=SettingsConstants.VISIBILITY__ADVANCED,
                      default_value=SettingsConstants.OPTION__ENABLED),

        SettingsEntry(category=SettingsConstants.CATEGORY__FEATURES,
                      attr_name=SettingsConstants.SETTING__PARTNER_LOGOS,
                      abbreviated_name="partners",
                      display_name=_mft("Show partner logos"),
                      visibility=SettingsConstants.VISIBILITY__ADVANCED,
                      default_value=SettingsConstants.OPTION__ENABLED),

        # Developer options
        # TODO: No real Developer options needed yet. Disable for now.
        # SettingsEntry(category=SettingsConstants.CATEGORY__SYSTEM,
        #               attr_name=SettingsConstants.SETTING__DEBUG,
        #               display_name="Debug",
        #               visibility=SettingsConstants.VISIBILITY__DEVELOPER,
        #               default_value=SettingsConstants.OPTION__DISABLED),
        
        # "Hidden" settings with no UI interaction
        SettingsEntry(category=SettingsConstants.CATEGORY__SYSTEM,
                      attr_name=SettingsConstants.SETTING__QR_BRIGHTNESS,
                      abbreviated_name="qr_brightness",
                      display_name=_mft("QR background color"),
                      type=SettingsConstants.TYPE__FREE_ENTRY,
                      visibility=SettingsConstants.VISIBILITY__HIDDEN,
                      default_value=62),
    ]


    @classmethod
    def get_settings_entries(cls, visibility: str = SettingsConstants.VISIBILITY__GENERAL) -> List[SettingsEntry]:
        entries = []
        for entry in cls.settings_entries:
            if entry.visibility == visibility:
                entries.append(entry)
        return entries
    

    @classmethod
    def get_settings_entry(cls, attr_name) -> SettingsEntry:
        for entry in cls.settings_entries:
            if entry.attr_name == attr_name:
                return entry


    @classmethod
    def get_settings_entry_by_abbreviated_name(cls, abbreviated_name: str) -> SettingsEntry:
        for entry in cls.settings_entries:
            if abbreviated_name in [entry.abbreviated_name, entry.attr_name]:
                return entry


    @classmethod
    def get_defaults(cls) -> dict:
        as_dict = {}
        for entry in SettingsDefinition.settings_entries:
            if type(entry.default_value) == list:
                # Must copy the default_value list, otherwise we'll inadvertently change
                # defaults when updating these attrs
                as_dict[entry.attr_name] = list(entry.default_value)
            else:
                as_dict[entry.attr_name] = entry.default_value
        return as_dict


    @classmethod
    def to_dict(cls) -> dict:
        output = {
            "settings_entries": [],
        }
        for settings_entry in cls.settings_entries:
            output["settings_entries"].append(settings_entry.to_dict())
        
        return output



if __name__ == "__main__":
    import json
    import os

    hostname = os.uname()[1]
  
    if hostname == "seedsigner-os":
        output_file = "/mnt/microsd/settings_definition.json"
    else:
        output_file = "settings_definition.json"
    
    with open(output_file, 'w') as json_file:
        json.dump(SettingsDefinition.to_dict(), json_file, indent=4)
