import gettext
import re
import logging

def mark_for_translation(message: str) -> str:
    """
    Wraps the target string literal for translation but does NOT return the translated string.
    """
    return message

class TranslationVariableMissingError(Exception):
    """
    Raised when a translation does not include the expected named variable(s).
    """
    def __init__(self, locale=None, message=None, translated=None, expected_vars=None):
        self.locale = locale
        self.message = message
        self.translated = translated
        self.expected_vars = expected_vars

    def __str__(self):
        if self.expected_vars:
            expected_vars_str = ', '.join([f'{{{var}}}' for var in self.expected_vars])
            return f"Translation error in locale '{self.locale}': Translation missing variables {expected_vars_str}.\nOriginal: '{self.message}'\nTranslation: '{self.translated}'"
        return f"Translation error in locale '{self.locale}'"

def seedsigner_gettext(message: str, **kwargs):
    """
    Enhanced gettext with built-in variable formatting and better error messages.
    """
    translated = gettext.gettext(message)
    
    if not kwargs:
        return translated
    
    try:
        return translated.format(**kwargs)
    except (KeyError, IndexError, ValueError) as e:
        from seedsigner.models.settings import Settings
        from seedsigner.models.settings_definition import SettingsConstants
        
        locale = Settings.get_instance().get_value(SettingsConstants.SETTING__LOCALE)
        
        # More detailed error logging based on exception type
        if isinstance(e, IndexError) and re.search(r'{}', translated):
            logging.error(f"Translation contains empty brackets {{}} instead of named variables in locale '{locale}'")
        elif isinstance(e, KeyError):
            missing_var = str(e).strip("'")
            logging.error(f"Translation missing named variable {{{missing_var}}} in locale '{locale}'")
        else:
            logging.error(f"Translation formatting error in locale '{locale}': {str(e)}")
        
        raise TranslationVariableMissingError(
            locale=locale,
            message=message,
            translated=translated,
            expected_vars=list(kwargs.keys())
        ) from e

def seedsigner_ngettext(singular: str, plural: str, n: int, **kwargs):
    """
    Enhanced ngettext with built-in variable formatting and better error messages.
    """
    translated = gettext.ngettext(singular, plural, n)
    
    if not kwargs:
        return translated
    
    try:
        return translated.format(**kwargs)
    except (KeyError, IndexError, ValueError) as e:
        from seedsigner.models.settings import Settings
        from seedsigner.models.settings_definition import SettingsConstants
        
        locale = Settings.get_instance().get_value(SettingsConstants.SETTING__LOCALE)
        
        # Log the error
        logging.error(f"Translation formatting error in locale '{locale}': {str(e)}")
        
        raise TranslationVariableMissingError(
            locale=locale,
            message=singular if n == 1 else plural,
            translated=translated,
            expected_vars=list(kwargs.keys())
        ) from e