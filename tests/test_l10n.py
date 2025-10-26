from gettext import gettext as _

from base import BaseTest
from seedsigner.gui.screens.screen import ButtonOption
from seedsigner.helpers.l10n import mark_for_translation as _mft
from seedsigner.models.settings import Settings
from seedsigner.models.settings_definition import SettingsConstants
from seedsigner.views.view import MainMenuView



class TestGettext(BaseTest):
    def test_english_as_default(self):
        # Key is available in other languages, but we get English back
        assert _("Home") == "Home"

    def test_missing_key_returns_english_key(self):
        test_str = "This is not in our translation library"
        assert _(test_str) == test_str
    

    def test_basic_spanish(self):
        settings = Settings.get_instance()
        settings.set_value(SettingsConstants.SETTING__LOCALE, SettingsConstants.LOCALE__SPANISH)
        assert _("Home") != "Home"


    def test_locale_changes(self):
        settings = Settings.get_instance()

        settings.set_value(SettingsConstants.SETTING__LOCALE, SettingsConstants.LOCALE__SPANISH)
        spanish_str = _("Home")

        settings.set_value(SettingsConstants.SETTING__LOCALE, SettingsConstants.LOCALE__ENGLISH)
        assert spanish_str != _("Home")
        assert _("Home") == "Home"



class TestButtonOption(BaseTest):
    def test_english_key_not_translated(self):
        """ ButtonOption should always return its English key, regardless of current locale setting. """
        button_option = ButtonOption("Home")
        settings = Settings.get_instance()
        settings.set_value(SettingsConstants.SETTING__LOCALE, SettingsConstants.LOCALE__SPANISH)

        assert button_option.button_label == "Home"

        brand_new_button_option = ButtonOption("Tools")
        assert brand_new_button_option.button_label == "Tools"
    

    def test_class_level_button_option_english_key_not_translated(self):
        settings = Settings.get_instance()
        settings.set_value(SettingsConstants.SETTING__LOCALE, SettingsConstants.LOCALE__SPANISH)

        class FooClass:
            HOME = ButtonOption("Home")
        
        assert FooClass.HOME.button_label == "Home"


    def test_gettext_translates_class_level_button_option(self):
        settings = Settings.get_instance()
        settings.set_value(SettingsConstants.SETTING__LOCALE, SettingsConstants.LOCALE__SPANISH)

        class BarClass:
            HOME = ButtonOption("Home")

        assert _(BarClass.HOME.button_label) != "Home"



class TestMarkForTranslation(BaseTest):
    def test_english_key_not_translated(self):
        """ _mft() should always return its English key, regardless of current locale setting. """
        mft_attr = _mft("Home")
        settings = Settings.get_instance()
        settings.set_value(SettingsConstants.SETTING__LOCALE, SettingsConstants.LOCALE__SPANISH)

        assert mft_attr == "Home"

        brand_new_mft_attr = _mft("Tools")
        assert brand_new_mft_attr == "Tools"


    def test_class_level_mft_attr_english_key_not_translated(self):
        settings = Settings.get_instance()
        settings.set_value(SettingsConstants.SETTING__LOCALE, SettingsConstants.LOCALE__SPANISH)

        class FooClass:
            home = _mft("Home")
        
        assert FooClass.home == "Home"


    def test_gettext_translates_class_level_mft_attr(self):
        settings = Settings.get_instance()
        settings.set_value(SettingsConstants.SETTING__LOCALE, SettingsConstants.LOCALE__SPANISH)

        class BarClass:
            home = _mft("Home")

        assert _(BarClass.home) != "Home"
