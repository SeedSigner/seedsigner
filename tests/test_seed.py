from seedsigner.models.seed import Seed

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

	
def test_electrum_seed():
	seed = Seed(mnemonic="regular reject rare profit once math fringe chase until ketchup century escape".split())

	intended_seed = b'\xcan|\xf8\x8a\x8d\xf78=Pq\xc4_\xe6\x02\x91\xfcs\xb2[\xed*\xdc\xc7%\xb6[_-(~D\xe5\x1e\x85%N\x9c\x03\x9dh\xafX}\x16\xb1\x99,\xbe\xc4\x11\xfaW\x0f\xb0\x89yD\xf4\x0f\xd5?\x8eA'

	assert not seed.seed_bytes

	assert seed.electrum_seed_bytes == intended_seed

	seed.switch_to_electrum()

	assert seed.seed_bytes == intended_seed

	assert seed.is_electrum

def test_seed_bip39_electrum_both_valid():
	seed = Seed(mnemonic="frog cricket convince battle film mistake survey normal frequent magnet park cheap".split())

	assert seed.seed_bytes == b'\x05-\x0c\xc2\x97\xfbw\x17b}U[\x80o\x94\x9c\xaa\x0f\xfc\xb2\xac\x08\xa3Q=\xbd\xf6\xcf] I\xfd9\x9a\x7f/\xa3OA\xe21.5^*\xa7e\xcd\xf7$h\x04\x02\xf6\xdf1\xc6\xa9{\x8c\xcc\xcc\xce)'

	assert seed.electrum_seed_bytes == b'<\x03y\xb7\xd6Q\x80I\xf5n\x8e\x9ek\x03!\xea\xbf\xe1\xc4f\x04\xcd\xde\x15\xe9\xfcG\xdd\xf3\x86\xc3\xc4R\xa1\xf0\xeb\xeb\x1f\'\xdd\x84\x9b\xa8\\\xd5\xfc\x9f\xd4q<\xd8\x0b\xb4\x04\x03\x9b8\x937\xb3B\x1e"\xf2'

