from mock import MagicMock
from typing import Type

# Must import this before any seedsigner imports
from base import FlowTest, FlowStep

from seedsigner.models import SettingsDefinition
from seedsigner.models.settings_definition import SettingsConstants
from seedsigner.gui.screens.screen import RET_CODE__BACK_BUTTON
from seedsigner.views.view import Destination, MainMenuView, View
from seedsigner.views import settings_views



class TestSettingsFlows(FlowTest):

    def test_persistent_settings(self):
        """ Basic flow from MainMenuView to enable/disable persistent settings """
        # Which option are we testing?
        settings_entry = SettingsDefinition.get_settings_entry(SettingsConstants.SETTING__PERSISTENT_SETTINGS)

        destination = self.run_sequence(
            Destination(MainMenuView),
            sequence=[
                FlowStep(
                    button_data_selection=MainMenuView.SETTINGS
                ),
                FlowStep(
                    expected_view=settings_views.SettingsMenuView,
                    button_data_selection=settings_entry.display_name
                ),
                FlowStep(
                    expected_view=settings_views.SettingsEntryUpdateSelectionView,
                    button_data_selection=settings_entry.get_selection_option_display_name_by_value(SettingsConstants.OPTION__ENABLED),
                ),
                FlowStep(
                    expected_view=settings_views.SettingsEntryUpdateSelectionView,
                    screen_return_value=RET_CODE__BACK_BUTTON
                )
            ]
        )
        assert destination.View_cls == settings_views.SettingsMenuView


    def test_multiselect(self):
        """ Multiselect Settings options should stay in-place; requires BACK to exit. """
        # Which option are we testing?
        settings_entry = SettingsDefinition.get_settings_entry(SettingsConstants.SETTING__COORDINATORS)

        destination = self.run_sequence(
            Destination(MainMenuView),
            sequence=[
                FlowStep(
                    button_data_selection=MainMenuView.SETTINGS
                ),
                FlowStep(
                    expected_view=settings_views.SettingsMenuView,
                    button_data_selection=settings_entry.display_name
                ),
                FlowStep(
                    expected_view=settings_views.SettingsEntryUpdateSelectionView,
                    screen_return_value=0,          # select/deselect first option
                ),
                FlowStep(
                    expected_view=settings_views.SettingsEntryUpdateSelectionView,
                    screen_return_value=1,          # select/deselect second option
                ),
                FlowStep(
                    expected_view=settings_views.SettingsEntryUpdateSelectionView,
                    screen_return_value=1,          # select/deselect second option
                ),
                FlowStep(
                    expected_view=settings_views.SettingsEntryUpdateSelectionView,
                    screen_return_value=RET_CODE__BACK_BUTTON,  # BACK to exit
                ),
            ]
        )
        assert destination.View_cls == settings_views.SettingsMenuView


    def test_io_test(self):
        """ Basic flow from MainMenuView to I/O Test View """
        destination = self.run_sequence(
            Destination(MainMenuView),
            sequence=[
                FlowStep(
                    button_data_selection=MainMenuView.SETTINGS,
                ),
                FlowStep(
                    expected_view=settings_views.SettingsMenuView,
                    button_data_selection=settings_views.SettingsMenuView.IO_TEST
                ),
                FlowStep(
                    expected_view=settings_views.IOTestView,
                    # ret value is ignored
                ),
            ]
        )
        # Exiting IOTestView should return us to the main SettingsMenuView
        assert destination.View_cls == settings_views.SettingsMenuView


    def test_donate(self):
        """ Basic flow from MainMenuView to Donate View """        
        destination = self.run_sequence(
            Destination(MainMenuView),
            sequence=[
                FlowStep(
                    button_data_selection=MainMenuView.SETTINGS,
                ),
                FlowStep(
                    expected_view=settings_views.SettingsMenuView,
                    button_data_selection=settings_views.SettingsMenuView.DONATE
                ),
                FlowStep(
                    expected_view=settings_views.DonateView,
                    # ret value is ignored
                ),
            ]
        )
        # Exiting IOTestView should return us to the main SettingsMenuView
        assert destination.View_cls == settings_views.SettingsMenuView
