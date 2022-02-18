import json
import os

from dataclasses import dataclass
from typing import Any, List

from .seed import SeedConstants
from .singleton import Singleton
from .encode_qr import EncodeQR



class SettingsConstants:
    # Basic defaults
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

    # User-facing selection options
    COORDINATOR__BLUE_WALLET = "BlueWallet"
    COORDINATOR__SPARROW = "Sparrow"
    COORDINATOR__SPECTER_DESKTOP = "Specter Desktop"
    ALL_COORDINATORS = [
        COORDINATOR__BLUE_WALLET,
        COORDINATOR__SPARROW,
        COORDINATOR__SPECTER_DESKTOP,
    ]

    LANGUAGE__ENGLISH = "en"
    ALL_LANGUAGES = [
        (LANGUAGE__ENGLISH, "English"),
    ]

    CAMERA_ROTATION__0 = 0
    CAMERA_ROTATION__90 = 90
    CAMERA_ROTATION__180 = 180
    CAMERA_ROTATION__270 = 270
    ALL_CAMERA_ROTATIONS = [
        (CAMERA_ROTATION__0, "0°"),
        (CAMERA_ROTATION__90, "90°"),
        (CAMERA_ROTATION__180, "180°"),
        (CAMERA_ROTATION__270, "270°"),
    ]

    # Individual SettingsEntry attr_names
    SETTING__LANGUAGE = "language"
    SETTING__WORDLIST_LANGUAGE = "wordlist_language"
    SETTING__PERSISTENT_SETTINGS = "persistent_settings"
    SETTING__COORDINATORS = "coordinators"

    SETTING__NETWORK = "network"
    SETTING__QR_DENSITY = "qr_density"
    SETTING__XPUB_EXPORT = "xpub_export"
    SETTING__SIG_TYPES = "sig_types"
    SETTING__SCRIPT_TYPES = "script_types"
    SETTING__XPUB_DETAILS = "xpub_details"
    SETTING__PASSPHRASE = "passphrase"
    SETTING__CAMERA_ROTATION = "camera_rotation"
    SETTING__COMPACT_SEEDQR = "compact_seedqr"
    SETTING__PRIVACY_WARNINGS = "privacy_warnings"
    SETTING__DIRE_WARNINGS = "dire_warnings"

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
    verbose_name: str = None
    abbreviated_name: str = None
    visibility: str = SettingsConstants.VISIBILITY__GENERAL
    type: str = SettingsConstants.TYPE__ENABLED_DISABLED
    help_text: str = None
    selection_options: List[str] = None
    selection_options_abbreviated: List[str] = None
    default_value: Any = None

    def __post_init__(self):
        if self.type == SettingsConstants.TYPE__ENABLED_DISABLED:
            self.selection_options = [SettingsConstants.OPTION__ENABLED,
                                      SettingsConstants.OPTION__DISABLED]

        elif self.type == SettingsConstants.TYPE__ENABLED_DISABLED_PROMPT:
            self.selection_options = [SettingsConstants.OPTION__ENABLED,
                                      SettingsConstants.OPTION__DISABLED,
                                      SettingsConstants.OPTION__PROMPT]

        elif self.type == SettingsConstants.TYPE__ENABLED_DISABLED_PROMPT_REQUIRED:
            self.selection_options = [SettingsConstants.ALL_OPTIONS]

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

        # TODO: Full babel multilanguage support! Until then, type == HIDDEN
        SettingsEntry(category=SettingsConstants.CATEGORY__SYSTEM,
                      attr_name=SettingsConstants.SETTING__LANGUAGE,
                      display_name="Language",
                      type=SettingsConstants.TYPE__SELECT_1,
                      visibility=SettingsConstants.VISIBILITY__HIDDEN,
                      selection_options=SettingsConstants.ALL_LANGUAGES,
                      default_value=SettingsConstants.LANGUAGE__ENGLISH),

        # TODO: Support other bip-39 wordlist languages! Until then, type == HIDDEN
        SettingsEntry(category=SettingsConstants.CATEGORY__SYSTEM,
                      attr_name=SettingsConstants.SETTING__WORDLIST_LANGUAGE,
                      display_name="Mnemonic language",
                      type=SettingsConstants.TYPE__SELECT_1,
                      visibility=SettingsConstants.VISIBILITY__HIDDEN,
                      selection_options=SeedConstants.ALL_WORDLIST_LANGUAGES,
                      default_value=SeedConstants.WORDLIST_LANGUAGE__ENGLISH),
     
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
                      default_value=SeedConstants.REGTEST),         # DEBUGGING!

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
                      attr_name=SettingsConstants.SETTING__SIG_TYPES,
                      display_name="Sig types",
                      type=SettingsConstants.TYPE__MULTISELECT,
                      visibility=SettingsConstants.VISIBILITY__ADVANCED,
                      selection_options=SeedConstants.ALL_SIG_TYPES,
                      default_value=SeedConstants.ALL_SIG_TYPES),

        SettingsEntry(category=SettingsConstants.CATEGORY__FEATURES,
                      attr_name=SettingsConstants.SETTING__SCRIPT_TYPES,
                      display_name="Script types",
                      type=SettingsConstants.TYPE__MULTISELECT,
                      visibility=SettingsConstants.VISIBILITY__ADVANCED,
                      selection_options=SeedConstants.ALL_SCRIPT_TYPES,
                      default_value=[SeedConstants.NATIVE_SEGWIT, SeedConstants.NESTED_SEGWIT]),

        SettingsEntry(category=SettingsConstants.CATEGORY__FEATURES,
                      attr_name=SettingsConstants.SETTING__XPUB_DETAILS,
                      display_name="Show xpub details",
                      visibility=SettingsConstants.VISIBILITY__ADVANCED,
                      default_value=SettingsConstants.OPTION__ENABLED),

        SettingsEntry(category=SettingsConstants.CATEGORY__FEATURES,
                      attr_name=SettingsConstants.SETTING__PASSPHRASE,
                      display_name="BIP-39 passphrase",
                      visibility=SettingsConstants.VISIBILITY__ADVANCED,
                      selection_options=SettingsConstants.TYPE__ENABLED_DISABLED_PROMPT_REQUIRED,
                      default_value=SettingsConstants.OPTION__ENABLED),

        SettingsEntry(category=SettingsConstants.CATEGORY__FEATURES,
                      attr_name=SettingsConstants.SETTING__CAMERA_ROTATION,
                      display_name="Camera rotation",
                      type=SettingsConstants.TYPE__SELECT_1,
                      visibility=SettingsConstants.VISIBILITY__ADVANCED,
                      selection_options=SettingsConstants.ALL_CAMERA_ROTATIONS,
                      default_value=SettingsConstants.CAMERA_ROTATION__0),

        SettingsEntry(category=SettingsConstants.CATEGORY__FEATURES,
                      attr_name=SettingsConstants.SETTING__COMPACT_SEEDQR,
                      display_name="CompactSeedQR",
                      visibility=SettingsConstants.VISIBILITY__ADVANCED,
                      default_value=SettingsConstants.OPTION__DISABLED),

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
        
        # "Hidden" settings with no UI interaction
        SettingsEntry(category=SettingsConstants.CATEGORY__SYSTEM,
                      attr_name=SettingsConstants.SETTING__QR_BRIGHTNESS,
                      display_name="QR background color",
                      type=SettingsConstants.TYPE__FREE_ENTRY,
                      visibility=SettingsConstants.VISIBILITY__HIDDEN,
                      default_value=189),
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

            # Read persistent settings file, if it exists
            if os.path.exists(Settings.SETTINGS_FILENAME):
                with open(Settings.SETTINGS_FILENAME) as settings_file:
                    settings.update(json.load(settings_file))

        return cls._instance


    def __str__(self):
        return json.dumps(self._data, indent=4)
    

    def save(self):
        if self._data[SettingsConstants.SETTING__PERSISTENT_SETTINGS] == SettingsConstants.OPTION__ENABLED:
            with open(Settings.SETTINGS_FILENAME, 'w') as settings_file:
                json.dump(self._data, settings_file, indent=4)


    def update(self, new_settings: dict):
        # Can't just merge the _data dict; have to replace keys they have in common
        #   (otherwise list values will be merged instead of replaced).
        for key, value in new_settings.items():
            self._data.pop(key, None)
            self._data[key] = value


    def set_value(self, attr_name: str, value: any):
        """
            Updates the attr's current value.

            Note that for multiselect, the value must be a List.
        """
        if attr_name not in self._data:
            raise Exception(f"Setting for {attr_name} not found")

        if SettingsDefinition.get_settings_entry(attr_name).type == SettingsConstants.TYPE__MULTISELECT:
            if type(value) != list:
                raise Exception(f"value must be a List for {attr_name}")
        
        # Special handling for toggling persistence
        if attr_name == SettingsConstants.SETTING__PERSISTENT_SETTINGS and value == SettingsConstants.OPTION__DISABLED:
            os.remove(self.SETTINGS_FILENAME)
            print(f"Removed {self.SETTINGS_FILENAME}")

        self._data[attr_name] = value
        self.save()
    

    def get_value(self, attr_name: str):
        """
            Returns the attr's current value.

            Note that for multiselect, the current value is a List.
        """
        if attr_name not in self._data:
            raise Exception(f"Setting for {attr_name} not found")
        return self._data[attr_name]


    def get_value_display_name(self, attr_name: str) -> str:
        """
            Figures out the mapping from value to display_name for the current value's
            tuple(value, display_name) definition, if it's defined that way.
            
            If the selection_options are defined as simple strings, we just return the
            string.

            Cannot be used for multiselect (use get_multiselect_value_display_names
            instead) or free entry types (there is no tuple mapping).
        """
        if attr_name not in self._data:
            raise Exception(f"Setting for {attr_name} not found")
        settings_entry = SettingsDefinition.get_settings_entry(attr_name)
        if settings_entry.type in [SettingsConstants.TYPE__FREE_ENTRY, SettingsConstants.TYPE__MULTISELECT]:
            raise Exception(f"Unsupported SettingsEntry.type: {settings_entry.type}")
        return settings_entry.get_selection_option_display_name_by_value(value=self._data[attr_name])
    

    def get_multiselect_value_display_names(self, attr_name: str) -> List[str]:
        """
            Returns a List of all the selected values' display_names.
        """
        if attr_name not in self._data:
            raise Exception(f"Setting for {attr_name} not found")
        settings_entry = SettingsDefinition.get_settings_entry(attr_name)
        if settings_entry.type != SettingsConstants.TYPE__MULTISELECT:
            raise Exception(f"Unsupported SettingsEntry.type: {settings_entry.type}")

        display_names = []
        for value in self._data[attr_name]:
            display_names.append(settings_entry.get_selection_option_display_name_by_value(value))
        return display_names



    """
        Intentionally keeping the properties very limited to avoid an expectation of
        boilerplate property code for every SettingsEntry.

        It's more cumbersome, but instead use:

        settings.get_value(SettingsConstants.SETTING__MY_SETTING_ATTR)
    """
    @property
    def debug(self) -> bool:
        return self._data[SettingsConstants.SETTING__DEBUG] == SettingsConstants.OPTION__ENABLED

