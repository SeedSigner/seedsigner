import pytest

# Must import test base before the Controller
from base import FlowTest, FlowStep, FlowTestMissingRedirectException, FlowTestUnexpectedRedirectException, FlowTestUnexpectedViewException, FlowTestInvalidButtonDataSelectionException, FlowTestInvalidButtonDataInstanceTypeException

from seedsigner.controller import Controller
from seedsigner.gui.screens.screen import RET_CODE__BACK_BUTTON, RET_CODE__POWER_BUTTON, ButtonListScreen, ButtonOption
from seedsigner.models.seed import Seed
from seedsigner.views import scan_views
from seedsigner.views.psbt_views import PSBTSelectSeedView
from seedsigner.views.seed_views import SeedBackupView, SeedMnemonicEntryView, SeedOptionsView, SeedsMenuView
from seedsigner.views.view import Destination, MainMenuView, PowerOptionsView, UnhandledExceptionView, View
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
                FlowStep(ToolsMenuView),  # <-- Wrong target View!
            ])
    

    def test_UnhandledExceptionView(self):
        """
        This is a regression test to ensure that the FlowTest is aware of exceptions that
        redirect to the UnhandledExceptionView. If that isn't the expected View, the
        FlowTest should raise a FlowTestUnexpectedViewException.
        """
        # This sequence simulates a FlowTest that is unaware of an exception that will
        # derail the sequence (i.e. somebody wrote a bad FlowTest or something unexpected
        # is breaking). The sequence should fail with FlowTestUnexpectedViewException.
        with pytest.raises(FlowTestUnexpectedViewException):
            self.run_sequence([
                FlowStep(PSBTSelectSeedView),  # <-- There is no PSBT loaded. Should raise an exception that routes us to the UnhandledExceptionView.
                FlowStep(scan_views.ScanSeedQRView),  # <-- This is not the View we'll end up at; FlowTest should raise the FlowTestUnexpectedViewException
            ])

        # This sequence *expects* an exception to route us to the UnhandledExceptionView
        # and therefore can complete successfully.
        self.run_sequence([
            FlowStep(PSBTSelectSeedView),  # <-- There's no PSBT loaded.
            FlowStep(UnhandledExceptionView),
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


    def test_FlowTestUnexpectedRedirectException(self):
        """
        If the FlowStep doesn't specify is_redirect when the View redirects, raise FlowTestUnexpectedRedirectException
        """
        with pytest.raises(FlowTestUnexpectedRedirectException) as e:
            self.run_sequence([
                FlowStep(SeedsMenuView, button_data_selection=SeedsMenuView.LOAD),  # <-- No seeds loaded, so it'll redirect elsewhere
            ])

        # This time we'll show that we know it should redirect
        self.run_sequence([
            FlowStep(SeedsMenuView, is_redirect=True),
        ])


    def test_FlowTestMissingRedirectException(self):
        """
        If the FlowStep specifies is_redirect but the View does NOT redirect, raise FlowTestMissingRedirectException
        """
        with pytest.raises(FlowTestMissingRedirectException):
            self.run_sequence([
                FlowStep(MainMenuView, button_data_selection=MainMenuView.TOOLS, is_redirect=True),
            ])


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
    

    def test_raise_exception_on_bad_button_data_type(self):
        """
        Ensure that the FlowTest raises an exception if a Screen's button_data has
        non-ButtonOption entries.
        """
        class MyBadButtonDataTestView(View):
            def run(self):
                self.run_screen(
                    ButtonListScreen,
                    button_data=[ButtonOption("this is fine"), "this is not"]
                )

        class MyGoodButtonDataTestView(View):
            def run(self):
                self.run_screen(
                    ButtonListScreen,
                    button_data=[ButtonOption("this is fine"), ButtonOption("this is also fine")]
                )
                return Destination(MainMenuView)


        # Should catch the bad button_data
        with pytest.raises(FlowTestInvalidButtonDataInstanceTypeException):
            self.run_sequence([
                FlowStep(MyBadButtonDataTestView),
                FlowStep(MainMenuView),  # Need a next Destination to force the first step to run
            ])

        # But if it's all ButtonOption instances, it should be fine
        self.run_sequence([
            FlowStep(MyGoodButtonDataTestView),
            FlowStep(MainMenuView),  # Need a next Destination to force the first step to run
        ])

