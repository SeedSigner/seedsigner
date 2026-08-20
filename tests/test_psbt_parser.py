import pytest
import random

from binascii import a2b_base64
from copy import deepcopy
from unittest.mock import patch
from embit import bip32
from embit.networks import NETWORKS
from embit.psbt import PSBT, DerivationPath
from embit.descriptor import Descriptor

from seedsigner.models.psbt_parser import PSBTParser
from seedsigner.models.seed import Seed
from seedsigner.models.settings_definition import SettingsConstants

from psbt_testing_util import PSBTTestData, create_output



class TestPSBTParser:
    """
    Exhaustively test all supported script input and output types.
    """
    seed = PSBTTestData.seed

    def run_basic_test(self, psbt_base64: str, change_data: str, self_transfer_data: str):
        """
        Constructs a series of test psbts that use the specified `psbt_base64` for the input(s).

        * A spend to each recipient type + specified `change_data`
        * Self-transfer back to sender via the `self_transfer_data`
        * A full spend (no change) to each recipient type
        * 1 mega psbt with an output to each recipient type + specified `change_data`
        """
        psbt: PSBT = PSBT.parse(a2b_base64(psbt_base64))
        input_amount = sum([inp.utxo.value for inp in psbt.inputs])
        recipient_amount = random.randint(200_000, 90_000_000)
        fee_amount = 5_000
        change_output = create_output(change_data, input_amount - recipient_amount - fee_amount)

        # Spend the input(s) to each supported recipient type + change
        for output in PSBTTestData.ALL_EXTERNAL_OUTPUTS:
            psbt.outputs.clear()
            psbt.outputs.append(create_output(output, recipient_amount))
            psbt.outputs.append(change_output)

            assert len(psbt.outputs) == 2
            psbt_parser = PSBTParser(p=psbt, seed=self.seed, network=SettingsConstants.REGTEST)
            assert psbt_parser.num_inputs == len(psbt.inputs)
            assert psbt_parser.input_amount == input_amount
            assert psbt_parser.num_destinations == 1
            assert psbt_parser.num_change_outputs == 1
            assert psbt_parser.spend_amount == recipient_amount
            assert psbt_parser.change_amount == input_amount - recipient_amount - fee_amount
            assert psbt_parser.fee_amount == fee_amount
            assert psbt_parser.input_amount == psbt_parser.spend_amount + psbt_parser.change_amount + psbt_parser.fee_amount
        
        # Internally cycle the input(s) back to sender via the `self_transfer_data`
        psbt.outputs.clear()
        psbt.outputs.append(create_output(self_transfer_data, input_amount - fee_amount))

        assert len(psbt.outputs) == 1
        psbt_parser = PSBTParser(p=psbt, seed=self.seed, network=SettingsConstants.REGTEST)
        assert psbt_parser.num_inputs == len(psbt.inputs)
        assert psbt_parser.input_amount == input_amount
        assert psbt_parser.num_destinations == 0    # No external recipients == no destinations
        assert psbt_parser.num_change_outputs == 1  # PSBTParser considers self-transfers == change
        assert psbt_parser.spend_amount == 0        # No external recipients == nothing spent (ignores fee)
        assert psbt_parser.change_amount == input_amount - fee_amount  # PSBTParser considers self-transfers == change
        assert psbt_parser.fee_amount == fee_amount
        assert psbt_parser.input_amount == psbt_parser.spend_amount + psbt_parser.change_amount + psbt_parser.fee_amount

        # Now do full spends with no change
        fee_amount = random.randint(5_000, 100_000)
        recipient_amount = input_amount - fee_amount

        for output in PSBTTestData.ALL_EXTERNAL_OUTPUTS:
            psbt.outputs.clear()
            psbt.outputs.append(create_output(output, recipient_amount))

            assert len(psbt.outputs) == 1
            psbt_parser = PSBTParser(p=psbt, seed=self.seed, network=SettingsConstants.REGTEST)
            assert psbt_parser.num_inputs == len(psbt.inputs)
            assert psbt_parser.input_amount == input_amount
            assert psbt_parser.num_destinations == 1
            assert psbt_parser.num_change_outputs == 0
            assert psbt_parser.spend_amount == recipient_amount
            assert psbt_parser.change_amount == 0
            assert psbt_parser.fee_amount == fee_amount
            assert psbt_parser.input_amount == psbt_parser.spend_amount + psbt_parser.change_amount + psbt_parser.fee_amount

        # Now try a single mega psbt with ALL the outputs at once
        psbt.outputs.clear()
        change_amount = input_amount - fee_amount
        for output in PSBTTestData.ALL_EXTERNAL_OUTPUTS:
            output_amount = random.randint(200_000, int(change_amount / 2))
            psbt.outputs.append(create_output(output, output_amount))
            change_amount -= output_amount

        # Don't forget the change!        
        psbt.outputs.append(create_output(change_data, change_amount))

        assert len(psbt.outputs) == len(PSBTTestData.ALL_EXTERNAL_OUTPUTS) + 1
        psbt_parser = PSBTParser(p=psbt, seed=self.seed, network=SettingsConstants.REGTEST)
        assert psbt_parser.num_inputs == len(psbt.inputs)
        assert psbt_parser.input_amount == input_amount
        assert psbt_parser.num_destinations == len(PSBTTestData.ALL_EXTERNAL_OUTPUTS)
        assert psbt_parser.num_change_outputs == 1
        assert psbt_parser.spend_amount == input_amount - change_amount - fee_amount
        assert psbt_parser.change_amount == change_amount
        assert psbt_parser.fee_amount == fee_amount
        assert psbt_parser.input_amount == psbt_parser.spend_amount + psbt_parser.change_amount + psbt_parser.fee_amount


    def test_singlesig_native_segwit(self):
        self.run_basic_test(PSBTTestData.SINGLE_SIG_NATIVE_SEGWIT_1_INPUT, PSBTTestData.SINGLE_SIG_NATIVE_SEGWIT_CHANGE, PSBTTestData.SINGLE_SIG_NATIVE_SEGWIT_SELF_TRANSFER)

    def test_singlesig_nested_segwit(self):
        self.run_basic_test(PSBTTestData.SINGLE_SIG_NESTED_SEGWIT_1_INPUT, PSBTTestData.SINGLE_SIG_NESTED_SEGWIT_CHANGE, PSBTTestData.SINGLE_SIG_NESTED_SEGWIT_SELF_TRANSFER)

    def test_singlesig_taproot(self):
        self.run_basic_test(PSBTTestData.SINGLE_SIG_TAPROOT_1_INPUT, PSBTTestData.SINGLE_SIG_TAPROOT_CHANGE, PSBTTestData.SINGLE_SIG_TAPROOT_SELF_TRANSFER)

    def test_singlesig_legacy_p2pkh(self):
        self.run_basic_test(PSBTTestData.SINGLE_SIG_LEGACY_P2PKH_1_INPUT, PSBTTestData.SINGLE_SIG_LEGACY_P2PKH_CHANGE, PSBTTestData.SINGLE_SIG_LEGACY_P2PKH_SELF_TRANSFER)

    def test_multisig_native_segwit(self):
        self.run_basic_test(PSBTTestData.MULTISIG_NATIVE_SEGWIT_1_INPUT, PSBTTestData.MULTISIG_NATIVE_SEGWIT_CHANGE, PSBTTestData.MULTISIG_NATIVE_SEGWIT_SELF_TRANSFER)

    def test_multisig_nested_segwit(self):
        self.run_basic_test(PSBTTestData.MULTISIG_NESTED_SEGWIT_1_INPUT, PSBTTestData.MULTISIG_NESTED_SEGWIT_CHANGE, PSBTTestData.MULTISIG_NESTED_SEGWIT_SELF_TRANSFER)

    def test_multisig_legacy_p2sh(self):
        self.run_basic_test(PSBTTestData.MULTISIG_LEGACY_P2SH_1_INPUT, PSBTTestData.MULTISIG_LEGACY_P2SH_CHANGE, PSBTTestData.MULTISIG_LEGACY_P2SH_SELF_TRANSFER)


    def test_has_matching_input_fingerprint(self):
        """
        PSBTParser should correctly identify when a psbt contains an input that matches a
        given Seed's fingerprint.
        """
        wrong_seed = Seed(["bacon"] * 24)
        for input in PSBTTestData.ALL_INPUTS:
            psbt = PSBT.parse(a2b_base64(input))
            assert PSBTParser.has_matching_input_fingerprint(psbt, PSBTTestData.seed)
            assert PSBTParser.has_matching_input_fingerprint(psbt, wrong_seed) == False

        # The other keys in the multisig inputs should also match        
        for input in PSBTTestData.MULTISIG_INPUTS:
            psbt = PSBT.parse(a2b_base64(input))
            assert PSBTParser.has_matching_input_fingerprint(psbt, PSBTTestData.multisig_key_2)
            assert PSBTParser.has_matching_input_fingerprint(psbt, PSBTTestData.multisig_key_3)


    def test_missing_fingerprint_handling(self):
        """
        PSBTParser should correctly handle PSBTs with missing fingerprints (created from XPUB-only imports, 
        without derivation path) by matching public keys against the seed and filling in correct fingerprints.
        """
        for input in PSBTTestData.ALL_INPUTS:
            psbt = PSBT.parse(a2b_base64(input))
            
            # Set fingerprints to zero to simulate XPUB-only import (missing fingerprint)
            from embit.psbt import DerivationPath
            for inp in psbt.inputs:
                for pub, derivation in inp.bip32_derivations.items():
                    inp.bip32_derivations[pub] = DerivationPath(
                        fingerprint=b"\x00\x00\x00\x00",
                        derivation=derivation.derivation
                    )

                for pub, (leaf_hashes, derivation) in inp.taproot_bip32_derivations.items():
                    inp.taproot_bip32_derivations[pub] = (leaf_hashes, DerivationPath(
                        fingerprint=b"\x00\x00\x00\x00",
                        derivation=derivation.derivation
                    ))
            
            # Test that has_matching_input_fingerprint can correctly identify that an input 
            # from the psbt does belong to the provided seed, even when the fingerprints 
            # (in the inputs' bip32 derivations) have been zeroed out.
            assert PSBTParser.has_matching_input_fingerprint(psbt, PSBTTestData.seed, SettingsConstants.REGTEST)
            
            # Test that it correctly rejects wrong seeds
            wrong_seed = Seed(["bacon"] * 24)
            assert not PSBTParser.has_matching_input_fingerprint(psbt, wrong_seed, SettingsConstants.REGTEST)
            
            # Test the PSBTParser's ability to fill missing fingerprints during parsing
            parser = PSBTParser(p=psbt, seed=PSBTTestData.seed, network=SettingsConstants.REGTEST)
            
            # Verify fingerprints were correctly filled after parsing
            seed_fingerprint = parser.seed.get_fingerprint(SettingsConstants.REGTEST)
            
            for inp in parser.psbt.inputs:
                for pub, derivation in inp.bip32_derivations.items():
                    from binascii import hexlify
                    fingerprint_hex = hexlify(derivation.fingerprint).decode()
                    
                    # Check if this public key derives from the current seed
                    derived_key = parser.root.derive(derivation.derivation)
                    if derived_key.key.sec() == pub.sec():
                        # This pubkey derives from current seed, should have current seed's fingerprint
                        assert fingerprint_hex == seed_fingerprint, f"Expected {seed_fingerprint}, got {fingerprint_hex} for pubkey that derives from current seed"
                    else:
                        # This pubkey doesn't derive from current seed, should remain 00000000
                        assert fingerprint_hex == "00000000"

                # Also check Taproot derivations
                for pub, (leaf_hashes, derivation) in inp.taproot_bip32_derivations.items():
                    from binascii import hexlify
                    fingerprint_hex = hexlify(derivation.fingerprint).decode()
                    
                    # Check if this public key derives from the current seed
                    derived_key = parser.root.derive(derivation.derivation)
                    if derived_key.key.sec() == pub.sec():
                        # This pubkey derives from current seed, should have current seed's fingerprint
                        assert fingerprint_hex == seed_fingerprint, f"Expected {seed_fingerprint}, got {fingerprint_hex} for taproot pubkey that derives from current seed"
                    else:
                        # This pubkey doesn't derive from current seed, should remain 00000000
                        assert fingerprint_hex == "00000000"


    def test_trim_and_sig_count(self):
        """
        PSBTParser should correctly trim a psbt of all unnecessary data and count the number of
        signatures in the psbt.
        """
        output = create_output(PSBTTestData.SINGLE_SIG_NATIVE_SEGWIT_RECEIVE, 100_000)
        for input in PSBTTestData.ALL_INPUTS:
            psbt: PSBT = PSBT.parse(a2b_base64(input))
            psbt.outputs.append(output)
            psbt.sign_with(bip32.HDKey.from_seed(self.seed.seed_bytes))
            assert PSBTParser.sig_count(psbt) == 1

            # TODO: What can we test for before/after trimming?
            PSBTParser.trim(psbt)

            if input in PSBTTestData.MULTISIG_INPUTS:
                psbt.sign_with(bip32.HDKey.from_seed(PSBTTestData.multisig_key_2.seed_bytes))
                assert PSBTParser.sig_count(psbt) == 2

                psbt.sign_with(bip32.HDKey.from_seed(PSBTTestData.multisig_key_3.seed_bytes))
                assert PSBTParser.sig_count(psbt) == 3


    def test_verify_multisig_output(self):
        """
        PSBTParser should correctly verify multisig change and self-transfer outputs against the
        provided descriptor or fail to verify if we provide the wrong descriptor.
        """
        multisig_inputs = [
            PSBTTestData.MULTISIG_NATIVE_SEGWIT_1_INPUT,
            PSBTTestData.MULTISIG_NESTED_SEGWIT_1_INPUT,
            PSBTTestData.MULTISIG_LEGACY_P2SH_1_INPUT
        ]
        change_outputs =  [
            PSBTTestData.MULTISIG_NATIVE_SEGWIT_CHANGE,
            PSBTTestData.MULTISIG_NESTED_SEGWIT_CHANGE,
            PSBTTestData.MULTISIG_LEGACY_P2SH_CHANGE
        ]
        self_transfer_outputs = [
            PSBTTestData.MULTISIG_NATIVE_SEGWIT_SELF_TRANSFER,
            PSBTTestData.MULTISIG_NESTED_SEGWIT_SELF_TRANSFER,
            PSBTTestData.MULTISIG_LEGACY_P2SH_SELF_TRANSFER
        ]
        descriptors = [
            PSBTTestData.MULTISIG_NATIVE_SEGWIT_DESCRIPTOR,
            PSBTTestData.MULTISIG_NESTED_SEGWIT_DESCRIPTOR,
            PSBTTestData.MULTISIG_LEGACY_P2SH_DESCRIPTOR
        ]

        for i, psbt_base64 in enumerate(multisig_inputs):
            # Construct a psbt with change & self-transfer outputs of the same type as the input
            psbt: PSBT = PSBT.parse(a2b_base64(psbt_base64))
            psbt.outputs.append(create_output(change_outputs[i], 100_000))
            psbt.outputs.append(create_output(self_transfer_outputs[i], 100_000))
            psbt_parser = PSBTParser(p=psbt, seed=self.seed, network=SettingsConstants.REGTEST)

            # Attempt to verify the change & self-transfer outputs using the right and wrong descriptors
            for j, descriptor_str in enumerate(descriptors):
                descriptor = Descriptor.from_string(descriptor_str.replace("<0;1>", "{0,1}"))
                if i == j:
                    assert psbt_parser.verify_multisig_output(descriptor, change_num=0) == True
                    assert psbt_parser.verify_multisig_output(descriptor, change_num=1) == True  # self-transfer is considered change
                else:
                    assert psbt_parser.verify_multisig_output(descriptor, change_num=0) == False
                    assert psbt_parser.verify_multisig_output(descriptor, change_num=1) == False



# TODO: Refactor all tests to be in the TestPSBTParser class(?)
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
    tx = PSBT.parse(raw)
    
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



# TODO: Test no longer necessary now that we have exhaustive tests for all types above?
def test_p2sh_legacy_multisig():
    """
        Should correctly parse a legacy multisig p2sh (m/45') psbt.

        PSBT Tx, wallet, and keys
        - Legacy 2-of-3 multisig p2sh; same format as Unchained
        - Regtest xpubs:
            - 0f889044 m/45' tpubD8NkS3Gngj7L4FJRYrwojKhsx2seBhrNrXVdvqaUyvtVe1YDCVcziZVa9g3KouXz7FN5CkGBkoC16nmNu2HcG9ubTdtCbSW8DEXSMHmmu62 (aka "Zoe" test seed)
            - 03cd0a2b m/45' tpubD8HkLLgkdJkVitn1i9CN4HpFKJdom48iKm9PyiXYz5hivn1cGz6H3VeS6ncmCEgamvzQA2Qofu2YSTwWzvuaYWbJDEnvTUtj5R96vACdV6L (aka "Malcolm" test seed)
            - 769f695c m/45' tpubD98hRDKvtATTM8hy5Vvt5ZrvDXwJvrUZm1p1mTKDmd7FqUHY9Wj2k4X1CvxjjtTf3JoChWqYbnWjfkRJ65GQnpVJKbbMfjnGzCwoBUXafyM (aka "Unchained" test seed)

        - 2 Inputs
            - 199,661 sats
        - 3 Outputs
            - 1 Output spend to another wallet: 50,000 sats to bcrt1q8q5uk9z7ta08h8hvknysd5n80w6f7kuvk5ey2m
            - 1 Output internal self-cycle
                - addresss 2N5eN5vUpgsLHAGzKm2VfmYyvNwXmCug5dH
                - amount 90,000 sats
                - receive address is index 0/5
            - 1 Output change
                - addresss 2NEnA5emHw9Q6vHXr912hGMSPtnrwAMReLz)
                - amount 58,969 sats
                - change addresses is index 1/0
            - Fee 692 sats

        "Malcolm": better gown govern speak spawn vendor exercise item uncle odor sound cat
        "Zoe": sign sword lift deer ocean insect web lazy sick pencil start select
        "Unchained": slight affair prefer tenant vacant below drill govern surface science affair nut

    """
    descriptor = Descriptor.from_string("sh(sortedmulti(2,[0f889044/45h]tpubD8NkS3Gngj7L4FJRYrwojKhsx2seBhrNrXVdvqaUyvtVe1YDCVcziZVa9g3KouXz7FN5CkGBkoC16nmNu2HcG9ubTdtCbSW8DEXSMHmmu62/<0;1>/*,[03cd0a2b/45h]tpubD8HkLLgkdJkVitn1i9CN4HpFKJdom48iKm9PyiXYz5hivn1cGz6H3VeS6ncmCEgamvzQA2Qofu2YSTwWzvuaYWbJDEnvTUtj5R96vACdV6L/<0;1>/*,[769f695c/45h]tpubD98hRDKvtATTM8hy5Vvt5ZrvDXwJvrUZm1p1mTKDmd7FqUHY9Wj2k4X1CvxjjtTf3JoChWqYbnWjfkRJ65GQnpVJKbbMfjnGzCwoBUXafyM/<0;1>/*))#uardwtq4".replace("<0;1>", "{0,1}"))
    psbt_base64 = "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"
    raw = a2b_base64(psbt_base64)
    tx = PSBT.parse(raw)

    # 03cd0a2b test seed
    mnemonic = "better gown govern speak spawn vendor exercise item uncle odor sound cat".split()
    seed = Seed(mnemonic)
    assert seed.get_fingerprint() == "03cd0a2b"

    psbt_parser = PSBTParser(p=tx, seed=seed, network=SettingsConstants.REGTEST)

    assert psbt_parser.spend_amount == 50000
    assert psbt_parser.change_amount == 90000 + 58969
    assert psbt_parser.fee_amount == 692

    assert psbt_parser.destination_addresses == ['bcrt1q8q5uk9z7ta08h8hvknysd5n80w6f7kuvk5ey2m']
    assert psbt_parser.destination_amounts == [50000]

    assert psbt_parser.get_change_data(0)['address'] == '2NEnA5emHw9Q6vHXr912hGMSPtnrwAMReLz'
    assert psbt_parser.get_change_data(0)["amount"] == 58969

    assert psbt_parser.get_change_data(1)['address'] == '2N5eN5vUpgsLHAGzKm2VfmYyvNwXmCug5dH'
    assert psbt_parser.get_change_data(1)["amount"] == 90000

    # We should be able to verify the change addr
    assert psbt_parser.verify_multisig_output(descriptor, 0)

    # And the self-transfer receive addr
    assert psbt_parser.verify_multisig_output(descriptor, 1)



# TODO: Test no longer necessary now that we have exhaustive tests for all types above?
def test_p2sh_p2wpkh_nested_segwit():
    """
        Should correctly parse a nested segwit (m/49'/1'/0') psbt.

        PSBT Tx, wallet, and keys
        - nested segwit single sig
        - Regtest xpubs:
            - c751dc07 c751dc07 tpubDDS23bf7c9mdfWpuvA61HHCYDusq25UtMNYsFagKPNMNWHSm8bvwmNNP2KSpivN3gQWAK8fhDFk3dzgoBn9rPoMncKxJuqNAv7sJMShbZ6i

        - 1 Inputs
            - 149,009 sats
        - 2 Outputs
            - 1 Output spend to another wallet: 93,000 sats to tb1qs7mdpjq7g7zq46vvycr8d6udc7za726ut8har9krfxpnc7kr04gqmdy2e4
            - 1 Output change
                - addresss 2Mz3MthXyM4YDjLPw1V4PAacKt4pD8Cz8N3)
                - amount 55,832 sats
                - change addresses is index 1/1
            - Fee 177 sats

        seed: goddess rough corn exclude cream trial fee trumpet million prevent gaze power
        passphrase: test

    """

    descriptor = Descriptor.from_string("sh(wpkh([c751dc07/49h/1h/0h]tpubDDS23bf7c9mdfWpuvA61HHCYDusq25UtMNYsFagKPNMNWHSm8bvwmNNP2KSpivN3gQWAK8fhDFk3dzgoBn9rPoMncKxJuqNAv7sJMShbZ6i/<0;1>/*))#7sn8gf37".replace("<0;1>", "{0,1}"))
    psbt_base64 = "cHNidP8BAH4CAAAAAXfY5crHl+bXtTvKvdo2MaFQeIXw+P+3kzZwBRgw84lFAQAAAAD9////AhjaAAAAAAAAF6kUSop8lEmO4FB1AyV1GJe2bygA7ASHSGsBAAAAAAAiACCHttDIHkeECumMJgZ2643Hhd8rXFnv0ZbDSYM8esN9UIouEwBPAQQ1h88Dv3UWAIAAAACfHgAYuw3ODwXCSP0valI9edAB1t3EInR2TXkbOd+F+AJgmJs8XUkZD5zQAgd3+/ijOqVphlWUMzxDnRorBQYEgxDHUdwHMQAAgAEAAIAAAACAAAEBIBFGAgAAAAAAF6kU7ijES3iWT8u0+44/blPlLfh9WkyHAQMEAQAAAAEEFgAUX7JspW1r0gC+WkUHwGABJ8DU9f8iBgO1/adRC+r8XJ/bjnfdwk3740n0m8gE3+xN8GHsNrxDUxjHUdwHMQAAgAEAAIAAAACAAQAAAAAAAAAAAQAWABT8V9vY29XR8niVYdVSF9H4zRTAbiICArH6DjPShnzXiaAnc2BR1f61QQliH0BOhqAvksByf3e9GMdR3AcxAACAAQAAgAAAAIABAAAAAQAAAAAA"
    raw = a2b_base64(psbt_base64)
    tx = PSBT.parse(raw)

    # 03cd0a2b test seed
    mnemonic = "goddess rough corn exclude cream trial fee trumpet million prevent gaze power".split()
    seed = Seed(mnemonic=mnemonic, passphrase="test")
    assert seed.get_fingerprint() == "c751dc07"

    psbt_parser = PSBTParser(p=tx, seed=seed, network=SettingsConstants.TESTNET)

    assert psbt_parser.spend_amount == 93000
    assert psbt_parser.change_amount == 55832
    assert psbt_parser.fee_amount == 177

    assert psbt_parser.destination_addresses == ['tb1qs7mdpjq7g7zq46vvycr8d6udc7za726ut8har9krfxpnc7kr04gqmdy2e4']
    assert psbt_parser.destination_amounts == [93000]

    assert psbt_parser.get_change_data(0)['address'] == '2Mz3MthXyM4YDjLPw1V4PAacKt4pD8Cz8N3'
    assert psbt_parser.get_change_data(0)["amount"] == 55832

    # We should be able to verify the change addr
    assert psbt_parser.verify_multisig_output(descriptor, 0)



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
    tx = PSBT.parse(raw)

    mnemonic = "model ensure search plunge galaxy firm exclude brain satoshi meadow cable roast".split()
    pw = ""
    seed = Seed(mnemonic, passphrase=pw)

    psbt_parser = PSBTParser(p=tx, seed=seed, network=SettingsConstants.REGTEST)

    # Remember to do the comparison as bytes
    assert psbt_parser.op_return_data == "Chancellor on the brink of third bailout".encode()

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



class TestPSBTParserOptimizations:
    """
    Guard tests for the parse-time optimizations in PSBTParser: that each one actually
    takes effect, and that none of them changes the result of a parse.
    """
    seed = PSBTTestData.seed

    def _root(self, seed: Seed = None) -> bip32.HDKey:
        if seed is None:
            seed = self.seed
        return bip32.HDKey.from_seed(
            seed.seed_bytes, version=NETWORKS["main"]["xprv"])


    def assert_same_parse_result(self, parser_a: PSBTParser, parser_b: PSBTParser):
        """
        Asserts that two parses produced the same result, field by field so that a failure
        names the exact field that differs.

        The fill path writes recovered fingerprints back into the psbt, so the serialized
        psbt is compared too, not just the parser's own attributes.
        """
        assert parser_a.policy == parser_b.policy
        assert parser_a.input_amount == parser_b.input_amount
        assert parser_a.spend_amount == parser_b.spend_amount
        assert parser_a.change_amount == parser_b.change_amount
        assert parser_a.fee_amount == parser_b.fee_amount
        assert parser_a.num_inputs == parser_b.num_inputs
        assert parser_a.destination_addresses == parser_b.destination_addresses
        assert parser_a.destination_amounts == parser_b.destination_amounts
        assert parser_a.change_data == parser_b.change_data
        assert parser_a.op_return_data == parser_b.op_return_data
        assert parser_a.psbt.serialize() == parser_b.psbt.serialize()


    def cache_size_recorder(self, cache_sizes: list):
        """
        Returns a stand-in for _derive_with_cache that derives exactly as the real one
        does, but appends the cache's size to cache_sizes on the way out of every call.

        The cache is a local inside parse(), so intercepting the calls it gets handed to
        is the only way to see how large it grew.
        """
        real_derive_with_cache = PSBTParser._derive_with_cache

        def recorded(parent_key, derivation_path, cache=None):
            derived_key = real_derive_with_cache(parent_key, derivation_path, cache)
            cache_sizes.append(len(cache))
            return derived_key

        return recorded


    def test_my_fingerprint_equals_child0_fingerprint(self):
        """
        Reading my_fingerprint in place of child(0).fingerprint is byte-identical,
        because HDKey.child(0) sets its .fingerprint to hash160(parent.sec())[:4],
        which is exactly parent.my_fingerprint.

        This is really a unit test / regression test against embit itself, but it is worth
        testing here.
        """
        root = self._root()
        assert root.my_fingerprint == root.child(0).fingerprint


    def test_zero_fingerprint_fill_over_many_inputs(self, monkeypatch):
        """
        The inputs in this test have their fingerprints blanked (set to all zero), which
        should then require one full derivation per input to work out whether that input
        is ours.

        The artificial inputs in this test share the same full derivation path so each
        level should only be derived once total rather than once per input.
        """
        psbt = PSBT.parse(a2b_base64(PSBTTestData.SINGLE_SIG_NATIVE_SEGWIT_1_INPUT))
        master_fingerprint = self._root().my_fingerprint

        # Sanity check that this artificial psbt has no outputs. We have to make sure that
        # the derivation counts at the end of the test were only for inputs, not outputs.
        assert len(psbt.outputs) == 0, "fixture is expected to have no outputs"

        # Artificially boost this test psbt to 10 total inputs from the same wallet
        for _ in range(9):
            psbt.inputs.append(deepcopy(psbt.inputs[0]))

        # Zero out all of the inputs' fingerprints
        num_zeroed = 0
        for inp in psbt.inputs:
            for pub, dp in list(inp.bip32_derivations.items()):
                inp.bip32_derivations[pub] = DerivationPath(b"\x00\x00\x00\x00", dp.derivation)
                num_zeroed += 1
        assert num_zeroed == len(psbt.inputs), "fixture did not yield one derivation per input"

        num_levels = len(list(psbt.inputs[0].bip32_derivations.values())[0].derivation)

        # Attach a counter to track every level actually derived during the parse
        num_derivations = 0
        uncounted_child = bip32.HDKey.child
        def counting_child(self, index, hardened=False):
            nonlocal num_derivations  # reference the above var outside the function scope
            num_derivations += 1
            return uncounted_child(self, index, hardened)
        monkeypatch.setattr(bip32.HDKey, "child", counting_child)

        # Instantiating the parser with the psbt will automatically fill in the zeroed
        # fingerprints.
        PSBTParser(psbt, self.seed, network=SettingsConstants.MAINNET)

        # All 10 inputs share the one derivation path, so each of its levels should have
        # been derived exactly once between them, rather than once per input.
        assert num_derivations == num_levels

        # Sanity check: num_derivations could be correct when just ONE of the ten inputs
        # was processed. Confirm that EVERY input really was processed by verifying that
        # each input was filled in with the correct fingerprint.
        for inp in psbt.inputs:
            for pub, dp in inp.bip32_derivations.items():
                assert dp.fingerprint == master_fingerprint


    def test_derive_with_cache_does_not_cross_parent_keys(self):
        """
        Multisig traverses the same relative derivation path below every cosigner's
        account xpub. Verify that the cache properly keeps the parents' cache data
        separate despite having derivations that share the same relative path.
        """
        # Two cosigners' account xpubs from the multisig test fixtures
        cosigner_a_xpub = self._root(PSBTTestData.multisig_key_2).derive("m/48h/0h/0h/2h").to_public()
        cosigner_b_xpub = self._root(PSBTTestData.multisig_key_3).derive("m/48h/0h/0h/2h").to_public()

        # The receive address at index 5 is: m/48h/0h/0h/2h/0/5. The parent xpubs already
        # have the first 4 levels derived, so this operation is only the final two levels.
        receive_index_5 = [0, 5]
        cache = {}

        # The cache here isn't providing any speedup (there are no derivations in the
        # cache to take advantage of), but we're just testing that the cache doesn't
        # confuse/combine the two cosigners' derivation data.
        from_a = PSBTParser._derive_with_cache(cosigner_a_xpub, receive_index_5, cache)
        from_b = PSBTParser._derive_with_cache(cosigner_b_xpub, receive_index_5, cache)

        # Two levels should have been added for each cosigner
        assert len(cache) == 4

        # The resulting derived child keys should be different
        assert from_a.key.sec() != from_b.key.sec()

        # The result derived with the cache must be identical to deriving from the xpub
        # directly.
        assert from_a.key.sec() == cosigner_a_xpub.derive(receive_index_5).key.sec()
        assert from_b.key.sec() == cosigner_b_xpub.derive(receive_index_5).key.sec()


    def test_get_cosigners_identical_with_and_without_cache(self):
        """
        The cache is transparent to callers: _get_cosigners returns the same cosigner
        list whether it derives every level itself or reads them back out of the cache.
        """
        psbt = PSBT.parse(a2b_base64(PSBTTestData.MULTISIG_NATIVE_SEGWIT_1_INPUT))
        inp = psbt.inputs[0]
        pubkeys = list(inp.bip32_derivations.keys())

        # No cache at all; every level is derived directly
        uncached = PSBTParser._get_cosigners(pubkeys, inp.bip32_derivations, psbt.xpubs, None)

        # An empty cache still has to derive every level, but now stores each one
        child_key_derivation_cache = {}
        populating_the_cache = PSBTParser._get_cosigners(pubkeys, inp.bip32_derivations, psbt.xpubs, child_key_derivation_cache)

        # 3 cosigners x 2 levels each
        assert len(child_key_derivation_cache) == 6

        # The same call against the now-populated cache reads those levels back instead
        # of deriving them. Each level sits below a different cosigner's xpub, so a cache
        # that confused parents would return the wrong cosigner here.
        reading_from_the_cache = PSBTParser._get_cosigners(pubkeys, inp.bip32_derivations, psbt.xpubs, child_key_derivation_cache)

        assert populating_the_cache == uncached
        assert reading_from_the_cache == uncached


    def test_cache_does_not_change_parse_output(self):
        """
        The whole point of the cache is that it changes nothing at all. Parse the same
        psbt twice — once normally, once with the cache discarded so that every derivation
        falls through to embit's own HDKey.derive() — and require identical parser state
        and identical resulting psbt bytes.

        Single-sig and multisig each get a run because they reach the cache from different
        starting points: single-sig traverses down from our own root, multisig down from
        each cosigner's account xpub.
        """
        def build_psbt(input_base64: str, change_hex: str) -> PSBT:
            # A fresh psbt for each parse: the base psbt plus its change output, twice.
            psbt = PSBT.parse(a2b_base64(input_base64))
            psbt.outputs.append(create_output(change_hex, 10_000))

            # Add a duplicate output to ensure that the cache yields some hits; the second
            # output will traverse the same levels the first one just cached.
            psbt.outputs.append(create_output(change_hex, 10_000))
            return psbt

        def assert_cache_makes_no_difference(input_base64: str, change_hex: str):
            # Store the real function before the patches below replace it. Each replacement
            # still needs access to the real function to do the actual deriving.
            real_derive_with_cache = PSBTParser._derive_with_cache

            # This version of the replacement will derive exactly as the real cache-backed
            # function does, but will also record the cache it was handed on each call.
            caches_received = []
            def recording_derive_with_cache(parent_key, derivation_path, cache=None):
                caches_received.append(cache)
                return real_derive_with_cache(parent_key, derivation_path, cache)

            with patch.object(PSBTParser, "_derive_with_cache", staticmethod(recording_derive_with_cache)):
                with_cache = PSBTParser(
                    build_psbt(input_base64, change_hex), self.seed, network=SettingsConstants.REGTEST)

            # Sanity check: the cache was actually available during the parse
            assert any(cache is not None for cache in caches_received)

            # And then this version discards the cache, which sends the real function down
            # its no-cache branch.
            def cache_free_derive(parent_key, derivation_path, cache=None):
                return real_derive_with_cache(parent_key, derivation_path)

            with patch.object(PSBTParser, "_derive_with_cache", staticmethod(cache_free_derive)):
                without_cache = PSBTParser(
                    build_psbt(input_base64, change_hex), self.seed, network=SettingsConstants.REGTEST)

            # Regardless of whether or not the cache was available, the resulting parser
            # state should be identical.
            self.assert_same_parse_result(with_cache, without_cache)

        assert_cache_makes_no_difference(PSBTTestData.SINGLE_SIG_NATIVE_SEGWIT_1_INPUT, PSBTTestData.SINGLE_SIG_NATIVE_SEGWIT_CHANGE)
        assert_cache_makes_no_difference(PSBTTestData.MULTISIG_NATIVE_SEGWIT_1_INPUT, PSBTTestData.MULTISIG_NATIVE_SEGWIT_CHANGE)


    def test_maxed_out_cache_does_not_change_parse_output(self):
        """
        There should be no effect on the parse output when the cache is maxed out.

        Parse a multisig and a single-sig psbt with the cache free to grow, then parse
        them again with the cap low enough that both hit the cap partway through. Verify
        that we get the identical parser state each time.
        """
        multisig_case = (PSBTTestData.MULTISIG_NATIVE_SEGWIT_1_INPUT, PSBTTestData.MULTISIG_NATIVE_SEGWIT_CHANGE)
        singlesig_case = (PSBTTestData.SINGLE_SIG_NATIVE_SEGWIT_1_INPUT, PSBTTestData.SINGLE_SIG_NATIVE_SEGWIT_CHANGE)

        def build_psbt(case: tuple) -> PSBT:
            # A fresh psbt for each parse: the case's base psbt plus its change output
            input_base64, change_hex = case
            psbt = PSBT.parse(a2b_base64(input_base64))
            psbt.outputs.append(create_output(change_hex, 10_000))
            return psbt

        # Record how large the cache grew over the course of each parse
        unconstrained_sizes = []
        with patch.object(PSBTParser, "_derive_with_cache", staticmethod(self.cache_size_recorder(unconstrained_sizes))):
            multisig_unconstrained = PSBTParser(build_psbt(multisig_case), self.seed, network=SettingsConstants.REGTEST)
            singlesig_unconstrained = PSBTParser(build_psbt(singlesig_case), self.seed, network=SettingsConstants.REGTEST)

        # Now constrain the cache enough that both psbts fill it partway through their
        # parse.
        cap = 3
        capped_sizes = []
        with patch.object(PSBTParser, "MAX_CACHED_DERIVATIONS", cap):
            with patch.object(PSBTParser, "_derive_with_cache", staticmethod(self.cache_size_recorder(capped_sizes))):
                multisig_capped = PSBTParser(build_psbt(multisig_case), self.seed, network=SettingsConstants.REGTEST)
                singlesig_capped = PSBTParser(build_psbt(singlesig_case), self.seed, network=SettingsConstants.REGTEST)

        self.assert_same_parse_result(multisig_unconstrained, multisig_capped)
        self.assert_same_parse_result(singlesig_unconstrained, singlesig_capped)

        # Sanity check: this test depends on the unconstrained cache actually being larger
        # than the capped cache's max.
        assert max(unconstrained_sizes) > cap
        assert max(capped_sizes) == cap


