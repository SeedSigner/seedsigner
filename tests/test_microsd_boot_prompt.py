"""
Tests for the post-boot MicroSD removal prompt and its Advanced setting.
"""
from unittest.mock import MagicMock, patch

from base import BaseTest, FlowTest, FlowStep

from seedsigner.gui.screens.screen import RET_CODE__BACK_BUTTON, RET_CODE__SD_REMOVED, ButtonOption
from seedsigner.models.settings_definition import SettingsConstants, SettingsDefinition
from seedsigner.views.view import Destination, MainMenuView, RemoveMicroSDWarningView
from seedsigner.views import settings_views


class TestMicroSDBootPromptSetting(BaseTest):
    def test_setting_exists_and_defaults_enabled(self):
        entry = SettingsDefinition.get_settings_entry(SettingsConstants.SETTING__MICROSD_BOOT_PROMPT)
        assert entry is not None
        assert entry.visibility == SettingsConstants.VISIBILITY__ADVANCED
        assert entry.default_value == SettingsConstants.OPTION__ENABLED
        assert entry.category == SettingsConstants.CATEGORY__FEATURES

        assert (
            self.settings.get_value(SettingsConstants.SETTING__MICROSD_BOOT_PROMPT)
            == SettingsConstants.OPTION__ENABLED
        )

    def test_setting_can_be_disabled(self):
        self.settings.set_value(
            SettingsConstants.SETTING__MICROSD_BOOT_PROMPT,
            SettingsConstants.OPTION__DISABLED,
        )
        assert (
            self.settings.get_value(SettingsConstants.SETTING__MICROSD_BOOT_PROMPT)
            == SettingsConstants.OPTION__DISABLED
        )


class TestRemoveMicroSDWarningView(BaseTest):
    def test_already_removed_goes_to_main_menu(self):
        with patch("seedsigner.hardware.microsd.MicroSD.get_instance") as mock_get:
            microsd = MagicMock()
            microsd.is_inserted = False
            mock_get.return_value = microsd

            dest = RemoveMicroSDWarningView().run()
            assert isinstance(dest, Destination)
            assert dest.View_cls == MainMenuView
            assert dest.clear_history is True

    def test_skip_goes_to_main_menu(self):
        with patch("seedsigner.hardware.microsd.MicroSD.get_instance") as mock_get, patch.object(
            RemoveMicroSDWarningView, "run_screen", return_value=0
        ):
            microsd = MagicMock()
            microsd.is_inserted = True
            mock_get.return_value = microsd

            dest = RemoveMicroSDWarningView().run()
            assert dest.View_cls == MainMenuView
            assert dest.clear_history is True

    def test_sd_removed_during_screen_goes_to_main_menu(self):
        with patch("seedsigner.hardware.microsd.MicroSD.get_instance") as mock_get, patch.object(
            RemoveMicroSDWarningView,
            "run_screen",
            return_value=RET_CODE__SD_REMOVED,
        ):
            microsd = MagicMock()
            microsd.is_inserted = True
            mock_get.return_value = microsd

            dest = RemoveMicroSDWarningView().run()
            assert dest.View_cls == MainMenuView
            assert dest.clear_history is True


class TestMicroSDBootPromptFlow(FlowTest):
    def test_can_disable_boot_prompt_from_advanced_settings(self):
        """Settings → Advanced → MicroSD boot prompt → Disabled."""
        settings_entry = SettingsDefinition.get_settings_entry(
            SettingsConstants.SETTING__MICROSD_BOOT_PROMPT
        )

        self.run_sequence([
            FlowStep(MainMenuView, button_data_selection=MainMenuView.SETTINGS),
            FlowStep(
                settings_views.SettingsMenuView,
                button_data_selection=settings_views.SettingsMenuView.ADVANCED,
            ),
            FlowStep(
                settings_views.SettingsMenuView,
                button_data_selection=ButtonOption(settings_entry.display_name),
            ),
            FlowStep(
                settings_views.SettingsEntryUpdateSelectionView,
                button_data_selection=ButtonOption(
                    settings_entry.get_selection_option_display_name_by_value(
                        SettingsConstants.OPTION__DISABLED
                    )
                ),
            ),
            FlowStep(
                settings_views.SettingsEntryUpdateSelectionView,
                screen_return_value=RET_CODE__BACK_BUTTON,
            ),
            FlowStep(settings_views.SettingsMenuView),
        ])

        assert (
            self.settings.get_value(SettingsConstants.SETTING__MICROSD_BOOT_PROMPT)
            == SettingsConstants.OPTION__DISABLED
        )
