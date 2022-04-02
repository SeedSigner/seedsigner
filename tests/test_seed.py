import pytest
from mock import MagicMock
from seedsigner.models import Seed
from embit import bip39

from seedsigner.models.settings import SettingsConstants



def test_seed():
	seed = Seed(mnemonic="obscure bone gas open exotic abuse virus bunker shuffle nasty ship dash".split())
	
	assert seed.seed_bytes == b'q\xb3\xd1i\x0c\x9b\x9b\xdf\xa7\xd9\xd97H\xa8,\xa7\xd9>\xeck\xc2\xf5ND?, \x88-\x07\x9aa\xc5\xee\xb7\xbf\xc4x\xd6\x07 X\xb6}?M\xaa\x05\xa6\xa7(>\xbf\x03\xb0\x9d\xef\xed":\xdf\x88w7'
	
	assert seed.mnemonic_str == "obscure bone gas open exotic abuse virus bunker shuffle nasty ship dash"
	
	assert seed.passphrase == ""
	
	# TODO: Not yet supported in new implementation
	# seed.set_wordlist_language_code("es")
	
	# assert seed.mnemonic_str == "natural ayuda futuro nivel espejo abuelo vago bien repetir moreno relevo conga"
	
	# seed.set_wordlist_language_code(SettingsConstants.WORDLIST_LANGUAGE__ENGLISH)
	
	# seed.mnemonic_str = "height demise useless trap grow lion found off key clown transfer enroll"
	
	# assert seed.mnemonic_str == "height demise useless trap grow lion found off key clown transfer enroll"
	
	# # TODO: Not yet supported in new implementation
	# seed.set_wordlist_language_code("es")
	
	# assert seed.mnemonic_str == "hebilla cría truco tigre gris llenar folio negocio laico casa tieso eludir"
	
	# seed.set_passphrase("test")
	
	# assert seed.seed_bytes == b'\xdd\r\xcb\x0b V\xb4@\xee+\x01`\xabem\xc1B\xfd\x8fba0\xab;[\xab\xc9\xf9\xba[F\x0c5,\x7fd8\xebI\x90"\xb8\x86C\x821\x01\xdb\xbe\xf3\xbc\x1cBH"%\x18\xc2{\x04\x08a]\xa5'
	
	# assert seed.passphrase == "test"

	
	
	
	