from base import BaseTest
from seedsigner.models.settings import Settings
from seedsigner.models.settings_definition import SettingsConstants


class TestSettings(BaseTest):
    
    def test_reset_settings(self):
        """ BaseTest.reset_settings() should wipe out any previous Settings changes """
        settings = Settings.get_instance()
        settings.set_value(SettingsConstants.SETTING__PERSISTENT_SETTINGS, SettingsConstants.OPTION__ENABLED)
        assert settings.get_value(SettingsConstants.SETTING__PERSISTENT_SETTINGS) == SettingsConstants.OPTION__ENABLED

        BaseTest.reset_settings()
        settings = Settings.get_instance()
        assert settings.get_value(SettingsConstants.SETTING__PERSISTENT_SETTINGS) == SettingsConstants.OPTION__DISABLED
