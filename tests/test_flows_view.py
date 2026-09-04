from unittest.mock import patch

# Must import test base before the Controller
from base import FlowTest, FlowStep

from seedsigner.gui.screens.screen import RET_CODE__POWER_BUTTON, RET_CODE__BACK_BUTTON
from seedsigner.hardware.camera import CameraConnectionError
from seedsigner.models.settings import Settings
from seedsigner.views.scan_views import ScanView, ScanInvalidQRTypeView
from seedsigner.views.tools_views import ToolsCalcFinalWordNumWordsView, ToolsMenuView
from seedsigner.views.view import CameraConnectionErrorView, MainMenuView, NotYetImplementedView, PowerOptionsView, PowerOffView, RestartView, UnhandledExceptionView, View



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


    def test__camera_connection_error__flow(self):
        """
        Simulate a camera connection error and ensure that we get the
        CameraConnectionErrorView.
        """
        # Force a camera exception during `ScanView.run()`
        with patch('seedsigner.views.scan_views.ScanView.run') as mock_run:
            mock_run.side_effect = CameraConnectionError()

            self.run_sequence([
                FlowStep(MainMenuView, button_data_selection=MainMenuView.SCAN),
                FlowStep(ScanView),
                FlowStep(UnhandledExceptionView, is_redirect=True),
                FlowStep(CameraConnectionErrorView),
                FlowStep(MainMenuView),
            ])


    def test_invalid_qr_main_menu_flow(self):
        """
        Scanning an invalid QR from Main Menu should give the user the option
        to go back and retry or exit the flow and return to the Main Menu
        """

        def load_invalid_qr(view: ScanView):
            view.decoder.add_data("this text will not make sense to the decoder")

        # Sequence 1: User clicks on "Return to Main Menu"
        self.run_sequence([
            FlowStep(MainMenuView, button_data_selection=MainMenuView.SCAN),
            FlowStep(ScanView, before_run=load_invalid_qr),
            FlowStep(ScanInvalidQRTypeView),
            FlowStep(MainMenuView)
        ])

        # Sequence 2: User clicks on BACK, returns to Scan View for a rescan
        self.run_sequence([
            FlowStep(MainMenuView, button_data_selection=MainMenuView.SCAN),
            FlowStep(ScanView, before_run=load_invalid_qr),
            FlowStep(ScanInvalidQRTypeView, screen_return_value=RET_CODE__BACK_BUTTON),
            FlowStep(ScanView)
        ])
