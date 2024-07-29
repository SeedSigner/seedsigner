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

    # jdlcdl: these vectors created with electrum & sparrow as a 2 of 3 multisig based on bip39-bip32-standard-path wallets
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

        # multisig taproot on testnet, not supported
        # TODO: find what a multisig-taproot descriptor would look like and add a test so we can fall into the last condition exception.

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
