import json, os, subprocess

from typing import Any, List

from seedsigner.models.settings_definition import SettingsConstants, SettingsDefinition
from .singleton import Singleton
from .threads import BaseThread


class Settings(Singleton):
    HOSTNAME = os.uname()[1]
    JSON_FILENAME = "/mnt/microsd/settings.json" if HOSTNAME == "seedsigner-os" else "settings.json"
    microsd_in_use = False
        
    @classmethod
    def get_instance(cls):
        # This is the only way to access the one and only instance
        if cls._instance is None:
            # Instantiate the one and only instance
            settings = cls.__new__(cls)
            cls._instance = settings

            settings._data = SettingsDefinition.get_defaults()

            # Read persistent settings file, if it exists
            settings.load()
            
            settings.microsd_detect_thread = SettingsMircoSDDetectThread()
            settings.microsd_detect_thread.start()

        return cls._instance

    def __str__(self):
        return json.dumps(self._data, indent=4)
    
    def load(self):
        # read settings file if it exists
        if os.path.exists(Settings.JSON_FILENAME):
            with open(Settings.JSON_FILENAME) as settings_file:
                self.update(json.load(settings_file), disable_missing_entries=False)

    def save(self):
        if self._data[SettingsConstants.SETTING__PERSISTENT_SETTINGS] == SettingsConstants.OPTION__ENABLED:
            # write out settings files
            with open(Settings.JSON_FILENAME, 'w') as settings_file:
                json.dump(self._data, settings_file, indent=4)

    def update(self, new_settings: dict, disable_missing_entries: bool = True):
        """
            * disable_missing_entries: The SettingsQR Generator omits any multiselect
                fields with zero selections or disabled Enabled/Disabled toggles. So if a
                field is missing, interpret it as such. But if this is set to False, keep
                the existing value for the field; most likely this is a new setting that
                the user may not have a value for when loading their persistent settings,
                in which case this would preserve the new field's default value.
        """
        for entry in SettingsDefinition.settings_entries:
            if entry.attr_name not in new_settings:
                if not disable_missing_entries:
                    # Setting is missing; insert default
                    new_settings[entry.attr_name] = entry.default_value
                
                elif entry.visibility == SettingsConstants.VISIBILITY__HIDDEN:
                    # Missing hidden values always get their default
                    new_settings[entry.attr_name] = entry.default_value

                elif entry.type == SettingsConstants.TYPE__MULTISELECT:
                    # Clear out the multiselect
                    new_settings[entry.attr_name] = []

                elif entry.type in SettingsConstants.ALL_ENABLED_DISABLED_TYPES:
                    # Set DISABLED for this missing setting
                    new_settings[entry.attr_name] = SettingsConstants.OPTION__DISABLED

            else:
                # Clean the incoming data, if necessary
                if entry.type == SettingsConstants.TYPE__MULTISELECT:
                    if type(new_settings[entry.attr_name]) == str:
                        # Break comma-separated SettingsQR input into List
                        new_settings[entry.attr_name] = new_settings[entry.attr_name].split(",")
                
                # TODO: If value is not in entry.selection_options...


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
            if os.path.exists(Settings.JSON_FILENAME):
                os.remove(self.JSON_FILENAME)
                print(f"Removed {self.JSON_FILENAME}")

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
        
class SettingsMircoSDDetectThread(BaseThread):
    def run(self):
        import socket
        import os, os.path
        import time
        
        if Settings.HOSTNAME == "seedsigner-os":
        
            if os.path.exists("/tmp/mdev_socket"):
                os.remove("/tmp/mdev_socket")
            
            server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            server.bind("/tmp/mdev_socket")
            while self.keep_running:
                server.listen(1)
                conn, addr = server.accept()
                data = conn.recv(1000) # 1000 bytes limit
                action = ""
                mount_dir = ""
                if data:
                    msg = data.decode("utf-8").strip().split(" ")
                    action = msg[0]
                    mount_dir = msg[1]
                    print(f"socket message: {action} {mount_dir}")
                conn.close()
                
                if action == "add":
                    # restore persistent settings back to defaults
                    entry = SettingsDefinition.get_settings_entry(SettingsConstants.SETTING__PERSISTENT_SETTINGS)
                    entry.selection_options = SettingsConstants.OPTIONS__ENABLED_DISABLED
                    entry.help_text = "Store Settings on SD card."
                    
                    # if Settings file exists (meaning persistent settings was previously enabled), write out current settings to disk
                    if os.path.exists(Settings.JSON_FILENAME):
                        # enable persistent settings first, then save
                        Settings.get_instance().set_value(
                            SettingsConstants.SETTING__PERSISTENT_SETTINGS,
                            SettingsConstants.OPTION__ENABLED
                        )
                        Settings.get_instance().save()
                        
                elif action == "remove":
                    #set persistent settings to disabled
                    Settings.get_instance().set_value(
                        SettingsConstants.SETTING__PERSISTENT_SETTINGS,
                        SettingsConstants.OPTION__DISABLED
                    )
                    entry = SettingsDefinition.get_settings_entry(SettingsConstants.SETTING__PERSISTENT_SETTINGS)
                    entry.selection_options = SettingsConstants.OPTIONS__ONLY_DISABLED
                    entry.help_text = "MicroSD card is removed"

