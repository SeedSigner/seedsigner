import os

# Must import test base before the Controller
from base import FlowTest, FlowStep

from seedsigner.models import SettingsDefinition
from seedsigner.models.settings import Settings
from seedsigner.models.settings_definition import SettingsConstants
from seedsigner.gui.screens.screen import RET_CODE__BACK_BUTTON
from seedsigner.views.view import MainMenuView
from seedsigner.views import settings_views



class TestSettingsFlows(FlowTest):

    def test_persistent_settings(self):
        """ Basic flow from MainMenuView to enable/disable persistent settings """
        # Which option are we testing?
        settings_entry = SettingsDefinition.get_settings_entry(SettingsConstants.SETTING__PERSISTENT_SETTINGS)

        # No settings file should exist before we enable persistent settings
        assert os.path.exists(Settings.SETTINGS_FILENAME) == False

        self.run_sequence([
            FlowStep(MainMenuView, button_data_selection=MainMenuView.SETTINGS),
            FlowStep(settings_views.SettingsMenuView, button_data_selection=settings_entry.display_name),
            FlowStep(settings_views.SettingsEntryUpdateSelectionView, button_data_selection=settings_entry.get_selection_option_display_name_by_value(SettingsConstants.OPTION__ENABLED)),
            FlowStep(settings_views.SettingsEntryUpdateSelectionView, screen_return_value=RET_CODE__BACK_BUTTON),
            FlowStep(settings_views.SettingsMenuView),
        ])

        # Settings file should now exist
        assert os.path.exists(Settings.SETTINGS_FILENAME) == True


    def test_multiselect(self):
        """ Multiselect Settings options should stay in-place; requires BACK to exit. """
        # Which option are we testing?
        settings_entry = SettingsDefinition.get_settings_entry(SettingsConstants.SETTING__COORDINATORS)

        self.run_sequence([
            FlowStep(MainMenuView, button_data_selection=MainMenuView.SETTINGS),
            FlowStep(settings_views.SettingsMenuView, button_data_selection=settings_entry.display_name),
            FlowStep(settings_views.SettingsEntryUpdateSelectionView, screen_return_value=0),  # select/deselect first option
            FlowStep(settings_views.SettingsEntryUpdateSelectionView, screen_return_value=1),  # select/deselect second option
            FlowStep(settings_views.SettingsEntryUpdateSelectionView, screen_return_value=1),  # select/deselect second option
            FlowStep(settings_views.SettingsEntryUpdateSelectionView, screen_return_value=RET_CODE__BACK_BUTTON),  # BACK to exit
            FlowStep(settings_views.SettingsMenuView),
        ])


    def test_io_test(self):
        """ Basic flow from MainMenuView to I/O Test View """
        self.run_sequence([
            FlowStep(MainMenuView, button_data_selection=MainMenuView.SETTINGS),
            FlowStep(settings_views.SettingsMenuView, button_data_selection=settings_views.SettingsMenuView.IO_TEST),
            FlowStep(settings_views.IOTestView),
            FlowStep(settings_views.SettingsMenuView),
        ])


    def test_donate(self):
        """ Basic flow from MainMenuView to Donate View """        
        self.run_sequence([
            FlowStep(MainMenuView, button_data_selection=MainMenuView.SETTINGS),
            FlowStep(settings_views.SettingsMenuView, button_data_selection=settings_views.SettingsMenuView.DONATE),
            FlowStep(settings_views.DonateView),
            FlowStep(settings_views.SettingsMenuView),
        ])
