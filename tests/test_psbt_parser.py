import pytest
from mock import MagicMock
from seedsigner.models import PSBTParser, Seed
from embit import psbt
from binascii import a2b_base64
from seedsigner.models.settings_definition import SettingsConstants

def test_p2tr_change_detection():
	""" Should successfully detect change in a p2tr to p2tr psbt spend
	
		PSBT Tx and Wallet Details
		- Single Sig Wallet P2TR (Taproot) with no passphrase
		- Regtest 394aed14 m/86'/1'/0' tpubDCawGrRg7YdHdFb9p4mmD8GBaZjJegL53FPFRrMkGoLcgLATJfksUs2y1Q7dVzixAkgecazsxEsUuyj3LyDw7eVVYHQyojwrc2hfesK4wXW
		- 1 Inputs
			- 3,190,493,401 sats
		- 2 Outputs
			- 1 Output spend to another wallet (bcrt1p6p00wazu4nnqac29fvky6vhjnnhku5u2g9njss62rvy7e0yuperq86f5ek) p2tr address
			- 1 Output change
				- addresss bcrt1prz4g6saush37epdwhvwpu78td3q7yfz3xxz37axlx7udck6wracq3rwq30)
				- amount 2,871,443,918 sats
				- Change addresses is index 1/1
			- Fee 155 sats
	"""
	
	psbt_base64 = "cHNidP8BAIkCAAAAAf8upuiIWF1VTgC/Q8ZWRrameRigaXpRcQcBe8ye+TK3AQAAAAAXCgAAAs7BJqsAAAAAIlEgGKqNQ7yF4+yFrrscHnjrbEHiJFExhR903ze43FtOH3BwTgQTAAAAACJRINBe93RcrOYO4UVLLE0y8pzvblOKQWcoQ0obCey8nA5GAAAAAE8BBDWHzwNMUx9OgAAAAJdr+WtwWfVa6IPbpKZ4KgRC0clbm11Gl155IPA27n2FAvQCrFGH6Ac2U0Gcy1IH5f5ltgUBDz2+fe8iqL6JzZdgEDlK7RRWAACAAQAAgAAAAIAAAQB9AgAAAAGAKOOUFIzw9pbRDaZ7F0DYhLImrdMn//OSm++ff5VNdAAAAAAAAQAAAAKsjLwAAAAAABYAFKEcuxvXmB3rWHSqSviP5mrKMZoL2RArvgAAAAAiUSBGU0Lg5fx/ECsB1Z4ZUqXQFSLFnlmpm0rm5R2l599h2AAAAAABASvZECu+AAAAACJRIEZTQuDl/H8QKwHVnhlSpdAVIsWeWambSublHaXn32HYAQMEAAAAACEWF7hZVn7pIDR429kAn/WDeQiWjZey1iGHztsL1H83QLMZADlK7RRWAACAAQAAgAAAAIABAAAAAAAAAAEXIBe4WVZ+6SA0eNvZAJ/1g3kIlo2XstYhh87bC9R/N0CzACEHbJdqWyMxF2eOPr6YRXUJmry04HUbgKyeM2IZeG+NI9AZADlK7RRWAACAAQAAgAAAAIABAAAAAQAAAAEFIGyXalsjMRdnjj6+mEV1CZq8tOB1G4CsnjNiGXhvjSPQAAA="
	
	raw = a2b_base64(psbt_base64)
	tx = psbt.PSBT.parse(raw)
	
	mnemonic = "goddess rough corn exclude cream trial fee trumpet million prevent gaze power".split()
	pw = ""
	seed = Seed(mnemonic, passphrase=pw)

	pp = PSBTParser(p=tx, seed=seed, network=SettingsConstants.REGTEST)

	assert pp.change_data == [
		{
			'output_index': 0,
			'address': 'bcrt1prz4g6saush37epdwhvwpu78td3q7yfz3xxz37axlx7udck6wracq3rwq30',
			'amount': 2871443918,
			'fingerprint': ['394aed14'],
			'derivation_path': ['m/86h/1h/0h/1/1']}
		]
	assert pp.spend_amount == 319049328
	assert pp.change_amount == 2871443918
	assert pp.destination_addresses == ['bcrt1p6p00wazu4nnqac29fvky6vhjnnhku5u2g9njss62rvy7e0yuperq86f5ek']
	assert pp.destination_amounts == [319049328]