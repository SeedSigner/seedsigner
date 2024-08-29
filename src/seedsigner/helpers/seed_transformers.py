from embit import bip39

def convert_word_to_11_bits(word: str) -> str:
    wordlist = bip39.WORDLIST
    if word not in wordlist:
        raise ValueError(f"Word '{word}' is not in the dictionary")

    return f'{bip39.WORDLIST.index(word):011b}'

def convert_word_to_decimal(word: str) -> str:
    wordlist = bip39.WORDLIST
    if word not in wordlist:
        raise ValueError(f"Word '{word}' is not in the dictionary")

    return str(bip39.WORDLIST.index(word))