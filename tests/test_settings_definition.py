import os
from unittest.mock import Mock

from base import BaseTest
from seedsigner.models.settings_definition import SettingsConstants


class TestSettingsDefinition(BaseTest):
    @classmethod
    def setup_class(cls):
        super().setup_class()


    def test__get_detected_languages(self):
        """ Should auto-detect onboard languages based on the supported locales list """
        detected_languages = [lang_tuple[0] for lang_tuple in SettingsConstants.get_detected_languages()]

        # Find an unused language code; avoiding hard coding a language code to keep
        # this test future proof.
        absent_language_code = None
        for language_code in SettingsConstants.ALL_LOCALES.keys():
            if language_code not in detected_languages:
                absent_language_code = language_code
                break
        
        # Should only fail if we've absolutely crushed the global translations!!!
        assert absent_language_code is not None

        root = os.path.join(os.getcwd(), "src", "seedsigner", "resources", "seedsigner-translations", "l10n")

        # We're going to mock the `root` results to include the absent language code's .mo file
        mocked_results = [(os.path.join(root, "en", "LC_MESSAGES"), [], ["messages.po", "messages.mo"])]
        mocked_results.append((os.path.join(root, absent_language_code, "LC_MESSAGES"), [], ["messages.po", "messages.mo"]))
        os.walk = Mock(return_value=mocked_results)

        # Recheck w/our mocked dir listing:
        detected_languages = [lang_tuple[0] for lang_tuple in SettingsConstants.get_detected_languages()]
        assert absent_language_code in detected_languages
