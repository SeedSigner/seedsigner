import json
import pytest

from base import BaseTest

from seedsigner.models.settings import InvalidSettingsQRData, Settings
from seedsigner.models.settings_definition import SettingsConstants, SettingsDefinition



class TestSettings(BaseTest):
    @classmethod
    def setup_class(cls):
        super().setup_class()
        cls.settings = Settings.get_instance()


    def test_reset_settings(self):
        """ BaseTest.reset_settings() should wipe out any previous Settings changes """
        settings_entry = SettingsDefinition.get_settings_entry(SettingsConstants.SETTING__PERSISTENT_SETTINGS)
        assert settings_entry.default_value == SettingsConstants.OPTION__DISABLED

        # Change the setting from its default
        settings = Settings.get_instance()
        settings.set_value(SettingsConstants.SETTING__PERSISTENT_SETTINGS, SettingsConstants.OPTION__ENABLED)
        assert settings.get_value(SettingsConstants.SETTING__PERSISTENT_SETTINGS) == SettingsConstants.OPTION__ENABLED

        BaseTest.reset_settings()
        settings = Settings.get_instance()
        assert settings.get_value(SettingsConstants.SETTING__PERSISTENT_SETTINGS) == SettingsConstants.OPTION__DISABLED


    def test_settings_defaults(self):
        """ Settings should initialize to their default values """
        BaseTest.reset_settings()
        settings = Settings.get_instance()
        for settings_entry in SettingsDefinition.get_settings_entries():
            assert settings.get_value(settings_entry.attr_name) == settings_entry.default_value


    def test_load_persistent_settings(self):
        """ Settings should load previously saved persistent settings from disk, if any
        exist. """
        # Initial Settings will start with defaults
        settings = Settings.get_instance()

        # Enable persistent settings and make another change
        settings.set_value(SettingsConstants.SETTING__PERSISTENT_SETTINGS, SettingsConstants.OPTION__ENABLED)

        assert settings.get_value(SettingsConstants.SETTING__QR_DENSITY) != SettingsConstants.DENSITY__HIGH
        settings.set_value(SettingsConstants.SETTING__QR_DENSITY, SettingsConstants.DENSITY__HIGH)

        # Hold on to the settings.json content
        settings_json = None
        with open(Settings.SETTINGS_FILENAME) as settings_file:
            settings_json = json.loads(settings_file.read())

        # Now wipe out the Settings singleton
        BaseTest.reset_settings()

        # This also deletes settings.json, so recreate it
        with open(Settings.SETTINGS_FILENAME, "w") as settings_file:
            settings_file.write(json.dumps(settings_json))

        # Now instantiate the Settings singleton again; it should load from disk
        settings = Settings.get_instance()

        # Persistent setting change should have survived
        assert settings.get_value(SettingsConstants.SETTING__QR_DENSITY) == SettingsConstants.DENSITY__HIGH


    def test_load_empty_multiselect_settings(self):
        """ Empty multiselect settings should load defaults. """
        # Initial Settings will start with defaults
        settings = Settings.get_instance()

        # Enable persistent settings to write settings.json to disk
        settings.set_value(SettingsConstants.SETTING__PERSISTENT_SETTINGS, SettingsConstants.OPTION__ENABLED)

        # Hold on to the settings.json content
        settings_dict = None
        with open(Settings.SETTINGS_FILENAME) as settings_file:
            settings_dict = json.loads(settings_file.read())

        def _verify_defaults_loaded(attr_name: str):
            # Verify that the multiselect setting has loaded its defaults
            settings = Settings.get_instance()
            cur_setting_value = settings.get_value(attr_name)
            assert cur_setting_value == SettingsDefinition.get_settings_entry(attr_name).default_value

        # Alter the settings to test against various empty values
        for empty_value in ["", ",", [], None]:
            settings_dict[SettingsConstants.SETTING__SIG_TYPES] = empty_value
            settings.update(settings_dict)
            _verify_defaults_loaded(SettingsConstants.SETTING__SIG_TYPES)

        # One last test: remove the multiselect setting entirely
        del settings_dict[SettingsConstants.SETTING__SIG_TYPES]
        settings.update(settings_dict)
        _verify_defaults_loaded(SettingsConstants.SETTING__SIG_TYPES)



class SettingsQRBase(BaseTest):
    """
    Reusable base test class for testing SettingsQR data.
    """
    def setup_method(self):
        super().setup_method()
        settingsqr_dict = SettingsDefinition.get_defaults(use_abbreviated_name=True, skip_hidden=True)

        # Build baseline SettingsQR config based on defaults
        self.settingsqr_prefix = "settings::v1"
        self.settingsqr_default_attrs_str = ""
        for abbreviated_attr_name, value in settingsqr_dict.items():
            if isinstance(value, list):
                value_str = ",".join(value)
            else:
                value_str = str(value)
            self.settingsqr_default_attrs_str += f" {abbreviated_attr_name}={value_str}"



class TestSettingsQRParser(SettingsQRBase):
    def test_parse_settingsqr_data(self):
        """
        SettingsQR parser should successfully parse a valid settingsqr input string and
        return the resulting config_name and formatted settings_update_dict.
        """
        settings_name = "Test SettingsQR"
        settingsqr_data = f"""{self.settingsqr_prefix} name={ settings_name.replace(" ", "_") } {self.settingsqr_default_attrs_str}"""

        # First explicitly set settings that differ from the settingsqr_data
        self.settings.set_value(SettingsConstants.SETTING__COMPACT_SEEDQR, SettingsConstants.OPTION__DISABLED)
        self.settings.set_value(SettingsConstants.SETTING__DIRE_WARNINGS, SettingsConstants.OPTION__DISABLED)
        self.settings.set_value(SettingsConstants.SETTING__XPUB_QR_FORMAT, [SettingsConstants.XPUB_QR_FORMAT__STATIC, SettingsConstants.XPUB_QR_FORMAT__SPECTER_LEGACY])

        # Now parse the settingsqr_data
        config_name, settings_update_dict = Settings.parse_settingsqr(settingsqr_data)
        assert config_name == settings_name
        self.settings.update(new_settings=settings_update_dict)

        # Now verify that the settings were updated correctly
        assert self.settings.get_value(SettingsConstants.SETTING__COMPACT_SEEDQR) == SettingsConstants.OPTION__ENABLED
        assert self.settings.get_value(SettingsConstants.SETTING__DIRE_WARNINGS) == SettingsConstants.OPTION__ENABLED

        xpub_qr_formats = self.settings.get_value(SettingsConstants.SETTING__XPUB_QR_FORMAT)
        assert SettingsConstants.XPUB_QR_FORMAT__UR_CRYPTO_ACCOUNT in xpub_qr_formats
        assert SettingsConstants.XPUB_QR_FORMAT__STATIC in xpub_qr_formats
        assert SettingsConstants.XPUB_QR_FORMAT__SPECTER_LEGACY not in xpub_qr_formats
    

    def test_settingsqr_version(self):
        """ SettingsQR parser should accept SettingsQR v1 and reject any others """
        settingsqr_data = f"{self.settingsqr_prefix} {self.settingsqr_default_attrs_str}"
        config_name, settings_update_dict = Settings.parse_settingsqr(settingsqr_data)

        # Accepts update with no Exceptions
        self.settings.update(new_settings=settings_update_dict)

        settingsqr_data = f"settings::v2 {self.settingsqr_default_attrs_str}"
        with pytest.raises(InvalidSettingsQRData) as e:
            Settings.parse_settingsqr(settingsqr_data)
        assert "Unsupported SettingsQR version" in str(e.value)
    
        # Should also fail if version omitted
        settingsqr_data = f"settings {self.settingsqr_default_attrs_str}"
        with pytest.raises(InvalidSettingsQRData) as e:
            Settings.parse_settingsqr(settingsqr_data)

        # And if "settings" is omitted entirely
        settingsqr_data = self.settingsqr_default_attrs_str
        with pytest.raises(InvalidSettingsQRData) as e:
            Settings.parse_settingsqr(settingsqr_data)


    def test_settingsqr_ignores_unrecognized_setting(self):
        """ SettingsQR parser should ignore unrecognized settings """
        settings_entry = SettingsDefinition.get_settings_entry(SettingsConstants.SETTING__NETWORK)
        unknown_attr = "favorite_food"
        settingsqr_data = f"{self.settingsqr_prefix} {unknown_attr}=bacon {settings_entry.abbreviated_name}={settings_entry.default_value}"
        config_name, settings_update_dict = Settings.parse_settingsqr(settingsqr_data)

        assert unknown_attr not in settings_update_dict
        assert settings_entry.attr_name in settings_update_dict

        # Accepts update with no Exceptions
        self.settings.update(new_settings=settings_update_dict)


    def test_settingsqr_fails_unrecognized_option(self):
        """ SettingsQR parser should fail if a settings has an unrecognized option """
        settings_entry = SettingsDefinition.get_settings_entry(SettingsConstants.SETTING__NETWORK)
        settingsqr_data = f"{self.settingsqr_prefix} {settings_entry.abbreviated_name}=fake_value"
        with pytest.raises(InvalidSettingsQRData) as e:
            Settings.parse_settingsqr(settingsqr_data)
        assert settings_entry.attr_name in str(e.value)


    def test_settingsqr_fails_empty_values(self):
        """ SettingsQR parser should fail if a setting is empty """
        settingsqr_data = "settings::v1 persistent=D sigs= camera=180"
        with pytest.raises(InvalidSettingsQRData) as e:
            Settings.parse_settingsqr(settingsqr_data)
        assert "sigs" in str(e.value)


    def test_settingsqr_parses_line_break_separators(self):
        """ SettingsQR parser should read line breaks as acceptable separators """
        attrs_with_line_breaks = self.settingsqr_default_attrs_str.replace(' ', '\n')
        settingsqr_data = f"{self.settingsqr_prefix}\n{attrs_with_line_breaks}"
        config_name, settings_update_dict = Settings.parse_settingsqr(settingsqr_data)

        assert len(settings_update_dict.keys()) == self.settingsqr_default_attrs_str.count('=')

        # Accepts update with no Exceptions
        self.settings.update(new_settings=settings_update_dict)
