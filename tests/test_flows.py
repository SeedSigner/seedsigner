import pytest

# Must import test base before the Controller
from base import FlowTest, FlowStep, FlowTestUnexpectedViewException, FlowTestInvalidButtonDataSelectionException, FlowTestRunScreenNotExecutedException

from seedsigner.controller import Controller
from seedsigner.gui.screens.screen import RET_CODE__BACK_BUTTON, RET_CODE__POWER_BUTTON
from seedsigner.models.seed import Seed
from seedsigner.models.settings_definition import SettingsConstants
from seedsigner.views.seed_views import SeedBackupView, SeedMnemonicEntryView, SeedOptionsView, SeedWordsWarningView
from seedsigner.views.view import MainMenuView, PowerOptionsView, UnhandledExceptionView
from seedsigner.views.tools_views import ToolsMenuView, ToolsCalcFinalWordNumWordsView



class TestFlowTest(FlowTest):

    def test_simple_flow(self):
        """
        Basic test to ensure the FlowTest can flow through a sequence of Views and
        terminate via the StopControllerCommand.
        """
        self.run_sequence([
            FlowStep(MainMenuView, button_data_selection=MainMenuView.TOOLS),
            FlowStep(ToolsMenuView, button_data_selection=ToolsMenuView.KEYBOARD),
            FlowStep(ToolsCalcFinalWordNumWordsView, button_data_selection=ToolsCalcFinalWordNumWordsView.TWELVE),
            FlowStep(SeedMnemonicEntryView),
        ])


    def test_FlowTestUnexpectedViewException(self):
        """
        Ensure that the FlowTest will raise a FlowTestUnexpectedViewException if the next
        View in the sequence is not the expected View.
        """
        with pytest.raises(FlowTestUnexpectedViewException):
            self.run_sequence([
                FlowStep(MainMenuView, button_data_selection=RET_CODE__POWER_BUTTON),
                FlowStep(ToolsMenuView),  # <-- Wrong target View! Should raise an AssertionError.
            ])


    def test_FlowTestInvalidButtonDataSelectionException(self):
        """
        Ensure that the FlowTest will raise a FlowTestUnexpectedViewException if the
        specified button_data_selection in invalid.
        """
        with pytest.raises(FlowTestInvalidButtonDataSelectionException):
            self.run_sequence([
            FlowStep(MainMenuView, button_data_selection="this is not a real button option!"),
            ])


    def test_FlowTestRunScreenNotExecutedException(self):
        """
        Ensure that the FlowTest will raise a FlowTestRunScreenNotExecutedException if the next
        View in the sequence doesn't call its View.run_screen().
        """
        # Disable dire warnings so that the SeedWordsWarningView won't execute its run_screen()
        self.settings.set_value(SettingsConstants.SETTING__DIRE_WARNINGS, SettingsConstants.OPTION__DISABLED)
        self.controller.storage.set_pending_seed(Seed(mnemonic=["bacon"] * 24))
        self.controller.storage.finalize_pending_seed()

        with pytest.raises(FlowTestRunScreenNotExecutedException):
            self.run_sequence(
                initial_destination_view_args=dict(seed_num=0),
                sequence=[
                    FlowStep(SeedOptionsView, button_data_selection=SeedOptionsView.BACKUP),
                    FlowStep(SeedBackupView, button_data_selection=SeedBackupView.VIEW_WORDS),
                    FlowStep(SeedWordsWarningView, screen_return_value=0),
                ],
            )


    def test_before_run_executes(self):
        """
        Ensure that the FlowTest can execute a function before running a View.
        """
        # TODO
        pass


    def test_back_button_flow(self):
        """
        Ensure that the FlowTest works correctly with the Controller and its BackStack.
        """
        self.run_sequence([
            FlowStep(MainMenuView, screen_return_value=RET_CODE__POWER_BUTTON),
            FlowStep(PowerOptionsView, screen_return_value=RET_CODE__BACK_BUTTON),
            FlowStep(MainMenuView),
        ])
    

    def test_initial_destination(self):
        """
        Ensure that the FlowTest can start from a View other than MainMenuView.
        """
        # Don't have to start at the MainMenuView; can jump straight in
        self.run_sequence([
            FlowStep(ToolsCalcFinalWordNumWordsView),
        ])

        # And again, but this time with a View that requires input view_args
        self.reset_controller()
        self.controller = Controller.get_instance()

        # Load a seed into the Controller
        seed = Seed(mnemonic=["abandon "* 11 + "about"])
        self.controller.storage.set_pending_seed(seed)
        self.controller.storage.finalize_pending_seed()

        self.run_sequence(
            initial_destination_view_args=dict(seed_num=0),
            sequence=[
                FlowStep(SeedOptionsView, button_data_selection=SeedOptionsView.BACKUP),
                FlowStep(SeedBackupView),
            ]
        )
    

    def test_raise_exception_via_screen_return_value(self):
        """
        Ensure that the FlowTest can raise an exception via the screen_return_value.
        """
        # A generic Exception should be caught by the Controller and routed to the
        # UnhandledExceptionView.
        self.run_sequence([
            FlowStep(MainMenuView, screen_return_value=Exception("Test exception")),
            FlowStep(UnhandledExceptionView),
        ])

