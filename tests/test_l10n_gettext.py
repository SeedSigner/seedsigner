import logging
import re
from unittest.mock import patch, MagicMock

import pytest

import sys

# Prevent importing modules w/Raspi hardware dependencies (same as base.py).
sys.modules['numpy'] = MagicMock()
sys.modules['seedsigner.gui.renderer'] = MagicMock()
sys.modules['seedsigner.gui.screens.screensaver'] = MagicMock()
sys.modules['seedsigner.gui.toast'] = MagicMock()
sys.modules['seedsigner.views.screensaver'] = MagicMock()
sys.modules['seedsigner.hardware.buttons'] = MagicMock()
sys.modules['seedsigner.hardware.camera.Camera'] = MagicMock()
sys.modules['seedsigner.hardware.pivideostream'] = MagicMock()
sys.modules['seedsigner.hardware.st7789_mpy'] = MagicMock()
sys.modules['seedsigner.hardware.ili9341'] = MagicMock()

from seedsigner.helpers.l10n import (
    seedsigner_gettext,
    seedsigner_ngettext,
    mark_for_translation,
    TranslationVariableMissingError,
)


@pytest.fixture(autouse=True)
def _mock_settings():
    """Mock Settings.get_instance() so production settings are never touched."""
    mock_settings = MagicMock()
    mock_settings.get_value.return_value = "de_DE"
    with patch("seedsigner.models.settings.Settings") as MockSettings, \
         patch("seedsigner.models.settings_definition.SettingsConstants") as MockSC:
        MockSettings.get_instance.return_value = mock_settings
        MockSC.SETTING__LOCALE = "locale"
        yield



class TestMarkForTranslation:
    def test_returns_original_string(self):
        assert mark_for_translation("Hello") == "Hello"

    def test_does_not_translate(self):
        """mark_for_translation must never modify the string."""
        msg = "Some {variable} string"
        assert mark_for_translation(msg) is msg



class TestTranslationVariableMissingError:
    def test_str_with_all_fields(self):
        exc = TranslationVariableMissingError(
            locale="de_DE",
            message="Hello {name}",
            translated="Hallo {}",
            expected_vars=["name"],
        )
        s = str(exc)
        assert "de_DE" in s
        assert "Hello {name}" in s
        assert "Hallo {}" in s
        assert "{name}" in s

    def test_str_without_expected_vars(self):
        exc = TranslationVariableMissingError(locale="de_DE")
        assert "de_DE" in str(exc)

    def test_attributes_stored(self):
        exc = TranslationVariableMissingError(
            locale="fr_FR",
            message="original",
            translated="traduit",
            expected_vars=["a", "b"],
        )
        assert exc.locale == "fr_FR"
        assert exc.message == "original"
        assert exc.translated == "traduit"
        assert exc.expected_vars == ["a", "b"]



class TestSeedSignerGettextSuccess:
    @patch("seedsigner.helpers.l10n.gettext.gettext")
    def test_no_kwargs_returns_translated(self, mock_gt):
        mock_gt.return_value = "Hallo"
        assert seedsigner_gettext("Hello") == "Hallo"
        mock_gt.assert_called_once_with("Hello")

    @patch("seedsigner.helpers.l10n.gettext.gettext")
    def test_named_variable_substitution(self, mock_gt):
        mock_gt.return_value = "Hallo {name}"
        assert seedsigner_gettext("Hello {name}", name="World") == "Hallo World"

    @patch("seedsigner.helpers.l10n.gettext.gettext")
    def test_multiple_named_variables(self, mock_gt):
        mock_gt.return_value = "Das {n}te Wort wird erstellt aus {bits} Bits"
        result = seedsigner_gettext(
            "The {n}th word is built from {bits} bits",
            n=12,
            bits=8,
        )
        assert result == "Das 12te Wort wird erstellt aus 8 Bits"

    @patch("seedsigner.helpers.l10n.gettext.gettext")
    def test_no_translation_available(self, mock_gt):
        """When gettext returns the original string unchanged."""
        mock_gt.return_value = "Hello {name}"
        assert seedsigner_gettext("Hello {name}", name="World") == "Hello World"



class TestSeedSignerGettextFailure:
    @patch("seedsigner.helpers.l10n.gettext.gettext")
    def test_missing_variable_in_kwargs_raises(self, mock_gt):
        """Translation expects {name} but kwargs only has 'greeting' → KeyError."""
        mock_gt.return_value = "Hallo {name}"
        with pytest.raises(TranslationVariableMissingError) as exc_info:
            seedsigner_gettext("Hello {name}", greeting="Hi")

        exc = exc_info.value
        assert exc.locale == "de_DE"
        assert exc.message == "Hello {name}"
        assert exc.translated == "Hallo {name}"
        assert exc.expected_vars == ["greeting"]

    @patch("seedsigner.helpers.l10n.gettext.gettext")
    def test_positional_placeholder_raises(self, mock_gt, caplog):
        """Translation uses {} instead of {name} → IndexError."""
        mock_gt.return_value = "Hallo {}"
        with pytest.raises(TranslationVariableMissingError) as exc_info:
            seedsigner_gettext("Hello {name}", name="World")

        exc = exc_info.value
        assert exc.expected_vars == ["name"]
        assert "empty brackets" in caplog.text.lower() or "IndexError" in caplog.text or "{}" in caplog.text

    @patch("seedsigner.helpers.l10n.gettext.gettext")
    def test_wrong_variable_name_raises(self, mock_gt, caplog):
        """Translation uses {username} instead of {name} → KeyError."""
        mock_gt.return_value = "Hallo {username}"
        with pytest.raises(TranslationVariableMissingError) as exc_info:
            seedsigner_gettext("Hello {name}", name="World")

        exc = exc_info.value
        assert exc.expected_vars == ["name"]
        assert "username" in caplog.text

    @patch("seedsigner.helpers.l10n.gettext.gettext")
    def test_malformed_format_string_raises(self, mock_gt):
        """Translation has unclosed brace {name → ValueError."""
        mock_gt.return_value = "Hallo {name"
        with pytest.raises(TranslationVariableMissingError) as exc_info:
            seedsigner_gettext("Hello {name}", name="World")

        exc = exc_info.value
        assert exc.locale == "de_DE"
        assert exc.expected_vars == ["name"]

    @pytest.mark.parametrize(
        "translated, kwargs, expected_exc_cause",
        [
            pytest.param("Hallo {}", dict(name="World"), IndexError, id="positional_placeholder"),
            pytest.param("Hallo {username}", dict(name="World"), KeyError, id="wrong_variable_name"),
            pytest.param("Hallo {name", dict(name="World"), ValueError, id="malformed_brace"),
            pytest.param("{} {} bits", dict(n=12, bits=8), IndexError, id="multiple_positional"),
        ],
    )
    @patch("seedsigner.helpers.l10n.gettext.gettext")
    def test_parametrized_failures(self, mock_gt, translated, kwargs, expected_exc_cause):
        mock_gt.return_value = translated
        with pytest.raises(TranslationVariableMissingError) as exc_info:
            seedsigner_gettext("original", **kwargs)

        assert exc_info.value.locale == "de_DE"
        assert exc_info.value.expected_vars == list(kwargs.keys())
        assert isinstance(exc_info.value.__cause__, expected_exc_cause)

    @patch("seedsigner.helpers.l10n.gettext.gettext")
    def test_exception_chains_original_cause(self, mock_gt):
        """The custom exception should chain from the original formatting error."""
        mock_gt.return_value = "Hallo {}"
        with pytest.raises(TranslationVariableMissingError) as exc_info:
            seedsigner_gettext("Hello {name}", name="World")

        assert exc_info.value.__cause__ is not None
        assert isinstance(exc_info.value.__cause__, IndexError)



class TestSeedSignerGettextLogging:
    @patch("seedsigner.helpers.l10n.gettext.gettext")
    def test_logs_empty_brackets(self, mock_gt, caplog):
        mock_gt.return_value = "Hallo {}"
        with caplog.at_level(logging.ERROR):
            with pytest.raises(TranslationVariableMissingError):
                seedsigner_gettext("Hello {name}", name="World")
        assert "empty brackets" in caplog.text.lower() or "{}" in caplog.text

    @patch("seedsigner.helpers.l10n.gettext.gettext")
    def test_logs_missing_named_variable(self, mock_gt, caplog):
        mock_gt.return_value = "Hallo {username}"
        with caplog.at_level(logging.ERROR):
            with pytest.raises(TranslationVariableMissingError):
                seedsigner_gettext("Hello {name}", name="World")
        assert "username" in caplog.text

    @patch("seedsigner.helpers.l10n.gettext.gettext")
    def test_logs_malformed_format(self, mock_gt, caplog):
        mock_gt.return_value = "Hallo {name"
        with caplog.at_level(logging.ERROR):
            with pytest.raises(TranslationVariableMissingError):
                seedsigner_gettext("Hello {name}", name="World")
        assert "de_DE" in caplog.text



class TestSeedSignerNgettextSuccess:
    @patch("seedsigner.helpers.l10n.gettext.ngettext")
    def test_singular_no_kwargs(self, mock_ng):
        mock_ng.return_value = "1 Datei"
        result = seedsigner_ngettext("{count} file", "{count} files", 1)
        assert result == "1 Datei"
        mock_ng.assert_called_once_with("{count} file", "{count} files", 1)

    @patch("seedsigner.helpers.l10n.gettext.ngettext")
    def test_plural_no_kwargs(self, mock_ng):
        mock_ng.return_value = "5 Dateien"
        result = seedsigner_ngettext("{count} file", "{count} files", 5)
        assert result == "5 Dateien"

    @patch("seedsigner.helpers.l10n.gettext.ngettext")
    def test_singular_with_kwargs(self, mock_ng):
        mock_ng.return_value = "{count} Datei"
        result = seedsigner_ngettext("{count} file", "{count} files", 1, count=1)
        assert result == "1 Datei"

    @patch("seedsigner.helpers.l10n.gettext.ngettext")
    def test_plural_with_kwargs(self, mock_ng):
        mock_ng.return_value = "{count} Dateien"
        result = seedsigner_ngettext("{count} file", "{count} files", 5, count=5)
        assert result == "5 Dateien"



class TestSeedSignerNgettextFailure:
    @patch("seedsigner.helpers.l10n.gettext.ngettext")
    def test_positional_placeholder_raises(self, mock_ng):
        mock_ng.return_value = "{} Dateien"
        with pytest.raises(TranslationVariableMissingError) as exc_info:
            seedsigner_ngettext("{count} file", "{count} files", 5, count=5)

        exc = exc_info.value
        assert exc.locale == "de_DE"
        assert exc.expected_vars == ["count"]
        assert isinstance(exc.__cause__, IndexError)

    @patch("seedsigner.helpers.l10n.gettext.ngettext")
    def test_wrong_variable_name_raises(self, mock_ng):
        mock_ng.return_value = "{anzahl} Dateien"
        with pytest.raises(TranslationVariableMissingError) as exc_info:
            seedsigner_ngettext("{count} file", "{count} files", 5, count=5)

        exc = exc_info.value
        assert exc.expected_vars == ["count"]

    @patch("seedsigner.helpers.l10n.gettext.ngettext")
    def test_singular_message_stored_on_error(self, mock_ng):
        """When n==1, exception.message should be the singular form."""
        mock_ng.return_value = "{} Datei"
        with pytest.raises(TranslationVariableMissingError) as exc_info:
            seedsigner_ngettext("{count} file", "{count} files", 1, count=1)

        assert exc_info.value.message == "{count} file"

    @patch("seedsigner.helpers.l10n.gettext.ngettext")
    def test_plural_message_stored_on_error(self, mock_ng):
        """When n!=1, exception.message should be the plural form."""
        mock_ng.return_value = "{} Dateien"
        with pytest.raises(TranslationVariableMissingError) as exc_info:
            seedsigner_ngettext("{count} file", "{count} files", 5, count=5)

        assert exc_info.value.message == "{count} files"

    @patch("seedsigner.helpers.l10n.gettext.ngettext")
    def test_ngettext_logs_error(self, mock_ng, caplog):
        mock_ng.return_value = "{} Dateien"
        with caplog.at_level(logging.ERROR):
            with pytest.raises(TranslationVariableMissingError):
                seedsigner_ngettext("{count} file", "{count} files", 5, count=5)
        assert "de_DE" in caplog.text



def _extract_named_vars(fmt_string: str) -> set[str]:
    """Extract named variables from a format string like '{name} is {age}'."""
    return set(re.findall(r'\{(\w+)\}', fmt_string))


def _has_positional_placeholders(fmt_string: str) -> bool:
    """Detect positional {} placeholders (empty braces)."""
    return bool(re.search(r'\{\}', fmt_string))


class TestVariableConsistencyDetection:
    """
    Bonus tests demonstrating how to detect variable mismatches between
    source and translated strings — useful for a future CI lint step.
    """

    @pytest.mark.parametrize(
        "source, translated, expected_match",
        [
            pytest.param(
                "The {n}th word from {bits} bits",
                "Das {n}te Wort aus {bits} Bits",
                True,
                id="matching_vars",
            ),
            pytest.param(
                "The {n}th word from {bits} bits",
                "Das {number}te Wort aus {bits} Bits",
                False,
                id="renamed_var",
            ),
            pytest.param(
                "The {n}th word from {bits} bits",
                "Das {n}te Wort aus {bits} Bits und {extra}",
                False,
                id="extra_var_in_translation",
            ),
            pytest.param(
                "Hello {name}",
                "Hallo {}",
                False,
                id="positional_instead_of_named",
            ),
        ],
    )
    def test_variable_sets_match(self, source, translated, expected_match):
        source_vars = _extract_named_vars(source)
        translated_vars = _extract_named_vars(translated)
        has_positional = _has_positional_placeholders(translated)

        is_consistent = (source_vars == translated_vars) and not has_positional
        assert is_consistent == expected_match

    def test_detect_positional_placeholders(self):
        assert _has_positional_placeholders("Hello {}") is True
        assert _has_positional_placeholders("Hello {name}") is False
        assert _has_positional_placeholders("{} and {}") is True

    def test_detect_extra_vars_in_translation(self):
        source_vars = _extract_named_vars("Hello {name}")
        trans_vars = _extract_named_vars("Hallo {name} {extra}")
        extra = trans_vars - source_vars
        assert extra == {"extra"}
