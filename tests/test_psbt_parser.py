from seedsigner.models.psbt_parser import PSBTParser
from seedsigner.models.seed import Seed
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

    psbt_parser = PSBTParser(p=tx, seed=seed, network=SettingsConstants.REGTEST)

    assert psbt_parser.change_data == [
        {
            'output_index': 0,
            'address': 'bcrt1prz4g6saush37epdwhvwpu78td3q7yfz3xxz37axlx7udck6wracq3rwq30',
            'amount': 2871443918,
            'fingerprint': ['394aed14'],
            'derivation_path': ["m/86h/1h/0h/1/1"]}
        ]
    assert psbt_parser.spend_amount == 319049328
    assert psbt_parser.change_amount == 2871443918
    assert psbt_parser.destination_addresses == ['bcrt1p6p00wazu4nnqac29fvky6vhjnnhku5u2g9njss62rvy7e0yuperq86f5ek']
    assert psbt_parser.destination_amounts == [319049328]


def test_parse_op_return_content():
    """
        Should successfully parse the OP_RETURN content from a PSBT.

        PSBT Tx and Wallet Details
        - Single Sig Wallet P2WPKH (Native Segwit) with no passphrase
        - Regtest 0fb882ff m/84'/1'/0' tpubDCfk37PqcQx6nFtFVuYHvRLJHxvYj33NjHkKRyRmWyCjyJ64sYBXyVjsTHaLBp5GLhM91VBgJ8nKDWDu52J2xVRy64c7ybEjjyWQJuQGLcg
        - 1 Input
            - 99,992,460 sats
        - 2 Outputs
            - 1 Output back to self (bcrt1qvwkhakqhz7m7kmz6332avatsmdy32m644g86vv) of 99,992,296 sats
            - 1 OP_RETURN: "Chancellor on the brink of third bailout"
        - Fee 164 sats
    """
    psbt_base64 = "cHNidP8BAIYCAAAAATpQ10o+gKdZ8ThpKsbfHiHYn3NhvUrQ5DvW0ZWX8jKLAAAAAAD9////AujC9QUAAAAAFgAUY61+2BcXt+tsWoxV1nVw20kVb1UAAAAAAAAAACtqTChDaGFuY2VsbG9yIG9uIHRoZSBicmluayBvZiB0aGlyZCBiYWlsb3V0aQAAAE8BBDWHzwNXmUmVgAAAANRFa7R5gYD84Wbha3d1QnjgfYPOBw87on6cXS32WoyqAsPFtPxB7PRTdbujUnBPUVDh9YUBtwrl4nc0OcRNGvIyEA+4gv9UAACAAQAAgAAAAIAAAQB0AgAAAAGNFK/1X0fP5q+nu5XX7Tk2VRa0EL+jkGI9CHiJvsjZCgAAAAAA/f///wKMw/UFAAAAABYAFIpZMNnUU6cQt8Q0YpZ0pnvsSA5fAAAAAAAAAAAZakwWYml0Y29pbiBpcyBmcmVlIHNwZWVjaGgAAAABAR+Mw/UFAAAAABYAFIpZMNnUU6cQt8Q0YpZ0pnvsSA5fAQMEAQAAACIGAvxDI0eNI1oQ2AU69R7A0jf+hUdilWCgrWHgdzkqlaXMGA+4gv9UAACAAQAAgAAAAIAAAAAAAQAAAAAiAgK9qKtzGWyiRrpmupdA99NVLriz3GQy6cENbyD19sfl/hgPuIL/VAAAgAEAAIAAAACAAAAAAAIAAAAAAA=="

    raw = a2b_base64(psbt_base64)
    tx = psbt.PSBT.parse(raw)

    mnemonic = "model ensure search plunge galaxy firm exclude brain satoshi meadow cable roast".split()
    pw = ""
    seed = Seed(mnemonic, passphrase=pw)

    psbt_parser = PSBTParser(p=tx, seed=seed, network=SettingsConstants.REGTEST)

    # Remember to do the comparison as bytes
    assert psbt_parser.op_return == "Chancellor on the brink of third bailout".encode()

    # PSBT is an internal self-spend to the its own receive addr, but the parser categorizes it as "change"
    assert psbt_parser.change_data == [
        {
            'output_index': 0,
            'address': 'bcrt1qvwkhakqhz7m7kmz6332avatsmdy32m644g86vv',
            'amount': 99992296,
            'fingerprint': ['0fb882ff'],
            'derivation_path': ["m/84h/1h/0h/0/2"]}
        ]
    assert psbt_parser.spend_amount == 0  # This is a self-spend; no value being spent, other than the tx fee
    assert psbt_parser.change_amount == 99992296
    assert psbt_parser.destination_addresses == []
    assert psbt_parser.destination_amounts == []
