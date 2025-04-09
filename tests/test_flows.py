import pytest

# Must import test base before the Controller
from base import (
    FlowTest,
    FlowStep,
    FlowTestMissingRedirectException,
    FlowTestUnexpectedRedirectException,
    FlowTestUnexpectedViewException,
    FlowTestInvalidButtonDataSelectionException,
    FlowTestInvalidButtonDataInstanceTypeException,
)

from seedsigner.controller import Controller
from seedsigner.gui.screens.screen import (
    RET_CODE__BACK_BUTTON,
    RET_CODE__POWER_BUTTON,
    ButtonListScreen,
    ButtonOption,
)
from seedsigner.models.seed import Seed
from seedsigner.views import scan_views
from seedsigner.views.psbt_views import PSBTSelectSeedView
from seedsigner.views.seed_views import (
    SeedBackupView,
    SeedMnemonicEntryView,
    SeedOptionsView,
    SeedsMenuView,
)
from seedsigner.views.view import (
    Destination,
    MainMenuView,
    PowerOptionsView,
    UnhandledExceptionView,
    View,
)
from seedsigner.views.tools_views import (
    ToolsMenuView,
    ToolsCalcFinalWordNumWordsView,
)


class TestFlowTest(FlowTest):

    def test_simple_flow(self):
        """Ensure FlowTest follows a basic sequence of views."""
        self.run_sequence([
            FlowStep(MainMenuView, button_data_selection=MainMenuView.TOOLS),
            FlowStep(ToolsMenuView, button_data_selection=ToolsMenuView.KEYBOARD),
            FlowStep(ToolsCalcFinalWordNumWordsView, button_data_selection=ToolsCalcFinalWordNumWordsView.TWELVE),
            FlowStep(SeedMnemonicEntryView),
        ])

    def test_FlowTestUnexpectedViewException(self):
        """Raise exception if actual view doesn't match expected."""
        with pytest.raises(FlowTestUnexpectedViewException):
            self.run_sequence([
                FlowStep(MainMenuView, button_data_selection=RET_CODE__POWER_BUTTON),
                FlowStep(ToolsMenuView),  # Wrong view, should trigger exception
            ])

    def test_UnhandledExceptionView(self):
        """Check FlowTest catches unexpected routing to UnhandledExceptionView."""
        with pytest.raises(FlowTestUnexpectedViewException):
            self.run_sequence([
                FlowStep(PSBTSelectSeedView),
                FlowStep(scan_views.ScanSeedQRView),
            ])

        # Now expecting the exception redirect
        self.run_sequence([
            FlowStep(PSBTSelectSeedView),
            FlowStep(UnhandledExceptionView),
        ])

    def test_FlowTestInvalidButtonDataSelectionException(self):
        """Invalid button_data_selection should raise exception."""
        with pytest.raises(FlowTestInvalidButtonDataSelectionException):
            self.run_sequence([
                FlowStep(MainMenuView, button_data_selection="invalid-option"),
            ])

    def test_FlowTestUnexpectedRedirectException(self):
        """Unexpected redirect without is_redirect should raise exception."""
        with pytest.raises(FlowTestUnexpectedRedirectException):
            self.run_sequence([
                FlowStep(SeedsMenuView, button_data_selection=SeedsMenuView.LOAD),
            ])

        # Now expecting the redirect
        self.run_sequence([
            FlowStep(SeedsMenuView, is_redirect=True),
        ])

    def test_FlowTestMissingRedirectException(self):
        """If is_redirect=True but no redirect occurs, raise exception."""
        with pytest.raises(FlowTestMissingRedirectException):
            self.run_sequence([
                FlowStep(MainMenuView, button_data_selection=MainMenuView.TOOLS, is_redirect=True),
            ])

    def test_before_run_executes(self):
        """Test placeholder: should verify pre-run hook."""
        # TODO: Implement test logic
        pass

    def test_back_button_flow(self):
        """Validate back-button behavior in the Controller's stack."""
        self.run_sequence([
            FlowStep(MainMenuView, screen_return_value=RET_CODE__POWER_BUTTON),
            FlowStep(PowerOptionsView, screen_return_value=RET_CODE__BACK_BUTTON),
            FlowStep(MainMenuView),
        ])

    def test_initial_destination(self):
        """Ensure FlowTest can start from non-default view."""
        self.run_sequence([
            FlowStep(ToolsCalcFinalWordNumWordsView),
        ])

        self.reset_controller()
        self.controller = Controller.get_instance()

        seed = Seed(mnemonic=["abandon"] * 11 + ["about"])
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
        """Raising an exception should route to UnhandledExceptionView."""
        self.run_sequence([
            FlowStep(MainMenuView, screen_return_value=Exception("Test exception")),
            FlowStep(UnhandledExceptionView),
        ])

    def test_raise_exception_on_bad_button_data_type(self):
        """Raise exception if button_data contains invalid types."""
        class MyBadButtonDataTestView(View):
            def run(self):
                self.run_screen(
                    ButtonListScreen,
                    button_data=[ButtonOption("valid"), "invalid"]  # Invalid entry
                )

        class MyGoodButtonDataTestView(View):
            def run(self):
                self.run_screen(
                    ButtonListScreen,
                    button_data=[ButtonOption("valid"), ButtonOption("also valid")]
                )
                return Destination(MainMenuView)

        with pytest.raises(FlowTestInvalidButtonDataInstanceTypeException):
            self.run_sequence([
                FlowStep(MyBadButtonDataTestView),
                FlowStep(MainMenuView),
            ])

        self.run_sequence([
            FlowStep(MyGoodButtonDataTestView),
            FlowStep(MainMenuView),
        ])
