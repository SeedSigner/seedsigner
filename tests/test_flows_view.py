from unittest.mock import patch

# Must import test base before the Controller
from base import FlowTest, FlowStep

from seedsigner.gui.screens.screen import RET_CODE__POWER_BUTTON
from seedsigner.models.settings import Settings
from seedsigner.views.tools_views import ToolsCalcFinalWordNumWordsView, ToolsMenuView
from seedsigner.views.view import MainMenuView, NotYetImplementedView, PowerOptionsView, PowerOffView, RestartView, UnhandledExceptionView, View



class TestViewFlows(FlowTest):

    def test_restart_flow(self):
        """
        Basic flow from MainMenuView to RestartView
        """
        with patch('seedsigner.views.view.RestartView.DoResetThread'):
            self.run_sequence([
                FlowStep(MainMenuView, screen_return_value=RET_CODE__POWER_BUTTON),
                FlowStep(PowerOptionsView, button_data_selection=PowerOptionsView.RESET),
                FlowStep(RestartView),
            ])


    def test_power_off_flow(self):
        """
        Basic flow from MainMenuView to PowerOffView
        """
        Settings.HOSTNAME = Settings.SEEDSIGNER_OS
        self.run_sequence([
            FlowStep(MainMenuView, screen_return_value=RET_CODE__POWER_BUTTON),
            FlowStep(PowerOptionsView, button_data_selection=PowerOptionsView.POWER_OFF),
            FlowStep(PowerOffView),  # returns BackStackView
            FlowStep(PowerOptionsView),
        ])


    def test_not_yet_implemented_flow(self):
        """
        Run an incomplete View that returns None and ensure that we get the NotYetImplementedView
        """
        class IncompleteView(View):
            def run(self):
                self.run_screen(None)
                return None

        self.run_sequence([
            FlowStep(IncompleteView),
            FlowStep(NotYetImplementedView),
            FlowStep(MainMenuView),
        ])


    def test_unhandled_exception_flow(self):
        """
        Basic flow from any arbitrary View to the UnhandledExceptionView
        """
        self.run_sequence([
            FlowStep(MainMenuView, button_data_selection=MainMenuView.TOOLS),
            FlowStep(ToolsMenuView, button_data_selection=ToolsMenuView.KEYBOARD),
            FlowStep(ToolsCalcFinalWordNumWordsView, screen_return_value=Exception("Test exception")),  # <-- force an exception
            FlowStep(UnhandledExceptionView),
            FlowStep(MainMenuView),
        ])
