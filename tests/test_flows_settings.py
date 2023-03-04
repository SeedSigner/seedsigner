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
        settings_entries = SettingsDefinition.get_settings_entries()
        nth_entry = [s.attr_name for s in settings_entries].index(SettingsConstants.SETTING__PERSISTENT_SETTINGS)

        settings_entry = SettingsDefinition.get_settings_entry(SettingsConstants.SETTING__PERSISTENT_SETTINGS)

        def mock_settingsmenuview_screen(view: Type[View]):
            # SettingsMenuView reaches into its `self.screen` so we need to mock it out
            view.screen = MagicMock()
        
        destination = self.run_sequence(
            Destination(MainMenuView),
            sequence=[
                FlowStep(
                    screen_return_value=3,          # ret SETTINGS
                ),
                FlowStep(
                    expected_view=settings_views.SettingsMenuView,
                    run_before=mock_settingsmenuview_screen,
                    screen_return_value=nth_entry,  # ret persistent settings
                ),
                FlowStep(
                    expected_view=settings_views.SettingsEntryUpdateSelectionView,
                    screen_return_value=[s[0] for s in settings_entry.selection_options].index(SettingsConstants.OPTION__ENABLED),
                ),
            ]
        )
        assert destination.View_cls == settings_views.SettingsMenuView


    def test_multiselect(self):
        """ Multiselect Settings options should stay in-place; requires BACK to exit. """
        # Which option are we testing?
        settings_entry = SettingsDefinition.get_settings_entry(SettingsConstants.SETTING__COORDINATORS)
        nth_entry = SettingsDefinition.get_settings_entries().index(settings_entry)

        def mock_settingsmenuview_screen(view: Type[View]):
            # SettingsMenuView reaches into its `self.screen` so we need to mock it out
            view.screen = MagicMock()

        def disable_recursion(view: Type[View]):
            # The recursion in SettingsEntryUpdateSelectionView for multiselect settings
            # won't work with our FlowTest sequence structure.
            view.is_test = True

        destination = self.run_sequence(
            Destination(MainMenuView),
            sequence=[
                FlowStep(
                    screen_return_value=3,          # ret SETTINGS
                ),
                FlowStep(
                    expected_view=settings_views.SettingsMenuView,
                    run_before=mock_settingsmenuview_screen,
                    screen_return_value=nth_entry,  # ret Coordinator software
                ),
                FlowStep(
                    expected_view=settings_views.SettingsEntryUpdateSelectionView,
                    run_before=disable_recursion,
                    screen_return_value=0,          # select/deselect first option
                ),
                FlowStep(
                    expected_view=settings_views.SettingsEntryUpdateSelectionView,
                    run_before=disable_recursion,
                    screen_return_value=1,          # select/deselect second option
                ),
                FlowStep(
                    expected_view=settings_views.SettingsEntryUpdateSelectionView,
                    run_before=disable_recursion,
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
        # I/O Test will be the nth_entry after we include the submenu to "Advanced"
        nth_entry = len(SettingsDefinition.get_settings_entries()) + 1

        def mock_settingsmenuview_screen(view: Type[View]):
            # SettingsMenuView reaches into its `self.screen` so we need to mock it out
            view.screen = MagicMock()
        
        destination = self.run_sequence(
            Destination(MainMenuView),
            sequence=[
                FlowStep(
                    screen_return_value=3,          # ret SETTINGS
                ),
                FlowStep(
                    expected_view=settings_views.SettingsMenuView,
                    run_before=mock_settingsmenuview_screen,
                    screen_return_value=nth_entry,  # ret I/O Test
                ),
                FlowStep(
                    expected_view=settings_views.IOTestView,
                    screen_return_value=None,       # ret value is ignored
                ),
            ]
        )
        # Exiting IOTestView should return us to the main SettingsMenuView
        assert destination.View_cls == settings_views.SettingsMenuView


    def test_donate(self):
        """ Basic flow from MainMenuView to Donate View """
        # DonateView will be the nth_entry after we include the submenu to "Advanced"
        # and the I/O Test
        nth_entry = len(SettingsDefinition.get_settings_entries()) + 2

        def mock_settingsmenuview_screen(view: Type[View]):
            # SettingsMenuView reaches into its `self.screen` so we need to mock it out
            view.screen = MagicMock()
        
        destination = self.run_sequence(
            Destination(MainMenuView),
            sequence=[
                FlowStep(
                    screen_return_value=3,          # ret SETTINGS
                ),
                FlowStep(
                    expected_view=settings_views.SettingsMenuView,
                    run_before=mock_settingsmenuview_screen,
                    screen_return_value=nth_entry,  # ret Donate
                ),
                FlowStep(
                    expected_view=settings_views.DonateView,
                    screen_return_value=None,       # ret value is ignored
                ),
            ]
        )
        # Exiting IOTestView should return us to the main SettingsMenuView
        assert destination.View_cls == settings_views.SettingsMenuView
