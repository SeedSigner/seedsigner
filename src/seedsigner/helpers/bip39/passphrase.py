from gettext import gettext as _ 

from seedsigner.models.settings import SettingsConstants
from .constants import SPECIAL_CHARSETS

def get_special_passphrase_charset(locale: str):
    """
    Returns an array of two strings containing special characters based upon the locale specified
    one in lower case and the other in upper case.
    """  
    if locale not in SPECIAL_CHARSETS:
        return []
    return SPECIAL_CHARSETS[locale]