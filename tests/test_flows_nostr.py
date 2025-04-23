# Must import test base before the Controller
from base import FlowStep, FlowTest

from seedsigner.models.seed import Seed
from seedsigner.models.settings_definition import SettingsConstants
from seedsigner.views import nostr_views, seed_views
from seedsigner.views.view import MainMenuView



class TestNostrFlows(FlowTest):
    def setup_method(self):
        super().setup_method()

        # Load a finalized Seed into the Controller; same mnemonic as the NIP-06 test vector
        mnemonic = "leader monkey parrot ring guide accident before fence cannon height naive bean".split()
        self.controller.storage.set_pending_seed(Seed(mnemonic=mnemonic))
        self.controller.storage.finalize_pending_seed()

        # NIP-06 option must be enabled
        self.settings.set_value(SettingsConstants.SETTING__NOSTR_NIP06_EXPORT, SettingsConstants.OPTION__ENABLED)


    def test__export_nostr_pubkey__flow(self):
        """
        Exporting a Nostr pubkey should work for npub or pubkey hex format, display it as
        a QR code, and return to Seed Options.
        """
        for nostr_type_selection in [nostr_views.NostrExportKeySelectTypeView.PUBKEY_NPUB, nostr_views.NostrExportKeySelectTypeView.PUBKEY_HEX]:
            self.run_sequence([
                FlowStep(MainMenuView, button_data_selection=MainMenuView.SEEDS),
                FlowStep(seed_views.SeedsMenuView, screen_return_value=0),
                FlowStep(seed_views.SeedOptionsView, button_data_selection=seed_views.SeedOptionsView.EXPORT_NOSTR_KEY),
                FlowStep(nostr_views.NostrExportKeyStartView),
                FlowStep(nostr_views.NostrExportKeySelectTypeView, button_data_selection=nostr_type_selection),
                FlowStep(nostr_views.NostrExportKeyDisplayKeyView),
                FlowStep(nostr_views.NostrExportKeyQRView),
                FlowStep(seed_views.SeedOptionsView),
            ])


    def test__export_nostr_privkey__flow(self):
        """
        Exporting a Nostr privkey should work for nsec or privkey hex format, display a
        dire warning message, display the privkey as a QR code, and return to Seed
        Options.
        """
        for nostr_type_selection in [nostr_views.NostrExportKeySelectTypeView.PRIVKEY_NSEC, nostr_views.NostrExportKeySelectTypeView.PRIVKEY_HEX]:
            self.run_sequence([
                FlowStep(MainMenuView, button_data_selection=MainMenuView.SEEDS),
                FlowStep(seed_views.SeedsMenuView, screen_return_value=0),
                FlowStep(seed_views.SeedOptionsView, button_data_selection=seed_views.SeedOptionsView.EXPORT_NOSTR_KEY),
                FlowStep(nostr_views.NostrExportKeyStartView),
                FlowStep(nostr_views.NostrExportKeySelectTypeView, button_data_selection=nostr_type_selection),
                FlowStep(nostr_views.NostrExportKeyPrivateKeyWarningView),  # Unique to the privkey export flow
                FlowStep(nostr_views.NostrExportKeyDisplayKeyView),
                FlowStep(nostr_views.NostrExportKeyQRView),
                FlowStep(seed_views.SeedOptionsView),
            ])
