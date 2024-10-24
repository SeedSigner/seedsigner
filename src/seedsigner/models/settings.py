import logging
import json
import os
import platform

from typing import List

from seedsigner.models.settings_definition import SettingsConstants, SettingsDefinition
from seedsigner.models.singleton import Singleton

logger = logging.getLogger(__name__)


class InvalidSettingsQRData(Exception):
    pass



class Settings(Singleton):
    HOSTNAME = platform.uname()[1]
    SEEDSIGNER_OS = "seedsigner-os"
    SETTINGS_FILENAME = "/mnt/microsd/settings.json" if HOSTNAME == SEEDSIGNER_OS else "settings.json"
        
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


    @classmethod
    def parse_settingsqr(cls, data: str) -> tuple[str, dict]:
        """
        Parses SettingsQR data and returns a tuple of (config_name, settings_dict).

        The resulting settings config can be applied by calling `Settings.update(settings_dict)`.
        """
        if not data.startswith("settings::"):
            raise InvalidSettingsQRData()

        version = data.split()[0].split("::")[1]
        if version != "v1":
            raise InvalidSettingsQRData(f"Unsupported SettingsQR version: {version}")
        
        # Start parsing key/value settings at the nth split() index
        split_index = 1

        # handle optional "name" attr
        config_name = None
        if "name=" in data.split()[1]:
            config_name = data.split("name=")[1].split()[0].replace("_", " ")
            split_index += 1

        updated_settings = {}
        for entry in data.split()[split_index:]:
            abbreviated_name, value = entry.split("=")

            # Parse multi-value settings; integer-ize where needed
            if "," in value:
                values_updated = []
                for v in value.split(","):
                    if v.isdigit():
                        v = int(v)
                    values_updated.append(v)
                value = values_updated
            elif value.isdigit():
                value = int(value)
            
            # Replace abbreviated name with full attr_name
            settings_entry = SettingsDefinition.get_settings_entry_by_abbreviated_name(abbreviated_name)
            if not settings_entry:
                logger.info(f"Ignoring unrecognized attribute: {abbreviated_name}")
                continue

            # Validate value(s) against SettingsDefinition's valid options
            if type(value) is not list:
                values = [value]
            else:
                values = value
            for v in values:
                if v not in [opt[0] for opt in settings_entry.selection_options]:
                    if settings_entry.attr_name == SettingsConstants.SETTING__PERSISTENT_SETTINGS and v == SettingsConstants.OPTION__ENABLED:
                        # Special case: trying to enable Persistent Settings when 
                        # DISABLED is the only option allowed (because the SD card is not
                        # inserted. Explicitly set to DISABLED.
                        value = SettingsConstants.OPTION__DISABLED
                        break
                    raise InvalidSettingsQRData(f"""{abbreviated_name} = '{v}' is not valid""")

            updated_settings[settings_entry.attr_name] = value
        
        return (config_name, updated_settings)


    def __str__(self):
        return json.dumps(self._data, indent=4)
    

    def save(self):
        if self._data[SettingsConstants.SETTING__PERSISTENT_SETTINGS] == SettingsConstants.OPTION__ENABLED:
            with open(Settings.SETTINGS_FILENAME, 'w') as settings_file:
                json.dump(self._data, settings_file, indent=4)
                # SeedSignerOS makes removing the microsd possible, flush and then fsync forces persistent settings to disk
                # without this, recent settings changes could be missing after the microsd card was removed
                settings_file.flush()
                os.fsync(settings_file.fileno())


    def update(self, new_settings: dict):
        """
            Replaces the current settings with the incoming dict.

            If a setting is missing from `new_settings`:
                * Hidden settings that have a value remain as-is.
                * All other missing settings are set to their default value.
        """
        for entry in SettingsDefinition.settings_entries:
            if entry.attr_name not in new_settings:
                if entry.visibility == SettingsConstants.VISIBILITY__HIDDEN and entry.attr_name in self._data:
                    # Preserve existing hidden values
                    new_settings[entry.attr_name] = self._data[entry.attr_name]
                else:
                    # Setting is missing; insert default
                    new_settings[entry.attr_name] = entry.default_value

            else:
                # Clean the incoming data, if necessary
                if entry.type == SettingsConstants.TYPE__MULTISELECT:
                    if type(new_settings[entry.attr_name]) == str:
                        # Break comma-separated SettingsQR input into List
                        new_settings[entry.attr_name] = new_settings[entry.attr_name].split(",")

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
            try:
                os.remove(self.SETTINGS_FILENAME)
                logger.info(f"Removed {self.SETTINGS_FILENAME}")
            except:
                logger.info(f"{self.SETTINGS_FILENAME} not found to be removed")
                
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
        # Iterate through the selection_options list in order to preserve intended sort
        # order when adding which options are selected.
        for value, display_name in settings_entry.selection_options:
            if value in self._data[attr_name]:
                display_names.append(display_name)
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


    def handle_microsd_state_change(action: str):
        """
        Enables/Disables the Persistent Settings option based on the MicroSD card state.
        """
        from seedsigner.hardware.microsd import MicroSD

        if Settings.HOSTNAME == Settings.SEEDSIGNER_OS:
            if action == MicroSD.ACTION__INSERTED:
                # SD card was just inserted.
                # Restore persistent settings back to defaults
                entry = SettingsDefinition.get_settings_entry(SettingsConstants.SETTING__PERSISTENT_SETTINGS)
                entry.selection_options = SettingsConstants.OPTIONS__ENABLED_DISABLED
                entry.help_text = SettingsConstants.PERSISTENT_SETTINGS__SD_INSERTED__HELP_TEXT

                # TODO: Perhaps prompt the user if the current settings (not including persistent
                # settings) should overwrite the settings on disk, if they differ:
                # - Overwrite settings on the SD?
                # - Load settings from SD?
                # if Settings file exists (meaning persistent settings was previously enabled), write out current settings to disk
                if os.path.exists(Settings.SETTINGS_FILENAME):
                    # enable persistent settings first, then save
                    Settings.get_instance()._data[SettingsConstants.SETTING__PERSISTENT_SETTINGS] = SettingsConstants.OPTION__ENABLED
                    Settings.get_instance().save()

            elif action == MicroSD.ACTION__REMOVED:
                # SD card was just removed.
                # Set persistent settings to disabled value directly
                Settings.get_instance()._data[SettingsConstants.SETTING__PERSISTENT_SETTINGS] = SettingsConstants.OPTION__DISABLED

                # set persistent settings to only have disabled as an option, adding additional help text that microSD is removed
                entry = SettingsDefinition.get_settings_entry(SettingsConstants.SETTING__PERSISTENT_SETTINGS)
                entry.selection_options = SettingsConstants.OPTIONS__ONLY_DISABLED
                entry.help_text = SettingsConstants.PERSISTENT_SETTINGS__SD_REMOVED__HELP_TEXT
            
            else:
                raise Exception(f"Invalid MicroSD action: {action}")
