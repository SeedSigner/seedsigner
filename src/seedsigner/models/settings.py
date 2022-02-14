from dataclasses import dataclass
import json
import os

from embit import bip39
from typing import List

from .seed import SeedConstants
from .singleton import Singleton
from .qr_type import QRType
from .encode_qr_density import EncodeQRDensity



class SettingsConstants:
    # User-facing selection options
    COORDINATOR__BLUE_WALLET = "BlueWallet"
    COORDINATOR__SPARROW = "Sparrow"
    COORDINATOR__SPECTER_DESKTOP = "Specter Desktop"

    ALL_COORDINATORS = [
        COORDINATOR__BLUE_WALLET,
        COORDINATOR__SPARROW,
        COORDINATOR__SPECTER_DESKTOP,
    ]

    OPTION__ENABLED = "Enabled"
    OPTION__DISABLED = "Disabled"
    OPTION__PROMPT = "Prompt"
    OPTION__REQUIRED = "Required"

    ALL_OPTIONS = [
        OPTION__ENABLED,
        OPTION__DISABLED,
        OPTION__PROMPT,
        OPTION__REQUIRED,
    ]

    LANGUAGE__ENGLISH = "English"

    ALL_LANGUAGES = [
        LANGUAGE__ENGLISH,
    ]


    # Individual settings entry attr_names
    SETTING__LANGUAGE = "language"
    SETTING__PERSISTENT_SETTINGS = "persistent_settings"
    SETTING__COORDINATORS = "coordinators"

    SETTING__PRIVACY_WARNINGS = "privacy_warnings"
    SETTING__DIRE_WARNINGS = "dire_warnings"

    SETTING__DEBUG = "debug"


    # Structural constants
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
    TYPE__ENABLED_DISABLED_PROMPT_REQURIED = "enabled_disabled_prompt_required"
    TYPE__SELECT_1 = "select_1"
    TYPE__MULTISELECT = "multiselect"
    TYPE__FREE_ENTRY = "free_entry"



@dataclass
class SettingsEntry:
    """
        Defines all the parameters for a single settings entry.

        * category: Mostly for organizational purposes when displaying options in the
            SettingsQR UI. Potentially an additional sub-level breakout in the menus
            on the device itself, too.
    """
    # TODO: Handle multi-language `display_name` and `help_text`
    category: str
    attr_name: str
    display_name: str
    verbose_name: str = None
    abbreviated_name: str = None
    visibility: str = SettingsConstants.VISIBILITY__GENERAL
    type: str = SettingsConstants.TYPE__ENABLED_DISABLED
    help_text: str = None
    possible_values: List[str] = None
    possible_values_abbreviated: List[str] = None
    default_value: str = None

    def __post_init__(self):
        if self.type == SettingsConstants.TYPE__ENABLED_DISABLED:
            self.possible_values = [SettingsConstants.OPTION__ENABLED,
                                    SettingsConstants.OPTION__DISABLED]

        elif self.type == SettingsConstants.TYPE__ENABLED_DISABLED_PROMPT:
            self.possible_values = [SettingsConstants.OPTION__ENABLED,
                                    SettingsConstants.OPTION__DISABLED,
                                    SettingsConstants.OPTION__PROMPT]

        elif self.type == SettingsConstants.TYPE__ENABLED_DISABLED_PROMPT_REQURIED:
            self.possible_values = [SettingsConstants.ALL_OPTIONS]



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
    settings_entries: List[SettingsEntry] = [
        # General options
        SettingsEntry(category=SettingsConstants.CATEGORY__SYSTEM,
                      attr_name=SettingsConstants.SETTING__LANGUAGE,
                      display_name="Language",
                      type=SettingsConstants.TYPE__SELECT_1,
                      possible_values=SettingsConstants.ALL_LANGUAGES,
                      default_value=SettingsConstants.LANGUAGE__ENGLISH),
     
        SettingsEntry(category=SettingsConstants.CATEGORY__SYSTEM,
                      attr_name=SettingsConstants.SETTING__PERSISTENT_SETTINGS,
                      display_name="Persistent Settings",
                      help_text="Store Settings on SD card",
                      default_value=SettingsConstants.OPTION__DISABLED),

        SettingsEntry(category=SettingsConstants.CATEGORY__WALLET,
                      attr_name=SettingsConstants.SETTING__COORDINATORS,
                      display_name="Coordinator Software",
                      type=SettingsConstants.TYPE__MULTISELECT,
                      possible_values=SettingsConstants.ALL_COORDINATORS,
                      default_value=SettingsConstants.ALL_COORDINATORS),

        # Advanced options
        SettingsEntry(category=SettingsConstants.CATEGORY__FEATURES,
                      attr_name=SettingsConstants.SETTING__PRIVACY_WARNINGS,
                      display_name="Show Privacy Warnings",
                      visibility=SettingsConstants.VISIBILITY__ADVANCED,
                      default_value=SettingsConstants.OPTION__ENABLED),

        SettingsEntry(category=SettingsConstants.CATEGORY__FEATURES,
                      attr_name=SettingsConstants.SETTING__DIRE_WARNINGS,
                      display_name="Show Dire Warnings",
                      visibility=SettingsConstants.VISIBILITY__ADVANCED,
                      default_value=SettingsConstants.OPTION__ENABLED),

        # Developer options
        SettingsEntry(category=SettingsConstants.CATEGORY__SYSTEM,
                      attr_name=SettingsConstants.SETTING__DEBUG,
                      display_name="Debug",
                      visibility=SettingsConstants.VISIBILITY__DEVELOPER,
                      default_value=SettingsConstants.OPTION__DISABLED),
    ]


    @classmethod
    def get_settings_entries(cls, visibiilty: str = SettingsConstants.VISIBILITY__GENERAL) -> List[SettingsEntry]:
        entries = []
        for entry in cls.settings_entries:
            if entry.visibility == visibiilty:
                entries.append(entry)
        return entries
    

    @classmethod
    def get_settings_entry(cls, attr_name) -> SettingsEntry:
        for entry in cls.settings_entries:
            if entry.attr_name == attr_name:
                return entry


    @classmethod
    def parse_abbreviated_ini(cls, abbreviated_ini: str) -> dict:
        return False


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
    def to_json(cls):
        return json.dumps({})
    

    @classmethod
    def to_html(cls):
        return ""

class Settings(Singleton):
    SETTINGS_FILENAME = "settings.json"

    @classmethod
    def get_instance(cls):
        # This is the only way to access the one and only instance
        if cls._instance is None:
            # Instantiate the one and only instance
            settings = cls.__new__(cls)
            cls._instance = settings

            settings._data = SettingsDefinition.get_defaults()

            # # default internal data structure for settings
            # settings._data = {
            #     "system": {
            #         "debug": False,
            #         "default_language": "en",
            #         "persistent_settings": False,
            #     },
            #     "display": {
            #         "text_color": "white",
            #         "background_color": "black",
            #         "camera_rotation": 0,
            #     },
            #     "wallet": {
            #         "network": SeedConstants.MAINNET,
            #         "coordinators": SettingsConstants.ALL_COORDINATORS,
            #         "qr_density": EncodeQRDensity.MEDIUM,
            #         "custom_derivation": "m/"
            #     },
            #     "features": {
            #         "xpub_export": SettingsConstants.OPTION__ENABLED,        # ENABLED | DISABLED
            #         "sig_types": SeedConstants.ALL_SIG_TYPES,                # [single_sig, multisig]
            #         "script_types": [t["type"] for t in SeedConstants.ALL_SCRIPT_TYPES],  # [script_type1, ...]
            #         "show_xpub_details": SettingsConstants.OPTION__ENABLED,  # ENABLED | DISABLED
            #         "passphrase": SettingsConstants.OPTION__ENABLED,          # ENABLED | DISABLED | PROMPT
            #         "show_privacy_warnings": SettingsConstants.OPTION__ENABLED,   # ENABLED | DISABLED
            #         "show_dire_warnings": SettingsConstants.OPTION__ENABLED,      # ENABLED | DISABLED
            #     }
            # }

            # # Read persistent settings, if it exists
            # if os.path.exists(Settings.SETTINGS_FILENAME):
            #     with open(Settings.SETTINGS_FILENAME) as settings_file:
            #         settings._data.update(json.load(settings_file))

        return cls._instance


    def __str__(self):
        return json.dumps(self._data, indent=2)
    

    def save(self):
        if self.persistent_settings:
            with open(Settings.SETTINGS_FILENAME, 'w') as settings_file:
                json.dump(self._data, settings_file)


    def update(self, new_settings: dict):
        # Can't just merge the _data dict; have to replace keys they have in common
        #   (otherwise list values will be merged instead of replaced).
        for category, category_settings in new_settings.items():
            for key, value in category_settings.items():
                self._data[category].pop(key, None)
                self._data[category][key] = value


    def set_value(self, attr_name: str, value: any):
        if attr_name not in self._data:
            raise Exception(f"Setting for {attr_name} not found")
        self._data[attr_name] = value
        # self.save()
    
    # TODO: auto-intialize dict keys as getter properties?
    def get_value(self, attr_name: str):
        if attr_name not in self._data:
            raise Exception(f"Setting for {attr_name} not found")
        return self._data[attr_name]


    ### persistent settings handling

    @property
    def persistent_settings(self):
        return self._data[SettingsConstants.SETTING__PERSISTENT_SETTINGS] == SettingsConstants.OPTION__ENABLED

    @property
    def persistent_display(self):
        if self.persistent:
            return "Yes"
        else:
            return "No"

    ### system

    @property
    def debug(self):
        return False

    @property
    def language(self):
        return "en"
        
    @property
    def wordlist(self):
        # TODO: Support BIP-39 wordlists in other languages
        return bip39.WORDLIST

    ### display

    @property
    def text_color(self):
        from seedsigner.gui.components import GUIConstants
        return GUIConstants.BODY_FONT_COLOR
    
    @property
    def qr_background_color(self):
        return self._data["display"]["qr_background_color"]
        
    @qr_background_color.setter
    def qr_background_color(self, value):
        self._data["display"]["qr_background_color"] = value
        self.__writeConfig()

    @property
    def camera_rotation(self):
        return 0

    @camera_rotation.setter
    def camera_rotation(self, value: int):
        if value in [0, 90, 180, 270]:
            self._data["display"]["camera_rotation"] = value
            self.save()
        else:
            raise Exception("Unexpected display.camera_rotation settings.json value")

    ### wallet

    @property
    def network(self):
        return SeedConstants.MAINNET

    @network.setter
    def network(self, value):
        if value in [SeedConstants.MAINNET, SeedConstants.TESTNET]:
            self._data["wallet"]["network"] = value
            self.save()
        else:
            raise Exception("Unexpected wallet.network settings.json value")

    @property
    def coordinators(self):
        return self._data[SettingsConstants.SETTING__COORDINATORS]

    @property
    def qr_density(self):
        return self._data["wallet"]["qr_density"]

    @qr_density.setter
    def qr_density(self, value):
        if value in (EncodeQRDensity.LOW, EncodeQRDensity.MEDIUM, EncodeQRDensity.HIGH, int(EncodeQRDensity.LOW), int(EncodeQRDensity.MEDIUM), int(EncodeQRDensity.HIGH)):
            self._data["wallet"]["qr_density"] = int(value)
            self.save()
        else:
            raise Exception("Unexpected wallet.qr_density settings.json value")

    def qr_psbt_type(self, coordinator):
        if coordinator == SettingsConstants.COORDINATOR__SPECTER_DESKTOP:
            return QRType.PSBTSPECTER
        else:
            return QRType.PSBTUR2

    @property
    def qr_xpub_type(self):
        return Settings.getXPubType(self.coordinators)

    @staticmethod
    def getXPubType(software):
        if software == SettingsConstants.COORDINATOR__SPECTER_DESKTOP:
            return QRType.SPECTERXPUBQR
        elif software == "Blue Wallet":
            return QRType.XPUBQR
        else:
            return QRType.URXPUBQR

    @property
    def qr_density_name(self):
        if self.qr_density == EncodeQRDensity.LOW:
            return "Low"
        elif self.qr_density == EncodeQRDensity.MEDIUM:
            return "Medium"
        elif self.qr_density == EncodeQRDensity.HIGH:
            return "High"
        else:
            return "Unknown"

    @property
    def custom_derivation(self):
        return self._data["wallet"]["custom_derivation"]

    @custom_derivation.setter
    def custom_derivation(self, value):
        # TODO: parse and validate custom derivation path
        self._data["wallet"]["custom_derivation"] = value
        self.save()

    @staticmethod
    def calc_derivation(network, wallet_type, script_type):
        # TODO: Move this to Seed?
        if network == SeedConstants.MAINNET:
            network_path = "0'"
        elif network == SeedConstants.TESTNET:
            network_path = "1'"
        else:
            raise Exception("Unexpected network")

        if wallet_type == SeedConstants.SINGLE_SIG:
            if script_type == SeedConstants.NATIVE_SEGWIT:
                return f"m/84'/{network_path}/0'"
            elif script_type == SeedConstants.NESTED_SEGWIT:
                return f"m/49'/{network_path}/0'"
            elif script_type == SeedConstants.TAPROOT:
                return f"m/86'/{network_path}/0'"
            else:
                raise Exception("Unexpected script type")

        elif wallet_type == SeedConstants.MULTISIG:
            if script_type == SeedConstants.NATIVE_SEGWIT:
                return f"m/48'/{network_path}/0'/2'"
            elif script_type == SeedConstants.NESTED_SEGWIT:
                return f"m/48'/{network_path}/0'/1'"
            elif script_type == SeedConstants.TAPROOT:
                raise Exception("Taproot multisig/musig not yet supported")
            else:
                raise Exception("Unexpected script type")
        else:
            raise Exception("Unexpected wallet type")

    # Features
    @property
    def xpub_export(self):
        return self._data["features"].get("xpub_export")
    
    @property
    def sig_types(self) -> List[str]:
        return self._data["features"].get("sig_types")

    @property
    def script_types(self) -> List[str]:
        return self._data["features"].get("script_types")

    @property
    def show_xpub_details(self) -> bool:
        return self._data["features"].get("show_xpub_details") == SettingsConstants.OPTION__ENABLED

    @property
    def passphrase(self):
        return "Enabled"

    @property
    def show_privacy_warnings(self) -> bool:
        return self._data["features"].get("show_privacy_warnings") == SettingsConstants.OPTION__ENABLED

    @property
    def show_dire_warnings(self) -> bool:
        return self._data["features"].get("show_dire_warnings") == SettingsConstants.OPTION__ENABLED
