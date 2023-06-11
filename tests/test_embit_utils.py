import pytest

from seedsigner.models.settings_definition import SettingsConstants as SC
from seedsigner.helpers import embit_utils


def test_get_standard_derivation_path():
    """tests seedsigner.helpers.embit_utils.get_standard_derivation_path()"""

    vectors_args_expected = {
        # single sig
        tuple(): "m/84'/0'/0'",
        (SC.MAINNET,): "m/84'/0'/0'",
        (SC.MAINNET, SC.SINGLE_SIG, ): "m/84'/0'/0'",

        (SC.MAINNET, SC.SINGLE_SIG, SC.NATIVE_SEGWIT): "m/84'/0'/0'",
        (SC.TESTNET, SC.SINGLE_SIG, SC.NATIVE_SEGWIT): "m/84'/1'/0'",
        (SC.REGTEST, SC.SINGLE_SIG, SC.NATIVE_SEGWIT): "m/84'/1'/0'",

        (SC.MAINNET, SC.SINGLE_SIG, SC.NESTED_SEGWIT): "m/49'/0'/0'",
        (SC.TESTNET, SC.SINGLE_SIG, SC.NESTED_SEGWIT): "m/49'/1'/0'",
        (SC.REGTEST, SC.SINGLE_SIG, SC.NESTED_SEGWIT): "m/49'/1'/0'",

        (SC.MAINNET, SC.SINGLE_SIG, SC.TAPROOT): "m/86'/0'/0'",
        (SC.TESTNET, SC.SINGLE_SIG, SC.TAPROOT): "m/86'/1'/0'",
        (SC.REGTEST, SC.SINGLE_SIG, SC.TAPROOT): "m/86'/1'/0'",

        # multi sig
        (SC.MAINNET, SC.MULTISIG, SC.NATIVE_SEGWIT): "m/48'/0'/0'/2'",
        (SC.TESTNET, SC.MULTISIG, SC.NATIVE_SEGWIT): "m/48'/1'/0'/2'",
        (SC.REGTEST, SC.MULTISIG, SC.NATIVE_SEGWIT): "m/48'/1'/0'/2'",

        (SC.MAINNET, SC.MULTISIG, SC.NESTED_SEGWIT): "m/48'/0'/0'/1'",
        (SC.TESTNET, SC.MULTISIG, SC.NESTED_SEGWIT): "m/48'/1'/0'/1'",
        (SC.REGTEST, SC.MULTISIG, SC.NESTED_SEGWIT): "m/48'/1'/0'/1'",

        (SC.MAINNET, SC.MULTISIG, SC.TAPROOT): Exception,
        (SC.TESTNET, SC.MULTISIG, SC.TAPROOT): Exception,
        (SC.REGTEST, SC.MULTISIG, SC.TAPROOT): Exception,

        # nonsense arguments
        ("A",): Exception,
        ("B", "A"): Exception,
        ("C", "B", "A"): Exception,
        (True,): Exception,
        (False, True): Exception,
        (tuple(),): Exception,
    }
    func = embit_utils.get_standard_derivation_path

    print()
    for args, expected in vectors_args_expected.items():

        # test successful returns
        if type(expected) is str:
            # call with positional args
            print(f"asserting {func.__name__}(*{args}) == {repr(expected)}")
            assert func(*args) == expected

            # call with named args
            a_dict = {}
            if len(args) == 1: a_dict = {'network': args[0]}
            elif len(args) == 2: a_dict = {'network': args[0], 'wallet_type': args[1]}
            elif len(args) == 3: a_dict = {'network': args[0], 'wallet_type': args[1], 'script_type': args[2]}
            print(f"asserting {func.__name__}(**{a_dict}) == {repr(expected)}")
            assert func(**a_dict) == expected

        # test exceptions
        else: 
            # call with positional args
            with pytest.raises(expected):
                print(f"asserting {func.__name__}(*{args}) raises Exception")
                func(*args)

            # call with named args
            a_dict = {}
            if len(args) == 1: a_dict = {'network': args[0]}
            elif len(args) == 2: a_dict = {'network': args[0], 'wallet_type': args[1]}
            elif len(args) == 3: a_dict = {'network': args[0], 'wallet_type': args[1], 'script_type': args[2]}
            print(f"asserting {func.__name__}(**{a_dict}) raises Exception")
            with pytest.raises(expected):
                func(**a_dict)

def test_get_xpub():
    """tests seedsigner.helpers.embit_utils.get_xpub()"""

    from binascii import unhexlify
    from embit import bip39, bip32

    # test vectors originate from:
    #   https://github.com/bitcoin/bips/blob/master/bip-0032.mediawiki
    #   https://github.com/bitcoin/bips/blob/master/bip-0084.mediawiki
    #   https://github.com/satoshilabs/slips/blob/master/slip-0132.md
    #   https://github.com/bitcoin/bips/blob/master/bip-0049.mediawiki
    #   https://github.com/bitcoin/bips/blob/master/bip-0086.mediawiki
    vector_seeds = (
        unhexlify("000102030405060708090a0b0c0d0e0f"),
        unhexlify("fffcf9f6f3f0edeae7e4e1dedbd8d5d2cfccc9c6c3c0bdbab7b4b1aeaba8a5a29f9c999693908d8a8784817e7b7875726f6c696663605d5a5754514e4b484542"),
        unhexlify("4b381541583be4423346c643850da4b320e46a87ae3d2a4e6da11eba819cd4acba45d239319ac14f863b8d5ab5a0d0c64d2e8a1e7d1457df2e5a3c51c73235be"),
        unhexlify("3ddd5602285899a946114506157c7997e5444528f3003f6134712147db19b678"),
        bip39.mnemonic_to_seed('abandon '*11+'about'),
    )

    vectors_args_expected = {
        # https://github.com/bitcoin/bips/blob/master/bip-0032.mediawiki#test-vector-1
        (vector_seeds[0], "m/", "main"): "xpub661MyMwAqRbcFtXgS5sYJABqqG9YLmC4Q1Rdap9gSE8NqtwybGhePY2gZ29ESFjqJoCu1Rupje8YtGqsefD265TMg7usUDFdp6W1EGMcet8",
        (vector_seeds[0], "m/0'", "main"): "xpub68Gmy5EdvgibQVfPdqkBBCHxA5htiqg55crXYuXoQRKfDBFA1WEjWgP6LHhwBZeNK1VTsfTFUHCdrfp1bgwQ9xv5ski8PX9rL2dZXvgGDnw",
        (vector_seeds[0], "m/0h/1", "main"): "xpub6ASuArnXKPbfEwhqN6e3mwBcDTgzisQN1wXN9BJcM47sSikHjJf3UFHKkNAWbWMiGj7Wf5uMash7SyYq527Hqck2AxYysAA7xmALppuCkwQ",
        (vector_seeds[0], "m/0'/1/2h", "main"): "xpub6D4BDPcP2GT577Vvch3R8wDkScZWzQzMMUm3PWbmWvVJrZwQY4VUNgqFJPMM3No2dFDFGTsxxpG5uJh7n7epu4trkrX7x7DogT5Uv6fcLW5",
        (vector_seeds[0], "m/0'/1/2h/2", "main"): "xpub6FHa3pjLCk84BayeJxFW2SP4XRrFd1JYnxeLeU8EqN3vDfZmbqBqaGJAyiLjTAwm6ZLRQUMv1ZACTj37sR62cfN7fe5JnJ7dh8zL4fiyLHV",
        (vector_seeds[0], "m/0'/1/2h/2/1000000000", "main"): "xpub6H1LXWLaKsWFhvm6RVpEL9P4KfRZSW7abD2ttkWP3SSQvnyA8FSVqNTEcYFgJS2UaFcxupHiYkro49S8yGasTvXEYBVPamhGW6cFJodrTHy",

        # https://github.com/bitcoin/bips/blob/master/bip-0032.mediawiki#test-vector-2
        (vector_seeds[1], "m/", "main"): "xpub661MyMwAqRbcFW31YEwpkMuc5THy2PSt5bDMsktWQcFF8syAmRUapSCGu8ED9W6oDMSgv6Zz8idoc4a6mr8BDzTJY47LJhkJ8UB7WEGuduB",
        (vector_seeds[1], "m/0", "main"): "xpub69H7F5d8KSRgmmdJg2KhpAK8SR3DjMwAdkxj3ZuxV27CprR9LgpeyGmXUbC6wb7ERfvrnKZjXoUmmDznezpbZb7ap6r1D3tgFxHmwMkQTPH",
        (vector_seeds[1], "m/0/2147483647'", "main"): "xpub6ASAVgeehLbnwdqV6UKMHVzgqAG8Gr6riv3Fxxpj8ksbH9ebxaEyBLZ85ySDhKiLDBrQSARLq1uNRts8RuJiHjaDMBU4Zn9h8LZNnBC5y4a",
        (vector_seeds[1], "m/0/2147483647h/1", "main"): "xpub6DF8uhdarytz3FWdA8TvFSvvAh8dP3283MY7p2V4SeE2wyWmG5mg5EwVvmdMVCQcoNJxGoWaU9DCWh89LojfZ537wTfunKau47EL2dhHKon",
        (vector_seeds[1], "m/0/2147483647'/1/2147483646h", "main"): "xpub6ERApfZwUNrhLCkDtcHTcxd75RbzS1ed54G1LkBUHQVHQKqhMkhgbmJbZRkrgZw4koxb5JaHWkY4ALHY2grBGRjaDMzQLcgJvLJuZZvRcEL",
        (vector_seeds[1], "m/0/2147483647h/1/2147483646'/2", "main"): "xpub6FnCn6nSzZAw5Tw7cgR9bi15UV96gLZhjDstkXXxvCLsUXBGXPdSnLFbdpq8p9HmGsApME5hQTZ3emM2rnY5agb9rXpVGyy3bdW6EEgAtqt",

        # https://github.com/bitcoin/bips/blob/master/bip-0032.mediawiki#test-vector-3
        (vector_seeds[2], "m/", "main"): "xpub661MyMwAqRbcEZVB4dScxMAdx6d4nFc9nvyvH3v4gJL378CSRZiYmhRoP7mBy6gSPSCYk6SzXPTf3ND1cZAceL7SfJ1Z3GC8vBgp2epUt13",
        (vector_seeds[2], "m/0h", "main"): "xpub68NZiKmJWnxxS6aaHmn81bvJeTESw724CRDs6HbuccFQN9Ku14VQrADWgqbhhTHBaohPX4CjNLf9fq9MYo6oDaPPLPxSb7gwQN3ih19Zm4Y",

        # https://github.com/bitcoin/bips/blob/master/bip-0032.mediawiki#test-vector-4
        (vector_seeds[3], "m/", "main"): "xpub661MyMwAqRbcGczjuMoRm6dXaLDEhW1u34gKenbeYqAix21mdUKJyuyu5F1rzYGVxyL6tmgBUAEPrEz92mBXjByMRiJdba9wpnN37RLLAXa",
        (vector_seeds[3], "m/0'", "main"): "xpub69AUMk3qDBi3uW1sXgjCmVjJ2G6WQoYSnNHyzkmdCHEhSZ4tBok37xfFEqHd2AddP56Tqp4o56AePAgCjYdvpW2PU2jbUPFKsav5ut6Ch1m",
        (vector_seeds[3], "m/0h/1'", "main"): "xpub6BJA1jSqiukeaesWfxe6sNK9CCGaujFFSJLomWHprUL9DePQ4JDkM5d88n49sMGJxrhpjazuXYWdMf17C9T5XnxkopaeS7jGk1GyyVziaMt",

        #
        # embit_utils.get_xpub() returns the generic bip32 version "xpub", NOT the zpub/Zpub/ypub/Ypub extended versions
        #

        # https://github.com/bitcoin/bips/blob/master/bip-0084.mediawiki#test-vectors
        # https://github.com/satoshilabs/slips/blob/master/slip-0132.md#bitcoin-test-vectors
        (vector_seeds[4], "m/84'/0'/0'", "main"):
             bip32.HDKey.from_string("zpub6rFR7y4Q2AijBEqTUquhVz398htDFrtymD9xYYfG1m4wAcvPhXNfE3EfH1r1ADqtfSdVCToUG868RvUUkgDKf31mGDtKsAYz2oz2AGutZYs").to_base58(version=b'\x04\x88\xb2\x1e'),

        # https://github.com/satoshilabs/slips/blob/master/slip-0132.md#bitcoin-test-vectors
        (vector_seeds[4], "m/49'/0'/0'", "main"): 
             bip32.HDKey.from_string("ypub6Ww3ibxVfGzLrAH1PNcjyAWenMTbbAosGNB6VvmSEgytSER9azLDWCxoJwW7Ke7icmizBMXrzBx9979FfaHxHcrArf3zbeJJJUZPf663zsP").to_base58(version=b'\x04\x88\xb2\x1e'),
        
        # https://github.com/bitcoin/bips/blob/master/bip-0049.mediawiki#test-vectors
        (vector_seeds[4], "m/49'/1'/0'", "test"): 
             bip32.HDKey.from_string("upub5EFU65HtV5TeiSHmZZm7FUffBGy8UKeqp7vw43jYbvZPpoVsgU93oac7Wk3u6moKegAEWtGNF8DehrnHtv21XXEMYRUocHqguyjknFHYfgY").to_base58(version=b'\x04\x35\x87\xcf'),

        # https://github.com/bitcoin/bips/blob/master/bip-0086.mediawiki#test-vectors
        (vector_seeds[4], "m/86'/0'/0'", "main"): "xpub6BgBgsespWvERF3LHQu6CnqdvfEvtMcQjYrcRzx53QJjSxarj2afYWcLteoGVky7D3UKDP9QyrLprQ3VCECoY49yfdDEHGCtMMj92pReUsQ",

    }

    func = embit_utils.get_xpub
    for args, expected in vectors_args_expected.items():
        print("\nasserting...")

        # test calling w/o last param (default is "main")
        if args[2] == "main":
            print(f'  {func.__name__}({args[0]}, "{args[1]}") returns "{expected}"')
            assert str(func(args[0], args[1])) == expected

        # test calling w/ ordered params
        print(f'  {func.__name__}(*{args}) returns "{expected}"')
        assert str(func(*args)) == expected

        # test calling w/ named params
        print(f'  {func.__name__}(seed_bytes={args[0]}, derivation_path="{args[1]}", embit_network="{args[2]}") returns "{expected}"')
        assert str(func(seed_bytes=args[0], derivation_path=args[1], embit_network=args[2])) == expected
        
