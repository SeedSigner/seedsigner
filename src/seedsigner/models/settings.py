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
            
            settings.microsd_detect_thread = MircoSDSettingsDetectThread()
            settings.microsd_detect_thread.start()

        return cls._instance


    def __str__(self):
        return json.dumps(self._data, indent=4)
    
    def load(self):
        Settings.microsd_in_use = True
        # seedsigner-os check if microsd is inserted and mount if not already mounted
        if Settings.HOSTNAME == "seedsigner-os":
            if os.path.exists("/dev/mmcblk0p1"):
                rc = subprocess.call("mount | grep /mnt/microsd", shell=True)
                if rc != 0:
                    subprocess.call("mkdir -p /mnt/microsd && mount /dev/mmcblk0p1 /mnt/microsd", shell=True)
                    
        # read settings file if it exists
        if os.path.exists(Settings.JSON_FILENAME):
            with open(Settings.JSON_FILENAME) as settings_file:
                self.update(json.load(settings_file), disable_missing_entries=False)
                
        # seedsigner-os umount microsd after writing out settings file
        if Settings.HOSTNAME == "seedsigner-os":
            if os.path.isdir("/mnt/microsd"):
                subprocess.call("umount /mnt/microsd; rm -rf /mnt/microsd", shell=True)
        Settings.microsd_in_use = False


    def save(self):
        if self._data[SettingsConstants.SETTING__PERSISTENT_SETTINGS] == SettingsConstants.OPTION__ENABLED:
            Settings.microsd_in_use = True
            # seedsinger-os mounting microsd prior to writing out settings file
            if Settings.HOSTNAME == "seedsigner-os":
                if subprocess.call("mount | grep /mnt/microsd", shell=True) != 0:
                    subprocess.call("mkdir -p /mnt/microsd && mount /dev/mmcblk0p1 /mnt/microsd", shell=True)
                    
            # write out settings files
            with open(Settings.JSON_FILENAME, 'w') as settings_file:
                json.dump(self._data, settings_file, indent=4)
                
            # seedsigner-os umount microsd after writing out settings file
            if Settings.HOSTNAME == "seedsigner-os":
                if os.path.isdir("/mnt/microsd"):
                    subprocess.call("umount /mnt/microsd; rm -rf /mnt/microsd", shell=True)
            Settings.microsd_in_use = False

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
            # seedsinger-os mounting microsd prior to removing settings file
            if Settings.HOSTNAME == "seedsigner-os":
                if subprocess.call("mount | grep /mnt/microsd", shell=True) != 0:
                    subprocess.call("mkdir -p /mnt/microsd && mount /dev/mmcblk0p1 /mnt/microsd", shell=True)
            if os.path.exists(Settings.JSON_FILENAME):
                os.remove(self.JSON_FILENAME)
                print(f"Removed {self.JSON_FILENAME}")
            # seedsigner-os umount microsd after writing out settings file
            if Settings.HOSTNAME == "seedsigner-os":
                if os.path.isdir("/mnt/microsd"):
                    subprocess.call("umount /mnt/microsd; rm -rf /mnt/microsd", shell=True)

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
        
class MircoSDSettingsDetectThread(BaseThread):
    def run(self):
        import time
        
        load_cnt = 0    # prevents failed loads from trying over and over
        removed_cnt = 0
        
        time.sleep(6.0) # delay loop start
        
        if Settings.HOSTNAME == "seedsigner-os":
            while self.keep_running:
                if Settings.microsd_in_use == False:
                    
                    # check if newly mounted and load settings file
                    if subprocess.call("mount | grep /mnt/microsd", shell=True) == 0:
                        if os.path.isdir("/mnt/microsd") and load_cnt < 1:
                            
                            # restore persistent settings back to defaults
                            entry = SettingsDefinition.get_settings_entry(SettingsConstants.SETTING__PERSISTENT_SETTINGS)
                            entry.selection_options = SettingsConstants.OPTIONS__ENABLED_DISABLED
                            entry.help_text = "Store Settings on SD card."
                            
                            # load settings
                            Settings.get_instance().load()
                            load_cnt += 1
                    else:
                        umount = 0
                        
                    # check if newly removed and disabled persistent settings
                    if not os.path.exists("/dev/mmcblk0p1"):
                        removed_cnt += 1
                        if removed_cnt == 1: # on first detection of SD removed, set persistent settings to disabled
                            Settings.get_instance().set_value(
                                SettingsConstants.SETTING__PERSISTENT_SETTINGS,
                                SettingsConstants.OPTION__DISABLED
                            )
                            entry = SettingsDefinition.get_settings_entry(SettingsConstants.SETTING__PERSISTENT_SETTINGS)
                            entry.selection_options = SettingsConstants.OPTIONS__ONLY_DISABLED
                            entry.help_text = "MicroSD card is removed"
                    else:
                        removed_cnt = 0
                    
                time.sleep(1.0)

