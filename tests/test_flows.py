import sys
from typing import Any, List, Tuple, Type, Union
from mock import patch, MagicMock

# sys.modules['seedsigner.gui.screens.seed_screens'] = MagicMock()

# Must import this before the Controller
from utils import reset_controller

from seedsigner.controller import Controller
from seedsigner.models.seed import Seed
from seedsigner.views.view import Destination



def flow_sequence(initial_destination: Destination, return_values: List[Union[int, str]]) -> Destination:
    """
        Runs the given sequence from the initial_destination, mocking out the associated
        Screen and the scenario's return_value, receiving the resulting new Destination,
        and repeating until the sequence is complete.

        Returns the final Destination.
    """
    next_destination = initial_destination
    for return_value in return_values:
        if next_destination.View_cls.Screen_cls is None:
            raise Exception(f"Screen_cls not specified in {next_destination.View_cls}")
        qualname = ".".join([next_destination.View_cls.__module__, next_destination.View_cls.__name__])
        with patch(qualname + ".run_screen") as mock_run_screen:
            mock_run_screen.return_value = return_value
            next_destination = next_destination.run()

    return next_destination



class TestFlows:


    def setup_method(self):
        reset_controller()


    def test_addressexplorer_seedfinalizescreen_flow(self):
        """
            Finalizing a seed during the Address Explorer flow should return to the next
            Address Explorer step upon completion.
        """
        from seedsigner.views import seed_views

        controller = Controller.get_instance()
        seed = Seed(mnemonic=["abandon "* 11 + "about"])
        controller.storage.set_pending_seed(seed)
        
        # Default behavior should land at the SeedOptionsView
        sequence = [
            0,      # SeedFinalizeView: ret DONE
        ]
        destination = flow_sequence(Destination(seed_views.SeedFinalizeView), return_values=sequence)
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
        destination = flow_sequence(Destination(seed_views.SeedFinalizeView), return_values=sequence)

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
        destination = flow_sequence(Destination(seed_views.SeedFinalizeView), return_values=sequence)

        # Flow should resume at Script Type selection
        assert destination.View_cls == seed_views.SeedExportXpubScriptTypeView
