import os
import ast
from seedsigner.models.settings_definition import SettingsConstants
from .constants import WORDLIST_LANGUAGES

def load_wordlist_from_file(wordlist_language_code: str) -> list:
    """
    Load wordlist from file system path in seedsigner-translations submodule.
    """
    # Get the path to the wordlist file based on the language code.
    current_dir = os.path.dirname(os.path.abspath(__file__))
    translations_dir = os.path.join(current_dir, '..', '..', 'resources', 'seedsigner-translations')
    # Use the language_code directly as the filename (e.g., fr_list.py, es_list.py)
    wordlist_file = os.path.join(translations_dir, 'l10n', wordlist_language_code, 'wordlist', f'{wordlist_language_code}_list.py')

    if not os.path.exists(wordlist_file):
        raise FileNotFoundError(f"Wordlist file not found: {wordlist_file}")
    
    # Read and parse the Python file to extract the wordlist
    with open(wordlist_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Parse the file to extract the wordlist variable
    tree = ast.parse(content)
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id.startswith('WORDLIST__'):
                    # Evaluate the list literal
                    if isinstance(node.value, ast.List):
                        wordlist = [ast.literal_eval(elt) for elt in node.value.elts]
                        return wordlist
    
    raise ValueError(f"Could not find wordlist in file: {wordlist_file}")

def get_bip39_wordlist(wordlist_language_code: str) -> list:
    """
    Returns the wordlist for the specified language code.
    """
    # Only support languages that are in ALL_WORDLIST_LANGUAGES
    if wordlist_language_code not in WORDLIST_LANGUAGES:
        raise ValueError(f"Unsupported language code: {wordlist_language_code}")

    if wordlist_language_code == SettingsConstants.LOCALE__ENGLISH:
        from embit.wordlists.bip39 import WORDLIST as WORDLIST__ENGLISH
        if len(WORDLIST__ENGLISH) != 2048 or WORDLIST__ENGLISH[0] != "abandon":
            raise ValueError("English wordlist is not loaded correctly.")
        return WORDLIST__ENGLISH
    else:
        return load_wordlist_from_file(wordlist_language_code)

def get_possible_alphabet(wordlist_language_code: str) -> str: 
    """
    Returns the possible alphabet for the specified language code.
    """
    if wordlist_language_code not in WORDLIST_LANGUAGES:
        raise ValueError(f"Unsupported language code: {wordlist_language_code}")
    
    return "abcdefghijklmnopqrstuvwxyz"
