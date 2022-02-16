from dataclasses import dataclass
import json
import os

from embit import bip39
from typing import Any, List

from .seed import SeedConstants
from .singleton import Singleton
from .qr_type import QRType
from .encode_qr import EncodeQR



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

    LANGUAGE__ENGLISH = ("en", "English")
    ALL_LANGUAGES = [
        LANGUAGE__ENGLISH,
    ]

    ROTATION__0 = (0, "0°")
    ROTATION__90 = (90, "90°")
    ROTATION__180 = (180, "180°")
    ROTATION__270 = (270, "270°")
    ALL_ROTATIONS = [
        ROTATION__0, ROTATION__90, ROTATION__180, ROTATION__270
    ]

    # Individual settings entry attr_names
    SETTING__LANGUAGE = "language"
    SETTING__PERSISTENT_SETTINGS = "persistent_settings"
    SETTING__COORDINATORS = "coordinators"

    SETTING__NETWORK = "network"
    SETTING__QR_DENSITY = "qr_density"
    SETTING__XPUB_EXPORT = "xpub_export"
    SETTING__CAMERA_ROTATION = "camera_rotation"
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
    selection_options: List[str] = None
    selection_options_abbreviated: List[str] = None
    default_value: str = None

    def __post_init__(self):
        if self.type == SettingsConstants.TYPE__ENABLED_DISABLED:
            self.selection_options = [SettingsConstants.OPTION__ENABLED,
                                      SettingsConstants.OPTION__DISABLED]

        elif self.type == SettingsConstants.TYPE__ENABLED_DISABLED_PROMPT:
            self.selection_options = [SettingsConstants.OPTION__ENABLED,
                                      SettingsConstants.OPTION__DISABLED,
                                      SettingsConstants.OPTION__PROMPT]

        elif self.type == SettingsConstants.TYPE__ENABLED_DISABLED_PROMPT_REQURIED:
            self.selection_options = [SettingsConstants.ALL_OPTIONS]
    

    @property
    def selection_options_display_names(self) -> List[str]:
        if type(self.selection_options[0]) == tuple:
            return [v[1] for v in self.selection_options]
        else:
            # Always return a copy so the original can't be altered
            return list(self.selection_options)


    def get_selection_option_value(self, i: int):
        value = self.selection_options[i]
        if type(value) == tuple:
            value = value[0]
        return value


    def get_selection_option_display_name(self, i: int) -> str:
        value = self.selection_options[i]
        if type(value) == tuple:
            value = value[1]
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
                return display_name



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
                      selection_options=SettingsConstants.ALL_LANGUAGES,
                      default_value=SettingsConstants.LANGUAGE__ENGLISH),
     
        SettingsEntry(category=SettingsConstants.CATEGORY__SYSTEM,
                      attr_name=SettingsConstants.SETTING__PERSISTENT_SETTINGS,
                      display_name="Persistent settings",
                      help_text="Store Settings on SD card",
                      default_value=SettingsConstants.OPTION__DISABLED),

        SettingsEntry(category=SettingsConstants.CATEGORY__WALLET,
                      attr_name=SettingsConstants.SETTING__COORDINATORS,
                      display_name="Coordinator software",
                      type=SettingsConstants.TYPE__MULTISELECT,
                      selection_options=SettingsConstants.ALL_COORDINATORS,
                      default_value=SettingsConstants.ALL_COORDINATORS),

        # Advanced options
        SettingsEntry(category=SettingsConstants.CATEGORY__FEATURES,
                      attr_name=SettingsConstants.SETTING__NETWORK,
                      display_name="Bitcoin network",
                      type=SettingsConstants.TYPE__SELECT_1,
                      visibility=SettingsConstants.VISIBILITY__ADVANCED,
                      selection_options=SeedConstants.ALL_NETWORKS,
                      default_value=SeedConstants.MAINNET[0]),

        SettingsEntry(category=SettingsConstants.CATEGORY__FEATURES,
                      attr_name=SettingsConstants.SETTING__QR_DENSITY,
                      display_name="QR code density",
                      type=SettingsConstants.TYPE__SELECT_1,
                      visibility=SettingsConstants.VISIBILITY__ADVANCED,
                      selection_options=EncodeQR.ALL_DENSITIES,
                      default_value=EncodeQR.DENSITY__MEDIUM),

        SettingsEntry(category=SettingsConstants.CATEGORY__FEATURES,
                      attr_name=SettingsConstants.SETTING__XPUB_EXPORT,
                      display_name="Xpub export",
                      visibility=SettingsConstants.VISIBILITY__ADVANCED,
                      default_value=SettingsConstants.OPTION__ENABLED),

        SettingsEntry(category=SettingsConstants.CATEGORY__FEATURES,
                      attr_name=SettingsConstants.SETTING__QR_DENSITY,
                      display_name="QR code density",
                      type=SettingsConstants.TYPE__SELECT_1,
                      visibility=SettingsConstants.VISIBILITY__ADVANCED,
                      selection_options=SettingsConstants.ALL_ROTATIONS,
                      default_value=SettingsConstants.ROTATION__0),

        SettingsEntry(category=SettingsConstants.CATEGORY__FEATURES,
                      attr_name=SettingsConstants.SETTING__PRIVACY_WARNINGS,
                      display_name="Show privacy warnings",
                      visibility=SettingsConstants.VISIBILITY__ADVANCED,
                      default_value=SettingsConstants.OPTION__ENABLED),

        SettingsEntry(category=SettingsConstants.CATEGORY__FEATURES,
                      attr_name=SettingsConstants.SETTING__DIRE_WARNINGS,
                      display_name="Show dire warnings",
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
        raise Exception("Not implemented, maybe not needed")


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
        raise Exception("Not implemented")
    

    @classmethod
    def to_html(cls):
        raise Exception("Not implemented, maybe not needed")



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
            #         "qr_density": EncodeQR.DENSITY__MEDIUM,
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

            # TODO: Read persistent settings, if it exists
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
    

    def get_value(self, attr_name: str):
        if attr_name not in self._data:
            raise Exception(f"Setting for {attr_name} not found")
        return self._data[attr_name]


    def get_value_display_name(self, attr_name: str) -> str:
        if attr_name not in self._data:
            raise Exception(f"Setting for {attr_name} not found")
        settings_entry = SettingsDefinition.get_settings_entry(attr_name)
        if settings_entry.type in [SettingsConstants.TYPE__FREE_ENTRY, SettingsConstants.TYPE__MULTISELECT]:
            raise Exception(f"Unsupported SettingsEntry.type: {settings_entry.type}")
        return settings_entry.get_selection_option_display_name_by_value(value=self._data[attr_name])
    

    def get_multiselect_value_display_names(self, attr_name: str) -> List[str]:
        if attr_name not in self._data:
            raise Exception(f"Setting for {attr_name} not found")
        settings_entry = SettingsDefinition.get_settings_entry(attr_name)
        if settings_entry.type != SettingsConstants.TYPE__MULTISELECT:
            raise Exception(f"Unsupported SettingsEntry.type: {settings_entry.type}")

        display_names = []
        for value in self._data[attr_name]:
            display_names.append(settings_entry.get_selection_option_display_name_by_value(value))
        return display_names



    @property
    def persistent_settings(self) -> bool:
        return self._data[SettingsConstants.SETTING__PERSISTENT_SETTINGS] == SettingsConstants.OPTION__ENABLED

    @property
    def debug(self) -> bool:
        return self._data[SettingsConstants.SETTING__DEBUG] == SettingsConstants.OPTION__ENABLED

    # TODO: Deeper support for GUI-wide color customization
    @property
    def text_color(self):
        from seedsigner.gui.components import GUIConstants
        return GUIConstants.BODY_FONT_COLOR
    
    @property
    def qr_background_color(self):
        return self._data["display"]["qr_background_color"]


    @staticmethod
    def qr_psbt_type(coordinator):
        if coordinator == SettingsConstants.COORDINATOR__SPECTER_DESKTOP:
            return QRType.PSBTSPECTER
        else:
            return QRType.PSBTUR2

    @property
    def qr_xpub_type(self):
        return Settings.getXPubType(self._data[SettingsConstants.SETTING__COORDINATORS])

    @staticmethod
    def getXPubType(coordinators):
        if coordinators == [SettingsConstants.COORDINATOR__SPECTER_DESKTOP]:
            return QRType.SPECTERXPUBQR
        elif coordinators == [SettingsConstants.COORDINATOR__BLUE_WALLET]:
            return QRType.XPUBQR
        else:
            return QRType.URXPUBQR

    @property
    def custom_derivation(self):
        return self._data["wallet"]["custom_derivation"]

    @custom_derivation.setter
    def custom_derivation(self, value):
        # TODO: parse and validate custom derivation path
        self._data["wallet"]["custom_derivation"] = value
        self.save()
