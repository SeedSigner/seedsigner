import pytest

from seedsigner.models.settings_definition import SettingsConstants as SC
from seedsigner.helpers import embit_utils


def test_get_standard_derivation_path():
    """
    tests seedsigner.helpers.embit_utils.get_standard_derivation_path()
    """

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

        (SC.MAINNET, SC.SINGLE_SIG, SC.LEGACY_P2PKH): "m/44'/0'/0'",
        (SC.TESTNET, SC.SINGLE_SIG, SC.LEGACY_P2PKH): "m/44'/1'/0'",
        (SC.REGTEST, SC.SINGLE_SIG, SC.LEGACY_P2PKH): "m/44'/1'/0'",


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

        (SC.MAINNET, SC.MULTISIG, SC.LEGACY_P2PKH): "m/45'",

        # intentionally fall into exceptions
        (SC.MAINNET, SC.SINGLE_SIG, 'invalid'): Exception,
        (SC.MAINNET, SC.MULTISIG, 'invalid'): Exception,
        (SC.MAINNET, 'invalid', SC.NATIVE_SEGWIT): Exception,

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

        # test successful calls
        if type(expected) is str:
            # call with ordered params
            print(f"asserting {func.__name__}(*{args}) == {repr(expected)}")
            assert func(*args) == expected

            # call with named params
            a_dict = {}
            if len(args) == 1: a_dict = {'network': args[0]}
            elif len(args) == 2: a_dict = {'network': args[0], 'wallet_type': args[1]}
            elif len(args) == 3: a_dict = {'network': args[0], 'wallet_type': args[1], 'script_type': args[2]}
            print(f"asserting {func.__name__}(**{a_dict}) == {repr(expected)}")
            assert func(**a_dict) == expected

        # test exceptions
        else: 
            # call with ordered params
            with pytest.raises(expected):
                print(f"asserting {func.__name__}(*{args}) raises Exception")
                func(*args)

            # call with named params
            a_dict = {}
            if len(args) == 1: a_dict = {'network': args[0]}
            elif len(args) == 2: a_dict = {'network': args[0], 'wallet_type': args[1]}
            elif len(args) == 3: a_dict = {'network': args[0], 'wallet_type': args[1], 'script_type': args[2]}
            print(f"asserting {func.__name__}(**{a_dict}) raises Exception")
            with pytest.raises(expected):
                func(**a_dict)


def test_get_xpub():
    """
    tests seedsigner.helpers.embit_utils.get_xpub()
    """

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
        bip39.mnemonic_to_seed("abandon "*11 + "about"),
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

        # https://github.com/satoshilabs/slips/blob/master/slip-0132.md#bitcoin-test-vectors
        (vector_seeds[4], "m/44'/0'/0'", "main"): 
             bip32.HDKey.from_string("xpub6BosfCnifzxcFwrSzQiqu2DBVTshkCXacvNsWGYJVVhhawA7d4R5WSWGFNbi8Aw6ZRc1brxMyWMzG3DSSSSoekkudhUd9yLb6qx39T9nMdj").to_base58(version=b'\x04\x88\xb2\x1e'),

        # https://github.com/bitcoin/bips/blob/master/bip-0086.mediawiki#test-vectors
        (vector_seeds[4], "m/86'/0'/0'", "main"): "xpub6BgBgsespWvERF3LHQu6CnqdvfEvtMcQjYrcRzx53QJjSxarj2afYWcLteoGVky7D3UKDP9QyrLprQ3VCECoY49yfdDEHGCtMMj92pReUsQ",

    }
    func = embit_utils.get_xpub

    print()
    for args, expected in vectors_args_expected.items():
        print("\nasserting...")

        # call without optional params (default is "main")
        if args[2] == "main":
            print(f'  {func.__name__}({args[0]}, "{args[1]}") == "{expected}"')
            assert str(func(args[0], args[1])) == expected

        # call with ordered params
        print(f'  {func.__name__}(*{args}) == "{expected}"')
        assert str(func(*args)) == expected

        # call with named params
        print(f'  {func.__name__}(seed_bytes={args[0]}, derivation_path="{args[1]}", embit_network="{args[2]}") == "{expected}"')
        assert str(func(seed_bytes=args[0], derivation_path=args[1], embit_network=args[2])) == expected
        

def test_get_single_sig_address():
    """
    tests seedsigner.helpers.embit_utils.get_single_sig_address()
    """

    from embit.bip32 import HDKey

    # test vectors originate from:
    #   https://github.com/bitcoin/bips/blob/master/bip-0049.mediawiki
    #   https://github.com/satoshilabs/slips/blob/master/slip-0132.md
    #   https://iancoleman.io/bip39/
    #   https://github.com/bitcoin/bips/blob/master/bip-0086.mediawiki

    vectors_args_expected = {
        # https://github.com/satoshilabs/slips/blob/master/slip-0132.md#bitcoin-test-vectors (first payment address of native segwit on mainnet)
        (HDKey.from_string("zpub6rFR7y4Q2AijBEqTUquhVz398htDFrtymD9xYYfG1m4wAcvPhXNfE3EfH1r1ADqtfSdVCToUG868RvUUkgDKf31mGDtKsAYz2oz2AGutZYs"), "nat", 0, False, "main"):
            "bc1qcr8te4kr609gcawutmrza0j4xv80jy8z306fyu",
        # jdlcdl: derived via iancoleman test vector for first change address of native segwit on mainnet
        (HDKey.from_string("zpub6rFR7y4Q2AijBEqTUquhVz398htDFrtymD9xYYfG1m4wAcvPhXNfE3EfH1r1ADqtfSdVCToUG868RvUUkgDKf31mGDtKsAYz2oz2AGutZYs"), "nat", 0, True, "main"):
            "bc1q8c6fshw2dlwun7ekn9qwf37cu2rn755upcp6el",
        
        # https://github.com/satoshilabs/slips/blob/master/slip-0132.md#bitcoin-test-vectors (first payment address of nested segwit on mainnet)
        (HDKey.from_string("ypub6Ww3ibxVfGzLrAH1PNcjyAWenMTbbAosGNB6VvmSEgytSER9azLDWCxoJwW7Ke7icmizBMXrzBx9979FfaHxHcrArf3zbeJJJUZPf663zsP"), "nes", 0, False, "main"):
            "37VucYSaXLCAsxYyAPfbSi9eh4iEcbShgf",
        # jdlcdl: derived via iancoleman test vector for first change address of nested segwit on mainnet
        (HDKey.from_string("ypub6Ww3ibxVfGzLrAH1PNcjyAWenMTbbAosGNB6VvmSEgytSER9azLDWCxoJwW7Ke7icmizBMXrzBx9979FfaHxHcrArf3zbeJJJUZPf663zsP"), "nes", 0, True, "main"):
            "34K56kSjgUCUSD8GTtuF7c9Zzwokbs6uZ7",

        # https://github.com/bitcoin/bips/blob/master/bip-0049.mediawiki#test-vectors (first payment address of nested segwit on testnet)
        (HDKey.from_string("upub5EFU65HtV5TeiSHmZZm7FUffBGy8UKeqp7vw43jYbvZPpoVsgU93oac7Wk3u6moKegAEWtGNF8DehrnHtv21XXEMYRUocHqguyjknFHYfgY"), "nes", 0, False, "test"):
            "2Mww8dCYPUpKHofjgcXcBCEGmniw9CoaiD2",
        # jdlcdl: derived via iancoleman test vector for first change address of nested segwit on testnet
        (HDKey.from_string("upub5EFU65HtV5TeiSHmZZm7FUffBGy8UKeqp7vw43jYbvZPpoVsgU93oac7Wk3u6moKegAEWtGNF8DehrnHtv21XXEMYRUocHqguyjknFHYfgY"), "nes", 0, True, "test"):
            "2MvdUi5o3f2tnEFh9yGvta6FzptTZtkPJC8",

        # https://github.com/bitcoin/bips/blob/master/bip-0086.mediawiki#test-vectors (first payment address of taproot on mainnet)
        (HDKey.from_string("xpub6BgBgsespWvERF3LHQu6CnqdvfEvtMcQjYrcRzx53QJjSxarj2afYWcLteoGVky7D3UKDP9QyrLprQ3VCECoY49yfdDEHGCtMMj92pReUsQ"), "tr", 0, False, "main"):
            "bc1p5cyxnuxmeuwuvkwfem96lqzszd02n6xdcjrs20cac6yqjjwudpxqkedrcr",

        # https://github.com/bitcoin/bips/blob/master/bip-0086.mediawiki#test-vectors (second payment address of taproot on mainnet)
        (HDKey.from_string("xpub6BgBgsespWvERF3LHQu6CnqdvfEvtMcQjYrcRzx53QJjSxarj2afYWcLteoGVky7D3UKDP9QyrLprQ3VCECoY49yfdDEHGCtMMj92pReUsQ"), "tr", 1, False, "main"):
            "bc1p4qhjn9zdvkux4e44uhx8tc55attvtyu358kutcqkudyccelu0was9fqzwh",

        # https://github.com/bitcoin/bips/blob/master/bip-0086.mediawiki#test-vectors (first change address of taproot on mainnet)
        (HDKey.from_string("xpub6BgBgsespWvERF3LHQu6CnqdvfEvtMcQjYrcRzx53QJjSxarj2afYWcLteoGVky7D3UKDP9QyrLprQ3VCECoY49yfdDEHGCtMMj92pReUsQ"), "tr", 0, True, "main"):
            "bc1p3qkhfews2uk44qtvauqyr2ttdsw7svhkl9nkm9s9c3x4ax5h60wqwruhk7",

        # jdlcdl: derived via electrum m/44'/1'/0 (first payment address p2pkh on testnet)
        (HDKey.from_string("tpubDC5FSnBiZDMmhiuCmWAYsLwgLYrrT9rAqvTySfuCCrgsWz8wxMXUS9Tb9iVMvcRbvFcAHGkMD5Kx8koh4GquNGNTfohfk7pgjhaPCdXpoba"), "leg", 0, False, "test"):
            "mkpZhYtJu2r87Js3pDiWJDmPte2NRZ8bJV",

        # jdlcdl: derived via electrum m/44'/1'/0 (first change address p2pkh on testnet)
        (HDKey.from_string("tpubDC5FSnBiZDMmhiuCmWAYsLwgLYrrT9rAqvTySfuCCrgsWz8wxMXUS9Tb9iVMvcRbvFcAHGkMD5Kx8koh4GquNGNTfohfk7pgjhaPCdXpoba"), "leg", 0, True, "test"):
            "mi8nhzZgGZQthq6DQHbru9crMDerUdTKva",

        # https://github.com/satoshilabs/slips/blob/master/slip-0132.md#bitcoin-test-vectors (first payment address p2pkh on mainnet)
        (HDKey.from_string("xpub6BosfCnifzxcFwrSzQiqu2DBVTshkCXacvNsWGYJVVhhawA7d4R5WSWGFNbi8Aw6ZRc1brxMyWMzG3DSSSSoekkudhUd9yLb6qx39T9nMdj"), "leg", 0, False, "main"):
            "1LqBGSKuX5yYUonjxT5qGfpUsXKYYWeabA",

        # 3rdIteration: derived via electrum m/44'/0'/0 (first change address p2pkh on mainnet)
        (HDKey.from_string("xpub6BosfCnifzxcFwrSzQiqu2DBVTshkCXacvNsWGYJVVhhawA7d4R5WSWGFNbi8Aw6ZRc1brxMyWMzG3DSSSSoekkudhUd9yLb6qx39T9nMdj"), "leg", 0, True, "main"):
            "1J3J6EvPrv8q6AC3VCjWV45Uf3nssNMRtH",

        # jdlcdl: nonsense script_type falls off end of function returning None.  TODO: Would it be preferred to "else: raise ValueError"?
        (HDKey.from_string("tpubDC5FSnBiZDMmhiuCmWAYsLwgLYrrT9rAqvTySfuCCrgsWz8wxMXUS9Tb9iVMvcRbvFcAHGkMD5Kx8koh4GquNGNTfohfk7pgjhaPCdXpoba"), "NONSENSE", 0, True, "test"):
            "None",
    }
    func = embit_utils.get_single_sig_address

    print()
    for args, expected in vectors_args_expected.items():
        print("\nasserting...")

        # call without optional params (defaults: script_type="nat", index=0, is_change=False, embit_network="main")
        if args[1:5] == ("nat", 0, False, "main"):
            print(f'  {func.__name__}(HDKey.from_string("{args[0]}")) == "{expected}"')
            assert str(func(args[0])) == expected

        # call with ordered params
        print(f'  {func.__name__}(HDKey.from_string("{args[0]}"), *{args[1:5]}) == "{expected}"')
        assert str(func(*args)) == expected

        # call with named params
        print(f'  {func.__name__}(xpub=HDKey.from_string("{args[0]}"), script_type="{args[1]}", index={args[2]}, is_change={args[3]}, embit_network="{args[4]}") == "{expected}"')
        assert str(func(xpub=args[0], script_type=args[1], index=args[2], is_change=args[3], embit_network=args[4])) == expected


def test_get_multisig_address():
    """
    tests seedsigner.helpers.embit_utils.get_multisig_address()
    """

    from embit.descriptor import Descriptor

    # jdlcdl: these vectors created with electrum & sparrow as a 2 of 3 multisig based on BIP-39 and BIP-32 standard-path wallets
    #    keystore1 = 0x00*16 = 73c5da0a = 'abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon about'
    #    keystore2 = 0x11*16 = 0be174ee = 'baby mass dust captain baby mass dust captain baby mass dust casino'
    #    keystore3 = 0x22*16 = 8d55ff0d = 'captain baby mass dust captain baby mass dust captain baby mass dutch'

    vector_args_expected = { 
        # multisig native segwit on testnet, first payment and change addresses
        ("wsh(sortedmulti(2,[8d55ff0d/48h/1h/0h/2h]tpubDDxNVWk924RTUhdkVB2uLHw1hGMPNMGufpZefhkkswjbZppVZcuMdjYKQN4ewUog9vbL6RBLFPRWcgTGT7kYP79N6thyJ43ELUs4N2szXMg/{0,1}/*,[73c5da0a/48h/1h/0h/2h]tpubDFH9dgzveyD8zTbPUFuLrGmCydNvxehyNdUXKJAQN8x4aZ4j6UZqGfnqFrD4NqyaTVGKbvEW54tsvPTK2UoSbCC1PJY8iCNiwTL3RWZEheQ/{0,1}/*,[0be174ee/48h/1h/0h/2h]tpubDEsePyLPkbxbrDiZSTTWdsviiNtiQjrvvzZnkLtG72QYLBygEsXePRsTdXi8DeMA7taCuuvoEBjUAfFrsNZeQJqfvG9fFoujYWbFPYUn7ux/{0,1}/*))#zw6cnrlk" , 0, False, "test"): "tb1q7tpecll8jhp77yqdeyt2t8q5swxmmqeh2v22cqpms5dxlp6p27dqlftet8",
        ("wsh(sortedmulti(2,[8d55ff0d/48h/1h/0h/2h]tpubDDxNVWk924RTUhdkVB2uLHw1hGMPNMGufpZefhkkswjbZppVZcuMdjYKQN4ewUog9vbL6RBLFPRWcgTGT7kYP79N6thyJ43ELUs4N2szXMg/{0,1}/*,[73c5da0a/48h/1h/0h/2h]tpubDFH9dgzveyD8zTbPUFuLrGmCydNvxehyNdUXKJAQN8x4aZ4j6UZqGfnqFrD4NqyaTVGKbvEW54tsvPTK2UoSbCC1PJY8iCNiwTL3RWZEheQ/{0,1}/*,[0be174ee/48h/1h/0h/2h]tpubDEsePyLPkbxbrDiZSTTWdsviiNtiQjrvvzZnkLtG72QYLBygEsXePRsTdXi8DeMA7taCuuvoEBjUAfFrsNZeQJqfvG9fFoujYWbFPYUn7ux/{0,1}/*))#zw6cnrlk" , 0, True, "test"): "tb1q7h94ywhfjrpxdfzwl4dcawrg80r4rywswjrh447x4n3e5t3m0jms9jh7pm",

        # multisig nested segwit on testnet, first payment and change addresses
        ("sh(wsh(sortedmulti(2,[73c5da0a/48h/1h/1h/0h/1h]tpubDFH9dgzveyD8yHQb8VrpG8FYAuwcLMHMje2CCcbBo1FpaGzYVtJeYYxcYgRqSTta5utUFts8nPPHs9C2bqoxrey5jia6Dwf9mpwrPq7YvcJ/{0,1}/*,[0be174ee/48h/1h/0h/1h]tpubDEsePyLPkbxbnj6XuKvWwdERHaKkikZxaGJ9sJqmM7okbZXgkNSFiGU6GX6qEes6kD8f9Z9FosYB9UEnBSgBEyEwwJhj4uUcFE1WE8VtKoh/{0,1}/*,[8d55ff0d/48h/1h/0h/1h]tpubDDxNVWk924RTT3vyGLHdSDoZ2JUVX7jUsPcwCQ9MrKHAtJrW5zECTF9rFHCvqu526E4PjHp61hBknts2c5aGexvX7hvCZ8TGPvQFdzxxy59/{0,1}/*)))#2ujlfp73", 0, False, "test"): "2MtgJH28mZWNWU7VRU4ba6ciFbRRGYWZDt3",
        ("sh(wsh(sortedmulti(2,[73c5da0a/48h/1h/1h/0h/1h]tpubDFH9dgzveyD8yHQb8VrpG8FYAuwcLMHMje2CCcbBo1FpaGzYVtJeYYxcYgRqSTta5utUFts8nPPHs9C2bqoxrey5jia6Dwf9mpwrPq7YvcJ/{0,1}/*,[0be174ee/48h/1h/0h/1h]tpubDEsePyLPkbxbnj6XuKvWwdERHaKkikZxaGJ9sJqmM7okbZXgkNSFiGU6GX6qEes6kD8f9Z9FosYB9UEnBSgBEyEwwJhj4uUcFE1WE8VtKoh/{0,1}/*,[8d55ff0d/48h/1h/0h/1h]tpubDDxNVWk924RTT3vyGLHdSDoZ2JUVX7jUsPcwCQ9MrKHAtJrW5zECTF9rFHCvqu526E4PjHp61hBknts2c5aGexvX7hvCZ8TGPvQFdzxxy59/{0,1}/*)))#2ujlfp73", 0, True, "test"): "2NAjjwUQqwD9XRGLeQ6TitSUyMHUz3cLiWm",

        # legacy multisig p2sh on testnet, first payment and change addresses
        ("sh(sortedmulti(2,[8d55ff0d/45h]tpubDANogJ2yfnizHwX7fSi5kUVzybyuPXDhgHB2TR9TUvkSLZFW73cRq4STKFDpx7qjJJiisyq82tbu4CeiYtmKEmT1xoCq9P8BPvXV31HUh6d/{0,1}/*,[0be174ee/45h]tpubDBkeVF2tDNT1Pz7L47iJeBB6RokU12LX6x4E6Ph8T89hmjQfB77q1AMyGwL8qpREVGq9sCJEbWwmnemwNTxnpxGn1di7BGy8jx9wEi5Vahu/{0,1}/*,[73c5da0a/45h]tpubDBKsGC1UqBDNvx9aivFmxZNgeZTUnmsCFGhWrqkLzucUCDePvbWWm3n8tAaAwMmxBG2ihdKCG9fzBdUnMxKx5PrkiqSZFi6Vkv6msUs9ddN/{0,1}/*))#p5t8sa8c", 0, False, "test"): "2NBXci43Y2fagvrFYTg3QmXj2LCPU2oaRFH",
        ("sh(sortedmulti(2,[8d55ff0d/45h]tpubDANogJ2yfnizHwX7fSi5kUVzybyuPXDhgHB2TR9TUvkSLZFW73cRq4STKFDpx7qjJJiisyq82tbu4CeiYtmKEmT1xoCq9P8BPvXV31HUh6d/{0,1}/*,[0be174ee/45h]tpubDBkeVF2tDNT1Pz7L47iJeBB6RokU12LX6x4E6Ph8T89hmjQfB77q1AMyGwL8qpREVGq9sCJEbWwmnemwNTxnpxGn1di7BGy8jx9wEi5Vahu/{0,1}/*,[73c5da0a/45h]tpubDBKsGC1UqBDNvx9aivFmxZNgeZTUnmsCFGhWrqkLzucUCDePvbWWm3n8tAaAwMmxBG2ihdKCG9fzBdUnMxKx5PrkiqSZFi6Vkv6msUs9ddN/{0,1}/*))#p5t8sa8c", 0, True, "test"): "2MuWQTq7hUGiX1HpXuPRnf7YTM42H5zoEwj",

        # Taproot regression test (plan's explicit Phase 1 requirement): a
        # key-path key plus a hidden script-path recovery leaf. Despite the
        # `elif descriptor.is_taproot: raise` branch in get_multisig_address(),
        # this actually succeeds -- embit's `is_segwit` is True for taproot too,
        # so the p2wsh/p2tr branch above handles it, and the tweaked output key
        # correctly commits to the hidden leaf. See can_derive_multisig_address's
        # docstring: this is documented, not "fixed", per the working plan.
        ("tr([73c5da0a/86h/1h/0h]tpubDFH9dgzveyD8zTbPUFuLrGmCydNvxehyNdUXKJAQN8x4aZ4j6UZqGfnqFrD4NqyaTVGKbvEW54tsvPTK2UoSbCC1PJY8iCNiwTL3RWZEheQ/{0,1}/*,and_v(v:pk([0be174ee/86h/1h/0h]tpubDEsePyLPkbxbrDiZSTTWdsviiNtiQjrvvzZnkLtG72QYLBygEsXePRsTdXi8DeMA7taCuuvoEBjUAfFrsNZeQJqfvG9fFoujYWbFPYUn7ux/{0,1}/*),older(1000)))#pmau4kv6", 0, False, "test"): "tb1plje4kx3zmjum85mm8rc5cdsughj4nl9jevt4fdt05cnlx9sqqxpq6nsps7",
        ("tr([73c5da0a/86h/1h/0h]tpubDFH9dgzveyD8zTbPUFuLrGmCydNvxehyNdUXKJAQN8x4aZ4j6UZqGfnqFrD4NqyaTVGKbvEW54tsvPTK2UoSbCC1PJY8iCNiwTL3RWZEheQ/{0,1}/*,and_v(v:pk([0be174ee/86h/1h/0h]tpubDEsePyLPkbxbrDiZSTTWdsviiNtiQjrvvzZnkLtG72QYLBygEsXePRsTdXi8DeMA7taCuuvoEBjUAfFrsNZeQJqfvG9fFoujYWbFPYUn7ux/{0,1}/*),older(1000)))#pmau4kv6", 0, True, "test"): "tb1pv3fschyrnd89vca4yj7wymaxkuypjte3al5x8fmnjk693ewdelsszjj9u0",

        # some policy that is not supported:
        # TODO: find anything non supported so we can drop off the function: Would it be preferred to "else: raise ValueError()"?
        #("sh(multi(2,[8d55ff0d/45h]tpubDANogJ2yfnizHwX7fSi5kUVzybyuPXDhgHB2TR9TUvkSLZFW73cRq4STKFDpx7qjJJiisyq82tbu4CeiYtmKEmT1xoCq9P8BPvXV31HUh6d/{0,1}/*,[0be174ee/45h]tpubDBkeVF2tDNT1Pz7L47iJeBB6RokU12LX6x4E6Ph8T89hmjQfB77q1AMyGwL8qpREVGq9sCJEbWwmnemwNTxnpxGn1di7BGy8jx9wEi5Vahu/{0,1}/*,[73c5da0a/45h]tpubDBKsGC1UqBDNvx9aivFmxZNgeZTUnmsCFGhWrqkLzucUCDePvbWWm3n8tAaAwMmxBG2ihdKCG9fzBdUnMxKx5PrkiqSZFi6Vkv6msUs9ddN/{0,1}/*))#", 0, False, "test"): None,

    }
    func = embit_utils.get_multisig_address

    print()
    for args, expected in vector_args_expected.items():
        descriptor = Descriptor.from_string(args[0])

        print("\nasserting...")

        # test successful calls
        if type(expected) == str:
            # call with optional params (defaults: index=0, is_change=False, embit_network="main")
            if args[1:4] == (0, False, 'main'):
                print(f'  {func.__name__}(Descriptor.from_string("{descriptor}")) == "{expected}"')
                assert func(descriptor) == expected

            # call with ordered params
            print(f'  {func.__name__}(Descriptor.from_string("{descriptor}"), *{args[1:4]}) == "{expected}"')
            assert func(descriptor, *args[1:4]) == expected

            # call with named params
            print(f'  {func.__name__}(descriptor=Descriptor.from_string("{descriptor}"), index={args[1]}, is_change={args[2]}, embit_network="{args[3]}") == "{expected}"')
            assert func(descriptor=descriptor, index=args[1], is_change=args[2], embit_network=args[3]) == expected

        # test exceptions
        else:
            # call with ordered params
            with pytest.raises(expected):
                print(f'  {func.__name__}(Descriptor.from_string("{descriptor}"), *{args[1:4]}) raises Exception')
                func(descriptor, *args[1:4])

            # call with named params
            with pytest.raises(expected):
                print(f'  {func.__name__}(descriptor=Descriptor.from_string("{descriptor}"), index={args[1]}, is_change={args[2]}, embit_network="{args[3]}") raises Exception"')
                func(descriptor=descriptor, index=args[1], is_change=args[2], embit_network=args[3])


def test_get_multisig_policy():
    """
    tests seedsigner.helpers.embit_utils.get_multisig_policy()
    """
    from embit.descriptor import Descriptor

    # Reuses the same 2-of-3 multisig descriptors from test_get_multisig_address
    vectors_descriptor_expected = {
        # native segwit 2-of-3
        "wsh(sortedmulti(2,[8d55ff0d/48h/1h/0h/2h]tpubDDxNVWk924RTUhdkVB2uLHw1hGMPNMGufpZefhkkswjbZppVZcuMdjYKQN4ewUog9vbL6RBLFPRWcgTGT7kYP79N6thyJ43ELUs4N2szXMg/{0,1}/*,[73c5da0a/48h/1h/0h/2h]tpubDFH9dgzveyD8zTbPUFuLrGmCydNvxehyNdUXKJAQN8x4aZ4j6UZqGfnqFrD4NqyaTVGKbvEW54tsvPTK2UoSbCC1PJY8iCNiwTL3RWZEheQ/{0,1}/*,[0be174ee/48h/1h/0h/2h]tpubDEsePyLPkbxbrDiZSTTWdsviiNtiQjrvvzZnkLtG72QYLBygEsXePRsTdXi8DeMA7taCuuvoEBjUAfFrsNZeQJqfvG9fFoujYWbFPYUn7ux/{0,1}/*))#zw6cnrlk": ("2", "3"),
        # nested segwit 2-of-3
        "sh(wsh(sortedmulti(2,[73c5da0a/48h/1h/1h/0h/1h]tpubDFH9dgzveyD8yHQb8VrpG8FYAuwcLMHMje2CCcbBo1FpaGzYVtJeYYxcYgRqSTta5utUFts8nPPHs9C2bqoxrey5jia6Dwf9mpwrPq7YvcJ/{0,1}/*,[0be174ee/48h/1h/0h/1h]tpubDEsePyLPkbxbnj6XuKvWwdERHaKkikZxaGJ9sJqmM7okbZXgkNSFiGU6GX6qEes6kD8f9Z9FosYB9UEnBSgBEyEwwJhj4uUcFE1WE8VtKoh/{0,1}/*,[8d55ff0d/48h/1h/0h/1h]tpubDDxNVWk924RTT3vyGLHdSDoZ2JUVX7jUsPcwCQ9MrKHAtJrW5zECTF9rFHCvqu526E4PjHp61hBknts2c5aGexvX7hvCZ8TGPvQFdzxxy59/{0,1}/*)))#2ujlfp73": ("2", "3"),
        # legacy p2sh 2-of-3
        "sh(sortedmulti(2,[8d55ff0d/45h]tpubDANogJ2yfnizHwX7fSi5kUVzybyuPXDhgHB2TR9TUvkSLZFW73cRq4STKFDpx7qjJJiisyq82tbu4CeiYtmKEmT1xoCq9P8BPvXV31HUh6d/{0,1}/*,[0be174ee/45h]tpubDBkeVF2tDNT1Pz7L47iJeBB6RokU12LX6x4E6Ph8T89hmjQfB77q1AMyGwL8qpREVGq9sCJEbWwmnemwNTxnpxGn1di7BGy8jx9wEi5Vahu/{0,1}/*,[73c5da0a/45h]tpubDBKsGC1UqBDNvx9aivFmxZNgeZTUnmsCFGhWrqkLzucUCDePvbWWm3n8tAaAwMmxBG2ihdKCG9fzBdUnMxKx5PrkiqSZFi6Vkv6msUs9ddN/{0,1}/*))#p5t8sa8c": ("2", "3"),
    }

    for desc_str, (expected_threshold, expected_n) in vectors_descriptor_expected.items():
        descriptor = Descriptor.from_string(desc_str)
        threshold, n = embit_utils.get_multisig_policy(descriptor)
        assert threshold == expected_threshold
        assert n == expected_n

    # Non-multisig descriptor should raise ValueError
    with pytest.raises(ValueError):
        embit_utils.get_multisig_policy(Descriptor.from_string(
            "wpkh([73c5da0a/84h/1h/0h]tpubDC5FSnBiZDMmhiuCmWAYsLwgLYrrT9rAqvTySfuCCrgsWz8wxMXUS9Tb9iVMvcRbvFcAHGkMD5Kx8koh4GquNGNTfohfk7pgjhaPCdXpoba/{0,1}/*)#2aj6cvca"
        ))


#
# Liana-style wsh() Miniscript and taproot test vectors, reusing the exact same
# known-good keys/fingerprints as test_get_multisig_address above
# (73c5da0a = 'abandon...about', 0be174ee = 'baby mass dust...casino')
# so this test data is grounded in already-verified key material.
#
# wsh(or_d(pk(primary),and_v(v:pkh(recovery),older(1000)))) -- Liana's basic
# 2-key recovery policy: primary key spends any time, recovery key can spend
# alone after a 1000-block relative timelock.
LIANA_WSH_DESCRIPTOR = (
    "wsh(or_d(pk([73c5da0a/48h/1h/0h/2h]tpubDFH9dgzveyD8zTbPUFuLrGmCydNvxehyNdUXKJAQN8x4aZ4j6UZqGfnqFrD4NqyaTVGKbvEW54tsvPTK2UoSbCC1PJY8iCNiwTL3RWZEheQ/<0;1>/*),"
    "and_v(v:pkh([0be174ee/48h/1h/0h/2h]tpubDEsePyLPkbxbrDiZSTTWdsviiNtiQjrvvzZnkLtG72QYLBygEsXePRsTdXi8DeMA7taCuuvoEBjUAfFrsNZeQJqfvG9fFoujYWbFPYUn7ux/<0;1>/*),older(1000))))"
    "#73g7ls54"
)

# tr(primary, and_v(v:pk(recovery),older(1000))) -- same policy shape, taproot:
# key-path spend by the primary key, a single hidden script-path recovery leaf.
LIANA_TR_DESCRIPTOR = (
    "tr([73c5da0a/86h/1h/0h]tpubDFH9dgzveyD8zTbPUFuLrGmCydNvxehyNdUXKJAQN8x4aZ4j6UZqGfnqFrD4NqyaTVGKbvEW54tsvPTK2UoSbCC1PJY8iCNiwTL3RWZEheQ/<0;1>/*,"
    "and_v(v:pk([0be174ee/86h/1h/0h]tpubDEsePyLPkbxbrDiZSTTWdsviiNtiQjrvvzZnkLtG72QYLBygEsXePRsTdXi8DeMA7taCuuvoEBjUAfFrsNZeQJqfvG9fFoujYWbFPYUn7ux/<0;1>/*),older(1000)))"
    "#uq7s6lsf"
)

# Bare single-key wpkh() -- NOT a "wallet policy" in the Miniscript/multisig
# sense; should be excluded from is_supported_wallet_descriptor just like it
# was before this change (routes to NotYetImplementedView).
SINGLE_KEY_DESCRIPTOR = (
    "wpkh([73c5da0a/84h/1h/0h]tpubDFH9dgzveyD8zTbPUFuLrGmCydNvxehyNdUXKJAQN8x4aZ4j6UZqGfnqFrD4NqyaTVGKbvEW54tsvPTK2UoSbCC1PJY8iCNiwTL3RWZEheQ/<0;1>/*)"
    "#hxzwpz08"
)


def test_is_supported_wallet_descriptor():
    """
    tests seedsigner.helpers.embit_utils.is_supported_wallet_descriptor()
    """
    from embit.descriptor import Descriptor
    from embit.descriptor.checksum import add_checksum

    # Existing basic multisig (unchanged behavior)
    basic_multisig = Descriptor.from_string(
        "wsh(sortedmulti(2,[8d55ff0d/48h/1h/0h/2h]tpubDDxNVWk924RTUhdkVB2uLHw1hGMPNMGufpZefhkkswjbZppVZcuMdjYKQN4ewUog9vbL6RBLFPRWcgTGT7kYP79N6thyJ43ELUs4N2szXMg/{0,1}/*,[73c5da0a/48h/1h/0h/2h]tpubDFH9dgzveyD8zTbPUFuLrGmCydNvxehyNdUXKJAQN8x4aZ4j6UZqGfnqFrD4NqyaTVGKbvEW54tsvPTK2UoSbCC1PJY8iCNiwTL3RWZEheQ/{0,1}/*,[0be174ee/48h/1h/0h/2h]tpubDEsePyLPkbxbrDiZSTTWdsviiNtiQjrvvzZnkLtG72QYLBygEsXePRsTdXi8DeMA7taCuuvoEBjUAfFrsNZeQJqfvG9fFoujYWbFPYUn7ux/{0,1}/*))#zw6cnrlk"
    )
    assert embit_utils.is_supported_wallet_descriptor(basic_multisig) is True

    # Curated Miniscript template only: wsh() shape matching match_liana_recovery_policy()
    assert embit_utils.is_supported_wallet_descriptor(Descriptor.from_string(LIANA_WSH_DESCRIPTOR)) is True

    # Curated Miniscript template only: tr() shape matching match_liana_recovery_policy()
    assert embit_utils.is_supported_wallet_descriptor(Descriptor.from_string(LIANA_TR_DESCRIPTOR)) is True

    # Taproot key-path only (no hidden leaves): trivially safe, accepted generically
    key_only_taproot = Descriptor.from_string(
        "tr([73c5da0a/86h/1h/0h]tpubDFH9dgzveyD8zTbPUFuLrGmCydNvxehyNdUXKJAQN8x4aZ4j6UZqGfnqFrD4NqyaTVGKbvEW54tsvPTK2UoSbCC1PJY8iCNiwTL3RWZEheQ/<0;1>/*)#kcjfc8qw"
    )
    assert embit_utils.is_supported_wallet_descriptor(key_only_taproot) is True

    # Miniscript that does NOT match the curated template must be rejected --
    # this is the point of narrowing the gate (seedsigner#306, PR #1026): a
    # generic AST-to-English summary used to be accepted for any wsh()
    # Miniscript, which reviewers flagged as unreadable/unsafe on-device.
    #
    # Both cases below are valid miniscript that this curated screen cannot
    # state correctly, so both are refused rather than approximated.
    key_a = "[8d55ff0d/48h/1h/0h/2h]tpubDDxNVWk924RTUhdkVB2uLHw1hGMPNMGufpZefhkkswjbZppVZcuMdjYKQN4ewUog9vbL6RBLFPRWcgTGT7kYP79N6thyJ43ELUs4N2szXMg/<0;1>/*"
    key_b = "[73c5da0a/48h/1h/0h/2h]tpubDFH9dgzveyD8zTbPUFuLrGmCydNvxehyNdUXKJAQN8x4aZ4j6UZqGfnqFrD4NqyaTVGKbvEW54tsvPTK2UoSbCC1PJY8iCNiwTL3RWZEheQ/<0;1>/*"

    # An *absolute* timelock (after = block height) where the template expects a
    # *relative* one (older = blocks since the coin confirmed). Accepting this
    # would be actively misleading, since the screen says "after N blocks",
    # which describes the relative meaning.
    absolute_timelock = Descriptor.from_string(add_checksum(
        f"wsh(or_d(pk({key_a}),and_v(v:pkh({key_b}),after(500000))))"
    ))
    assert embit_utils.match_liana_recovery_policy(absolute_timelock) is None
    assert embit_utils.is_supported_wallet_descriptor(absolute_timelock) is False

    # A recovery path gated on a hash preimage in addition to a key and a
    # timelock -- a third condition the curated two-path screen has nowhere to
    # show, so silently omitting it would understate what's required to spend.
    hashlock_recovery = Descriptor.from_string(add_checksum(
        f"wsh(or_d(pk({key_a}),and_v(v:pkh({key_b}),"
        "and_v(v:sha256(6c60f404f8167a38fc70eaf8aa17ac351023bef86bcb9d1086a19afe95bd5333),older(100)))))"
    ))
    assert embit_utils.match_liana_recovery_policy(hashlock_recovery) is None
    assert embit_utils.is_supported_wallet_descriptor(hashlock_recovery) is False

    # Bare single-key descriptor: still excluded (unimplemented single-sig import)
    assert embit_utils.is_supported_wallet_descriptor(Descriptor.from_string(SINGLE_KEY_DESCRIPTOR)) is False


def test_match_liana_recovery_policy():
    """
    tests seedsigner.helpers.embit_utils.match_liana_recovery_policy()
    """
    from embit.descriptor import Descriptor
    from embit.descriptor.checksum import add_checksum

    wsh_match = embit_utils.match_liana_recovery_policy(Descriptor.from_string(LIANA_WSH_DESCRIPTOR))
    assert wsh_match is not None
    assert wsh_match.primary_threshold == 1
    assert wsh_match.primary_fingerprints == ["73c5da0a"]
    assert wsh_match.recovery_threshold == 1
    assert wsh_match.recovery_fingerprints == ["0be174ee"]
    assert wsh_match.timelock_blocks == 1000

    tr_match = embit_utils.match_liana_recovery_policy(Descriptor.from_string(LIANA_TR_DESCRIPTOR))
    assert tr_match is not None
    assert tr_match.primary_threshold == 1
    assert tr_match.primary_fingerprints == ["73c5da0a"]
    assert tr_match.recovery_threshold == 1
    assert tr_match.recovery_fingerprints == ["0be174ee"]
    assert tr_match.timelock_blocks == 1000

    # Basic multisig is a completely different shape -- no match, not an error
    basic_multisig = Descriptor.from_string(
        "wsh(sortedmulti(2,[8d55ff0d/48h/1h/0h/2h]tpubDDxNVWk924RTUhdkVB2uLHw1hGMPNMGufpZefhkkswjbZppVZcuMdjYKQN4ewUog9vbL6RBLFPRWcgTGT7kYP79N6thyJ43ELUs4N2szXMg/{0,1}/*,[73c5da0a/48h/1h/0h/2h]tpubDFH9dgzveyD8zTbPUFuLrGmCydNvxehyNdUXKJAQN8x4aZ4j6UZqGfnqFrD4NqyaTVGKbvEW54tsvPTK2UoSbCC1PJY8iCNiwTL3RWZEheQ/{0,1}/*,[0be174ee/48h/1h/0h/2h]tpubDEsePyLPkbxbrDiZSTTWdsviiNtiQjrvvzZnkLtG72QYLBygEsXePRsTdXi8DeMA7taCuuvoEBjUAfFrsNZeQJqfvG9fFoujYWbFPYUn7ux/{0,1}/*))#zw6cnrlk"
    )
    assert embit_utils.match_liana_recovery_policy(basic_multisig) is None

    assert embit_utils.match_liana_recovery_policy(Descriptor.from_string(SINGLE_KEY_DESCRIPTOR)) is None

    # A third OR branch, or any other shape beyond exactly "primary, or
    # recovery-after-timelock" -- must not match, even though it superficially
    # resembles the template (still an or_d at the top, still has an older()).
    three_way = Descriptor.from_string(add_checksum(
        "wsh(or_d(pk([73c5da0a/48h/1h/0h/2h]tpubDFH9dgzveyD8zTbPUFuLrGmCydNvxehyNdUXKJAQN8x4aZ4j6UZqGfnqFrD4NqyaTVGKbvEW54tsvPTK2UoSbCC1PJY8iCNiwTL3RWZEheQ/<0;1>/*),"
        "or_i(and_v(v:pkh([0be174ee/48h/1h/0h/2h]tpubDEsePyLPkbxbrDiZSTTWdsviiNtiQjrvvzZnkLtG72QYLBygEsXePRsTdXi8DeMA7taCuuvoEBjUAfFrsNZeQJqfvG9fFoujYWbFPYUn7ux/<0;1>/*),older(1000)),"
        "and_v(v:pkh([0f889044/48h/1h/0h/2h]tpubDFQDKbH2mDqNDPNaUVxM6R5mHhzC4u5F6mNnUkCf6gBMbcENMQ1ZGFLZc3QwgdEv2f34wkTvLMG5kD8AZEZRhat1HQDj42eVxQSxbcqxn31/<0;1>/*),older(2000)))))"
    ))
    assert embit_utils.match_liana_recovery_policy(three_way) is None

    # BIP68 time-based timelock (bit 22 set: 512-second units, not blocks).
    # Liana has never been observed to produce this encoding for this policy
    # shape; deliberately left unrecognized rather than assumed == blocks.
    # older(1000 | 0x00400000) as raw pushed argument.
    time_based = Descriptor.from_string(add_checksum(
        "wsh(or_d(pk([73c5da0a/48h/1h/0h/2h]tpubDFH9dgzveyD8zTbPUFuLrGmCydNvxehyNdUXKJAQN8x4aZ4j6UZqGfnqFrD4NqyaTVGKbvEW54tsvPTK2UoSbCC1PJY8iCNiwTL3RWZEheQ/<0;1>/*),"
        "and_v(v:pkh([0be174ee/48h/1h/0h/2h]tpubDEsePyLPkbxbrDiZSTTWdsviiNtiQjrvvzZnkLtG72QYLBygEsXePRsTdXi8DeMA7taCuuvoEBjUAfFrsNZeQJqfvG9fFoujYWbFPYUn7ux/<0;1>/*),older(4195304))))"
    ))
    assert embit_utils.match_liana_recovery_policy(time_based) is None


# Descriptors copied verbatim from Liana's own test suite
# (liana-gui/src/app/state/receive.rs and .../psbt.rs), so these assert against
# what Liana actually emits rather than against a hand-built approximation of
# it. Note the two different multi-key forms Liana uses: `multi(k,...)` for a
# quorum on the primary path, but `thresh(k,pkh(A),a:pkh(B))` for one on the
# recovery path -- the recovery branch sits under and_v and needs different
# miniscript type properties, so a matcher that only handled `multi()` would
# silently reject every multi-key recovery wallet.
LIANA_REAL_MULTISIG_PRIMARY = "wsh(or_d(multi(2,[ffd63c8d/48'/1'/0'/2']tpubDExA3EC3iAsPxPhFn4j6gMiVup6V2eH3qKyk69RcTc9TTNRfFYVPad8bJD5FCHVQxyBT4izKsvr7Btd2R4xmQ1hZkvsqGBaeE82J71uTK4N/<0;1>/*,[de6eb005/48'/1'/0'/2']tpubDFGuYfS2JwiUSEXiQuNGdT3R7WTDhbaE6jbUhgYSSdhmfQcSx7ZntMPPv7nrkvAqjpj3jX9wbhSGMeKVao4qAzhbNyBi7iQmv5xxQk6H6jz/<0;1>/*),and_v(v:pkh([ffd63c8d/48'/1'/0'/2']tpubDExA3EC3iAsPxPhFn4j6gMiVup6V2eH3qKyk69RcTc9TTNRfFYVPad8bJD5FCHVQxyBT4izKsvr7Btd2R4xmQ1hZkvsqGBaeE82J71uTK4N/<2;3>/*),older(3))))#p9ax3xxp"

LIANA_REAL_MULTISIG_BOTH_PATHS = "wsh(or_d(multi(2,[f714c228/48'/1'/0'/2']tpubDEwJnTwfKoMvu8AXXBPydBVWDpzNP5tatjjZ56q4TQioGL7iL9xzTbMoCCQ3tfGihtff7vtR4xsjcRuhZ7HWARVAkGZ1HZcpBhVdou76k7j/<0;1>/*,[2522f23c/48'/1'/0'/2']tpubDEoTU4bDW1EXN1rnLXnRfue1a7DeqjJcs39PkEeLcVXhVKzCnFo9yQX2EeeXJ6kh4hgbz5o9v7YAc1EE97AEJpJbKNmDxE3ZQo4msGPSp2J/<0;1>/*),and_v(v:thresh(1,pkh([f714c228/48'/1'/0'/2']tpubDEwJnTwfKoMvu8AXXBPydBVWDpzNP5tatjjZ56q4TQioGL7iL9xzTbMoCCQ3tfGihtff7vtR4xsjcRuhZ7HWARVAkGZ1HZcpBhVdou76k7j/<2;3>/*),a:pkh([2522f23c/48'/1'/0'/2']tpubDEoTU4bDW1EXN1rnLXnRfue1a7DeqjJcs39PkEeLcVXhVKzCnFo9yQX2EeeXJ6kh4hgbz5o9v7YAc1EE97AEJpJbKNmDxE3ZQo4msGPSp2J/<2;3>/*)),older(65535))))#9s8ekrce"


def test_match_liana_recovery_policy__multisig_paths():
    """
    A multi-key primary path with a timelocked recovery is Liana's flagship
    configuration (2-of-3 now, single recovery key later), so it has to be a
    first-class supported shape, not an edge case.
    """
    from embit.descriptor import Descriptor

    m = embit_utils.match_liana_recovery_policy(Descriptor.from_string(LIANA_REAL_MULTISIG_PRIMARY))
    assert m is not None
    assert m.primary_threshold == 2
    assert m.primary_fingerprints == ["ffd63c8d", "de6eb005"]
    assert m.recovery_threshold == 1
    assert m.recovery_fingerprints == ["ffd63c8d"]
    assert m.timelock_blocks == 3

    # thresh()-based recovery quorum, which is a different miniscript fragment
    # from the multi() used on the primary path.
    m = embit_utils.match_liana_recovery_policy(Descriptor.from_string(LIANA_REAL_MULTISIG_BOTH_PATHS))
    assert m is not None
    assert m.primary_threshold == 2
    assert m.primary_fingerprints == ["f714c228", "2522f23c"]
    assert m.recovery_threshold == 1
    assert m.recovery_fingerprints == ["f714c228", "2522f23c"]
    assert m.timelock_blocks == 65535

    assert embit_utils.is_supported_wallet_descriptor(
        Descriptor.from_string(LIANA_REAL_MULTISIG_PRIMARY)
    ) is True


# A real Liana export (signet), captured from the GUI during hardware testing:
# an n-of-n primary path plus a single timelocked recovery key. Note that the
# recovery key is also one of the three primary keys, on a different derivation
# branch -- legal, and something the display must not obscure.
#
# Liana compiles this differently from a k-of-n primary, which is why it needed
# separate handling: `or_d(X,Z)` requires X to be dissatisfiable, an `and_v`
# chain is not, so an all-keys-required primary compiles to `or_i` instead --
# with the recovery branch FIRST, the reverse of the or_d form.
LIANA_REAL_3OF3_OR_I = "wsh(or_i(and_v(v:pkh([bce87290/48'/1'/0'/2']tpubDEx7eA5kryaQzKGqGw6G7McWQv3s1t2opk28vzCmS38Q7Zx31QWijPe24z3mjKwbkhh48FpUQYoiRAJcLXkmGbmiWJTErLFAcfDN53tEQVn/<2;3>/*),older(26298)),and_v(v:and_v(v:pk([bce87290/48'/1'/0'/2']tpubDEx7eA5kryaQzKGqGw6G7McWQv3s1t2opk28vzCmS38Q7Zx31QWijPe24z3mjKwbkhh48FpUQYoiRAJcLXkmGbmiWJTErLFAcfDN53tEQVn/<0;1>/*),pk([0f21a47d/48'/1'/0'/2']tpubDFLufBxpBavKArzSHoaXPG7WB6ruswscnzFiuHQ1T3AQDTmSN2ZSe3EN7U82q86hQWjZMiL3hio99SafdwgESZ4uD4cebmNqu6VtdNgTLQV/<0;1>/*)),pk([65645849/48'/1'/0'/2']tpubDEctyheVBNxchsg3rV5zAWgTaYkw8VL6SnJJacaWLqyAX2L8zxzQCqHTNzx3RnuZy2SgeCGUPx56WyJjusbe73pgT9GDZPYTet13Gv4nsPo/<0;1>/*))))#5rvc9c67"


def test_match_liana_recovery_policy__n_of_n_primary_via_or_i():
    """
    An n-of-n primary path arrives structurally different from a k-of-n one:
    `or_i` instead of `or_d`, branches in the opposite order, and the keys
    chained through nested `and_v` rather than listed in `multi()`. This
    descriptor is a real Liana export that the earlier or_d-only matcher
    refused, showing up on hardware as "Not Yet Implemented".

    The threshold must come out as 3 of 3, not 2 of 3: an and_v chain requires
    every key, and understating that on a signing device would tell the user
    their wallet is more recoverable than it is.
    """
    from embit.descriptor import Descriptor

    d = Descriptor.from_string(LIANA_REAL_3OF3_OR_I)
    m = embit_utils.match_liana_recovery_policy(d)
    assert m is not None

    assert m.primary_threshold == 3
    assert m.primary_fingerprints == ["bce87290", "0f21a47d", "65645849"]
    assert m.recovery_threshold == 1
    assert m.recovery_fingerprints == ["bce87290"]
    assert m.timelock_blocks == 26298

    assert embit_utils.is_supported_wallet_descriptor(d) is True


def test_match_liana_recovery_policy__rejects_multiple_recovery_tiers():
    """
    Liana can define several recovery paths with different timelocks. Both
    branches of the resulting or_i are timelocked, so neither is spendable
    now -- describing either as the "Spend now" path would be false, and the
    curated screen has only two fields regardless. Refused rather than
    approximated.
    """
    from embit.descriptor import Descriptor
    from embit.descriptor.checksum import add_checksum

    key_b = "[73c5da0a/48h/1h/0h/2h]tpubDFH9dgzveyD8zTbPUFuLrGmCydNvxehyNdUXKJAQN8x4aZ4j6UZqGfnqFrD4NqyaTVGKbvEW54tsvPTK2UoSbCC1PJY8iCNiwTL3RWZEheQ/<0;1>/*"
    key_c = "[0be174ee/48h/1h/0h/2h]tpubDEsePyLPkbxbrDiZSTTWdsviiNtiQjrvvzZnkLtG72QYLBygEsXePRsTdXi8DeMA7taCuuvoEBjUAfFrsNZeQJqfvG9fFoujYWbFPYUn7ux/<0;1>/*"

    two_tier = Descriptor.from_string(add_checksum(
        f"wsh(or_i(and_v(v:pkh({key_b}),older(1000)),and_v(v:pkh({key_c}),older(2000))))"
    ))
    assert embit_utils.match_liana_recovery_policy(two_tier) is None
    assert embit_utils.is_supported_wallet_descriptor(two_tier) is False


def test_match_liana_recovery_policy__rejects_undisplayable_key_counts():
    """
    The curated screen renders fingerprints two per line with room for four
    lines across both paths. A policy needing more than that is refused at
    match time, because the alternative is a screen whose recovery section is
    pushed under the buttons and silently invisible -- hiding the timelocked
    path is strictly worse than declining to display the wallet.

    Verified against the real screen: 3 primary lines + 1 recovery line ends
    at 178px against a 200px button top; one more line reaches 199-201px.
    """
    from embit.descriptor import Descriptor
    from embit.descriptor.checksum import add_checksum

    xpubs = [
        "tpubDDxNVWk924RTUhdkVB2uLHw1hGMPNMGufpZefhkkswjbZppVZcuMdjYKQN4ewUog9vbL6RBLFPRWcgTGT7kYP79N6thyJ43ELUs4N2szXMg",
        "tpubDFH9dgzveyD8zTbPUFuLrGmCydNvxehyNdUXKJAQN8x4aZ4j6UZqGfnqFrD4NqyaTVGKbvEW54tsvPTK2UoSbCC1PJY8iCNiwTL3RWZEheQ",
        "tpubDEsePyLPkbxbrDiZSTTWdsviiNtiQjrvvzZnkLtG72QYLBygEsXePRsTdXi8DeMA7taCuuvoEBjUAfFrsNZeQJqfvG9fFoujYWbFPYUn7ux",
        "tpubDFQDKbH2mDqNDPNaUVxM6R5mHhzC4u5F6mNnUkCf6gBMbcENMQ1ZGFLZc3QwgdEv2f34wkTvLMG5kD8AZEZRhat1HQDj42eVxQSxbcqxn31",
        "tpubDEx7eA5kryaQzKGqGw6G7McWQv3s1t2opk28vzCmS38Q7Zx31QWijPe24z3mjKwbkhh48FpUQYoiRAJcLXkmGbmiWJTErLFAcfDN53tEQVn",
        "tpubDEejYZTUVV2p7Zxi8LKU1zH7oZXT9UaiWC3zbvZnNDQVkKCz7858R39j8mZn1vbBkwHDTzNRaC8hrjyM9u8MtsfTjYCJxx6XBHrhmPg4seG",
        "tpubDF1SdybxnrvMab6MpzaSFvN26BtfANBSdAG1g1fHPYtaNo8oJaxnNfn2XgVuEvjaxoScVhNThEey27x9m3UB7GFfmYg6BA7yJ7EegKYb6EM",
    ]

    def key(i, branch="<0;1>"):
        return f"[{'%08x' % (0x11111111 * (i + 1))}/48h/1h/0h/2h]{xpubs[i]}/{branch}/*"

    def build(num_primary):
        primary = f"multi(2,{','.join(key(i) for i in range(num_primary))})"
        recovery = f"pkh({key(0, '<2;3>')})"
        return Descriptor.from_string(
            add_checksum(f"wsh(or_d({primary},and_v(v:{recovery},older(1000))))")
        )

    # 5 primary keys -> 3 lines + 1 recovery line = 4, the documented ceiling.
    accepted = embit_utils.match_liana_recovery_policy(build(5))
    assert accepted is not None
    assert accepted.primary_threshold == 2
    assert len(accepted.primary_fingerprints) == 5

    # 7 primary keys -> 4 lines + 1 = 5, past the ceiling.
    assert embit_utils.match_liana_recovery_policy(build(7)) is None
    assert embit_utils.is_supported_wallet_descriptor(build(7)) is False


def test_get_descriptor_policy_summary():
    """
    tests seedsigner.helpers.embit_utils.get_descriptor_policy_summary()
    """
    from embit.descriptor import Descriptor

    # Basic multisig: unchanged output vs. the old get_multisig_policy()-based string
    basic_multisig = Descriptor.from_string(
        "wsh(sortedmulti(2,[8d55ff0d/48h/1h/0h/2h]tpubDDxNVWk924RTUhdkVB2uLHw1hGMPNMGufpZefhkkswjbZppVZcuMdjYKQN4ewUog9vbL6RBLFPRWcgTGT7kYP79N6thyJ43ELUs4N2szXMg/{0,1}/*,[73c5da0a/48h/1h/0h/2h]tpubDFH9dgzveyD8zTbPUFuLrGmCydNvxehyNdUXKJAQN8x4aZ4j6UZqGfnqFrD4NqyaTVGKbvEW54tsvPTK2UoSbCC1PJY8iCNiwTL3RWZEheQ/{0,1}/*,[0be174ee/48h/1h/0h/2h]tpubDEsePyLPkbxbrDiZSTTWdsviiNtiQjrvvzZnkLtG72QYLBygEsXePRsTdXi8DeMA7taCuuvoEBjUAfFrsNZeQJqfvG9fFoujYWbFPYUn7ux/{0,1}/*))#zw6cnrlk"
    )
    assert embit_utils.get_descriptor_policy_summary(basic_multisig) == "2 of 3 multisig"

    # Curated template (wsh and tr alike): must return the short fixed name,
    # NOT a rendering of the policy expression.
    #
    # Regression test for a real bug found in on-device testing: Address
    # Explorer's one-line "Wallet descriptor" field called this function and
    # got back "(key BCE87290) or ((key 36D9CF93) and (after 4383 blocks))",
    # which ran off the right edge of the screen mid-word. Wrapping it would
    # not have been a fix -- the nested expression is the thing reviewers
    # objected to showing at all (seedsigner#306, PR #1026). Asserting on the
    # *absence* of expression syntax, not just on length, so a future change
    # that merely shortens the expression still fails this.
    for label, descriptor_str in [
        ("wsh", LIANA_WSH_DESCRIPTOR),
        ("tr", LIANA_TR_DESCRIPTOR),
    ]:
        summary = embit_utils.get_descriptor_policy_summary(Descriptor.from_string(descriptor_str))
        assert summary == "Recovery wallet", f"{label}: {summary}"
        assert "(" not in summary, f"{label}: policy expression leaked into summary"
        assert "73C5DA0A" not in summary
        assert "1000" not in summary

    # Taproot correctness requirement still holds for the taproot shapes that
    # do NOT match the curated template and so fall through to the generic
    # description: a hidden script-path recovery leaf must never be
    # summarized as plain single-key/single-signature. Uses two leaves, which
    # match_liana_recovery_policy() rejects (it requires exactly one).
    from embit.descriptor.checksum import add_checksum
    two_leaf_taproot = Descriptor.from_string(add_checksum(
        "tr([73c5da0a/86h/1h/0h]tpubDFH9dgzveyD8zTbPUFuLrGmCydNvxehyNdUXKJAQN8x4aZ4j6UZqGfnqFrD4NqyaTVGKbvEW54tsvPTK2UoSbCC1PJY8iCNiwTL3RWZEheQ/<0;1>/*,"
        "{and_v(v:pk([0be174ee/86h/1h/0h]tpubDEsePyLPkbxbrDiZSTTWdsviiNtiQjrvvzZnkLtG72QYLBygEsXePRsTdXi8DeMA7taCuuvoEBjUAfFrsNZeQJqfvG9fFoujYWbFPYUn7ux/<0;1>/*),older(1000)),"
        "and_v(v:pk([0f889044/86h/1h/0h]tpubDFQDKbH2mDqNDPNaUVxM6R5mHhzC4u5F6mNnUkCf6gBMbcENMQ1ZGFLZc3QwgdEv2f34wkTvLMG5kD8AZEZRhat1HQDj42eVxQSxbcqxn31/<0;1>/*),older(2000))})"
    ))
    assert embit_utils.match_liana_recovery_policy(two_leaf_taproot) is None
    tr_summary = embit_utils.get_descriptor_policy_summary(two_leaf_taproot)
    assert "single" not in tr_summary.lower()
    assert "73C5DA0A" in tr_summary  # key-path key
    assert "0BE174EE" in tr_summary  # hidden recovery leaf key
    assert "1000" in tr_summary      # recovery leaf's timelock

    # Taproot with no script path at all (key-path only) -- also must not be
    # mislabeled, but has nothing to hide, so no leaves are expected.
    key_only_taproot = Descriptor.from_string(
        "tr([73c5da0a/86h/1h/0h]tpubDFH9dgzveyD8zTbPUFuLrGmCydNvxehyNdUXKJAQN8x4aZ4j6UZqGfnqFrD4NqyaTVGKbvEW54tsvPTK2UoSbCC1PJY8iCNiwTL3RWZEheQ/<0;1>/*)#kcjfc8qw"
    )
    key_only_summary = embit_utils.get_descriptor_policy_summary(key_only_taproot)
    assert "73C5DA0A" in key_only_summary

    # Bare single-key descriptor: get_descriptor_policy_summary() itself should
    # describe it safely rather than raise, even though callers today route
    # single-key descriptors elsewhere before ever calling this function.
    single_summary = embit_utils.get_descriptor_policy_summary(Descriptor.from_string(SINGLE_KEY_DESCRIPTOR))
    assert "73C5DA0A" in single_summary

    # 240x240-screen truncation: must never exceed max_length, and must end
    # with a truncation marker rather than silently overflowing. Uses the
    # two-leaf taproot above, since the curated template now returns a short
    # fixed name that never needs truncating.
    truncated = embit_utils.get_descriptor_policy_summary(two_leaf_taproot, max_length=20)
    assert len(truncated) <= 20
    assert truncated.endswith("…")

    # The curated template's short name is well under any sane max_length, so
    # it comes back whole rather than truncated.
    assert embit_utils.get_descriptor_policy_summary(
        Descriptor.from_string(LIANA_WSH_DESCRIPTOR), max_length=20
    ) == "Recovery wallet"


def test_can_derive_multisig_address():
    """
    tests seedsigner.helpers.embit_utils.can_derive_multisig_address()
    """
    from embit.descriptor import Descriptor

    basic_multisig = Descriptor.from_string(
        "wsh(sortedmulti(2,[8d55ff0d/48h/1h/0h/2h]tpubDDxNVWk924RTUhdkVB2uLHw1hGMPNMGufpZefhkkswjbZppVZcuMdjYKQN4ewUog9vbL6RBLFPRWcgTGT7kYP79N6thyJ43ELUs4N2szXMg/{0,1}/*,[73c5da0a/48h/1h/0h/2h]tpubDFH9dgzveyD8zTbPUFuLrGmCydNvxehyNdUXKJAQN8x4aZ4j6UZqGfnqFrD4NqyaTVGKbvEW54tsvPTK2UoSbCC1PJY8iCNiwTL3RWZEheQ/{0,1}/*,[0be174ee/48h/1h/0h/2h]tpubDEsePyLPkbxbrDiZSTTWdsviiNtiQjrvvzZnkLtG72QYLBygEsXePRsTdXi8DeMA7taCuuvoEBjUAfFrsNZeQJqfvG9fFoujYWbFPYUn7ux/{0,1}/*))#zw6cnrlk"
    )
    assert embit_utils.can_derive_multisig_address(basic_multisig) is True
    assert embit_utils.can_derive_multisig_address(Descriptor.from_string(LIANA_WSH_DESCRIPTOR)) is True

    # Perhaps surprisingly, True for taproot too -- see the docstring on
    # can_derive_multisig_address(): embit's `is_segwit` covers taproot, and
    # address derivation for it genuinely works (verified in test_get_multisig_address).
    assert embit_utils.can_derive_multisig_address(Descriptor.from_string(LIANA_TR_DESCRIPTOR)) is True


def test_parse_derivation_path():
    # Shouldn't care if input uses "'" or "h"
    derivation_path = "m/84'/0'/0'/0/0"

    result = embit_utils.parse_derivation_path(derivation_path)
    assert result["script_type"] == SC.NATIVE_SEGWIT
    assert result["network"] == SC.MAINNET

    result = embit_utils.parse_derivation_path(derivation_path.replace("'", "h"))
    assert result["script_type"] == SC.NATIVE_SEGWIT
    assert result["network"] == SC.MAINNET

    # Now exhaustively test supported permutations
    vectors_args = {
        (SC.MAINNET, SC.NATIVE_SEGWIT, False): "m/84'/0'/0'/0/5",
        (SC.TESTNET, SC.NATIVE_SEGWIT, False): "m/84'/1'/0'/0/5",
        (SC.REGTEST, SC.NATIVE_SEGWIT, False): "m/84'/1'/0'/0/5",
        (SC.MAINNET, SC.NATIVE_SEGWIT, True): "m/84'/0'/0'/1/5",
        (SC.TESTNET, SC.NATIVE_SEGWIT, True): "m/84'/1'/0'/1/5",
        (SC.REGTEST, SC.NATIVE_SEGWIT, True): "m/84'/1'/0'/1/5",

        (SC.MAINNET, SC.NESTED_SEGWIT, False): "m/49'/0'/0'/0/5",
        (SC.TESTNET, SC.NESTED_SEGWIT, False): "m/49'/1'/0'/0/5",
        (SC.REGTEST, SC.NESTED_SEGWIT, False): "m/49'/1'/0'/0/5",
        (SC.MAINNET, SC.NESTED_SEGWIT, True): "m/49'/0'/0'/1/5",
        (SC.TESTNET, SC.NESTED_SEGWIT, True): "m/49'/1'/0'/1/5",
        (SC.REGTEST, SC.NESTED_SEGWIT, True): "m/49'/1'/0'/1/5",

        (SC.MAINNET, SC.TAPROOT, False): "m/86'/0'/0'/0/5",
        (SC.TESTNET, SC.TAPROOT, False): "m/86'/1'/0'/0/5",
        (SC.REGTEST, SC.TAPROOT, False): "m/86'/1'/0'/0/5",
        (SC.MAINNET, SC.TAPROOT, True): "m/86'/0'/0'/1/5",
        (SC.TESTNET, SC.TAPROOT, True): "m/86'/1'/0'/1/5",
        (SC.REGTEST, SC.TAPROOT, True): "m/86'/1'/0'/1/5",

        (SC.MAINNET, SC.LEGACY_P2PKH, False): "m/44'/0'/0'/0/5",
        (SC.TESTNET, SC.LEGACY_P2PKH, False): "m/44'/1'/0'/0/5",
        (SC.REGTEST, SC.LEGACY_P2PKH, False): "m/44'/1'/0'/0/5",
        (SC.MAINNET, SC.LEGACY_P2PKH, True): "m/44'/0'/0'/1/5",
        (SC.TESTNET, SC.LEGACY_P2PKH, True): "m/44'/1'/0'/1/5",
        (SC.REGTEST, SC.LEGACY_P2PKH, True): "m/44'/1'/0'/1/5",

        # Try a typical custom derivation path (Unchained vault keys)
        (SC.MAINNET, SC.CUSTOM_DERIVATION, False): "m/45'/0'/0'/0/5",
        (SC.TESTNET, SC.CUSTOM_DERIVATION, False): "m/45'/1'/0'/0/5",
        (SC.REGTEST, SC.CUSTOM_DERIVATION, False): "m/45'/1'/0'/0/5",
        (SC.MAINNET, SC.CUSTOM_DERIVATION, True): "m/45'/0'/0'/1/5",
        (SC.TESTNET, SC.CUSTOM_DERIVATION, True): "m/45'/1'/0'/1/5",
        (SC.REGTEST, SC.CUSTOM_DERIVATION, True): "m/45'/1'/0'/1/5",

        # CRAZY custom derivation paths
        (None, SC.CUSTOM_DERIVATION, False, 5): "m/123'/9083270/9083270/9083270/9083270/0/5",

        # non-standard change and/or index
        (None, SC.CUSTOM_DERIVATION, None, 5): "m/9'/78/5",
        (None, SC.CUSTOM_DERIVATION, None, 5): "m/9'/78'/5",
        (None, SC.CUSTOM_DERIVATION, None, None): "m/9'/78'/5'",
        (None, SC.CUSTOM_DERIVATION, False, None): "m/9'/0/5'",
    }

    for expected_result, derivation_path in vectors_args.items():
        actual_result = embit_utils.parse_derivation_path(derivation_path)

        if expected_result[0] == SC.MAINNET:
            assert actual_result["network"] == expected_result[0]
            assert actual_result["clean_match"] is True
        elif expected_result[0] is None:
            assert actual_result["network"] is None
            assert actual_result["clean_match"] is False
        else:
            # Testnet and regtest are returned as a list since the parser can't tell which is intended
            assert expected_result[0] in actual_result["network"]
            assert actual_result["clean_match"] is True

        assert actual_result["script_type"] == expected_result[1]
        assert actual_result["is_change"] == expected_result[2]

        if len(expected_result) == 4:
            assert actual_result["index"] == expected_result[3]
        else:
            assert actual_result["index"] == int(derivation_path.split("/")[-1])
