from typing import List, Type, Union
from mock import patch

# Must import this before the Controller
from utils import reset_controller

from seedsigner.controller import Controller
from seedsigner.models.seed import Seed
from seedsigner.views.view import Destination, MainMenuView, View
from seedsigner.views import seed_views, scan_views



RUN_BEFORE = "run_before"
RETURN_VALUE = "return_value"



def run_flow_sequence(initial_destination: Destination, return_values: List[Union[int, str, dict]]) -> Destination:
    """
        Runs the given sequence from the initial_destination, mocking out the associated
        Screen and the scenario's return_value, receiving the resulting new Destination,
        and repeating until the sequence is complete.

        Returns the final Destination.
    """
    next_destination = initial_destination
    for return_value in return_values:
        # Optionally modify the View_cls instance before run_screen is called
        run_before = None
        if type(return_value) == dict:
            if RUN_BEFORE in return_value:
                run_before = return_value[RUN_BEFORE]

        # Patch the run_screen so we don't actually instantiate and execute the Screen_cls
        qualname = ".".join([next_destination.View_cls.__module__, next_destination.View_cls.__name__])
        with patch(qualname + ".run_screen") as mock_run_screen:
            mock_run_screen.return_value = return_value

            # Now we can run the View and grab its resulting next Destination
            next_destination = next_destination.run(run_before=run_before)

    return next_destination



class TestFlows:

    def setup_method(self):
        reset_controller()


    def test_home_scan_seedoptions_flow(self):
        """
            Selecting "Scan" from the MainMenuView and scanning a SeedQR should enter the
            Finalize Seed flow and end at the SeedOptionsView.
        """
        def load_seed_into_decoder(view: scan_views.ScanView):
            view.decoder.add_data("0000" * 11 + "0003")

        sequence = [
            0,      # MainMenuView: ret SCAN
            {RUN_BEFORE: load_seed_into_decoder, RETURN_VALUE: None},    # ScanView: read SeedQR
            0,      # SeedFinalizeView: ret DONE
        ]
        destination = run_flow_sequence(Destination(MainMenuView), return_values=sequence)

        # Should land on SeedOptionsView
        assert destination.View_cls == seed_views.SeedOptionsView


    def test_addressexplorer_seedfinalizescreen_flow(self):
        """
            Finalizing a seed during the Address Explorer flow should return to the next
            Address Explorer step upon completion.
        """
        controller = Controller.get_instance()
        seed = Seed(mnemonic=["abandon "* 11 + "about"])
        controller.storage.set_pending_seed(seed)
        
        # Default behavior should land at the SeedOptionsView
        sequence = [
            0,      # SeedFinalizeView: ret DONE
        ]
        destination = run_flow_sequence(Destination(seed_views.SeedFinalizeView), return_values=sequence)
        assert destination.View_cls == seed_views.SeedOptionsView

        # Reset
        controller.storage.seeds.clear()
        controller.storage.set_pending_seed(seed)

        # Now set the flow and try again
        controller.resume_main_flow = Controller.FLOW__ADDRESS_EXPLORER

        # Finalize the new seed w/out passphrase
        sequence = [
            0,      # SeedFinalizeView: ret DONE
            None,   # SeedOptionsView should auto-route away
        ]
        destination = run_flow_sequence(Destination(seed_views.SeedFinalizeView), return_values=sequence)

        # Flow should resume at Script Type selection
        assert destination.View_cls == seed_views.SeedExportXpubScriptTypeView

        # Reset
        controller.storage.seeds.clear()
        controller.storage.set_pending_seed(seed)

        # Finalize the new seed w/passphrase
        sequence = [
            1,                  # SeedFinalizeView: ret PASSPHRASE
            "mypassphrase",     # SeedPassphraseView: ret passphrase str
            1,                  # SeedReviewPassphraseView: ret DONE
            None,               # SeedOptionsView should auto-route away
        ]
        destination = run_flow_sequence(Destination(seed_views.SeedFinalizeView), return_values=sequence)

        # Flow should resume at Script Type selection
        assert destination.View_cls == seed_views.SeedExportXpubScriptTypeView
