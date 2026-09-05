from binascii import a2b_base64, unhexlify
from io import BytesIO

from embit import bip32, script
from embit.ec import PublicKey
from embit.hashes import tagged_hash
from embit.networks import NETWORKS
from embit.psbt import PSBT, DerivationPath, InputScope, OutputScope

from seedsigner.models.seed import Seed



class PSBTTestData:
    """
    Output data extracted from regtest psbts via the util helper methods below.
    """
    seed = Seed("model ensure search plunge galaxy firm exclude brain satoshi meadow cable roast".split())
    multisig_key_2 = Seed("better gown govern speak spawn vendor exercise item uncle odor sound cat".split())
    multisig_key_3 = Seed("sign sword lift deer ocean insect web lazy sick pencil start select".split())

    # Base psbts with various inputs for various wallet script types; outputs have been stripped
    SINGLE_SIG_NATIVE_SEGWIT_1_INPUT = "cHNidP8BADMCAAAAAU4T/0aX9mmNZHyKh+0AHYY+EtdJxndMRra0gn4QPCZdAQAAAAD9////AHAAAABPAQQ1h88DV5lJlYAAAADURWu0eYGA/OFm4Wt3dUJ44H2DzgcPO6J+nF0t9lqMqgLDxbT8Qez0U3W7o1JwT1FQ4fWFAbcK5eJ3NDnETRryMhAPuIL/VAAAgAEAAIAAAACAAAEAiAIAAAAB1Tct22qlCW5iTOZDfXqVu6CKlwdTtrPhbPI7pcTQ/GUBAAAAFxYAFCPpAsYWUNJnTErOjkoChnQylGp6/f///wLNLhoeAQAAABYAFI4lU5EAZIlw/MpX6r3gh1zqazEOAOH1BQAAAAAWABRYjLo+w43NT+5rzgPCNuy79lZjDm4AAAABAR8A4fUFAAAAABYAFFiMuj7Djc1P7mvOA8I27Lv2VmMOAQMEAQAAACIGAvXbqnkmWDXPNEkHznP0l2VFFql2WpgX42yD3Z9fJY/3GA+4gv9UAACAAQAAgAAAAIAAAAAAAwAAAAA="
    SINGLE_SIG_NESTED_SEGWIT_1_INPUT = "cHNidP8BADMCAAAAAdU3LdtqpQluYkzmQ316lbugipcHU7az4WzyO6XE0PxlAAAAAAD9////AHAAAABPAQQ1h88DIWg8n4AAAACkwPiG7M1QVnBPyAKQofuHpAZAXgXRNyJ15AYUNQRCFQIwD+a/8Dc8z2f/GXiC8z1fbvjC6VqIcciZQ51uU2tq9BAPuIL/MQAAgAEAAIAAAACAAAEAcwIAAAAB9EA7OurOd1aGyQJpQN+S0G+3IF31HO2UFAZnIpALsfQAAAAAAP3///8CAOH1BQAAAAAXqRQDW7vsMAXGa+tKARihpGq6ZwuDYYdxEBAkAQAAABepFGaYxdrjSngzRRSCeg3U/SKQOEfXhwAAAAABASAA4fUFAAAAABepFANbu+wwBcZr60oBGKGkarpnC4NhhwEDBAEAAAABBBYAFDriE9Kbby6bOWzXbXatODyyIRpcIgYDQD4mWFMSOO9mDOb+bwzEiaDf+1dWJICoG4BCig4K2awYD7iC/zEAAIABAACAAAAAgAAAAAAAAAAAAA=="
    SINGLE_SIG_TAPROOT_1_INPUT       = "cHNidP8BADMCAAAAAQljnRdfh8jB/p3Px/Qozd8x0+T4fxI6AwIOf7jQJm6FAAAAAAABAAAAAAAAAABPAQQ1h88DGQXiXoAAAACWEQ4AaLct5K3pnPzxRrHl/74twiazq4XLYi+gGu/5BgPEM2JVPwHaGssfGr25yECm8d73bfEpXMdNNBV3vMW72hAPuIL/VgAAgAEAAIAAAACAAAEA8wIAAAABrv27i6AMCio94q4NQzF6YKxuhgeRW1KQZm2+jWaKGDQBAAAAakcwRAIgM5nApqEOs/MiP9GMA5yKvV3a5qXp8sGfQ8edVizr/ZUCIHhDNQlYvBXCr8iTGycq1/XznJYav88tIJ5Cb7/pdMc8ASECtDcBLkIBPnoXcobfeX36XFp8nD+ZSj1DfxQbQy2JW6/9////AgDh9QUAAAAAIlEgcd/UDa6cM/La5HWyGkTvZOIFp6qTD3MlHZav5/CDmlsT5Vb6AAAAACJRIESp0pjyhqlKbwUtt6WOLKRUhX6Id49uLAK3cd0s+SWrcgAAAAEBKwDh9QUAAAAAIlEgcd/UDa6cM/La5HWyGkTvZOIFp6qTD3MlHZav5/CDmlsBAwQAAAAAIRYXKjsWmE7bdCAHODqvbHkLw5B2jIZj5C3QjXX00E6AdhkAD7iC/1YAAIABAACAAAAAgAAAAAAAAAAAARcgFyo7FphO23QgBzg6r2x5C8OQdoyGY+Qt0I119NBOgHYA"
    SINGLE_SIG_LEGACY_P2PKH_1_INPUT  = "cHNidP8BADMCAAAAAa79u4ugDAoqPeKuDUMxemCsboYHkVtSkGZtvo1mihg0AAAAAAD9////AHIAAABPAQQ1h88DZEKTEIAAAABFOKVFUmpvsmxCAlh1YH6xGPpkLNS0qGLYidlf2TMkHwLTyV38ld8evWpfC6fWTSUoGkkbCu6TfPqYFx9Hd/up4hAPuIL/LAAAgAEAAIAAAACAAAEAjgIAAAABu1uNN8B9NH+3zx1+QaZxkHPSX+7Osu4kTJ/RYweX3i8AAAAAFxYAFE6ANd2QMqwrq2YgFN/s7E9mbmHc/f///wIA4fUFAAAAABl2qRSFDsVqajk9QGakHH5tKXuflIWEBYisBsdMAAEAAAAZdqkUm0UFp//k5knGslifTh4z3o8s6/GIrHEAAAABAwQBAAAAIgYCENx0YsKdM+SNcY34QcTjuaZ9uYhS2tFoLA14o6OlJmwYD7iC/ywAAIABAACAAAAAgAAAAAAAAAAAAA=="
    MULTISIG_NATIVE_SEGWIT_1_INPUT   = "cHNidP8BADMCAAAAAbaPcIOkYKEWkbJpYrT/gbRQYzJ6CSFOJ5eeewflO6jJAAAAAAD9////AHAAAABPAQQ1h88EmoSnUYAAAAIQMkp0H2fIDDprJUDbKzC/+HxUkXMORn4E1dW9s6YYUQLOMo4uvEoFnOcNGcjrzHnZ64ZXsv22WoU7UMUfhSn2NxQPuIL/MAAAgAEAAIAAAACAAgAAgE8BBDWHzwRA+hbPgAAAAtCjPoabT6mduHms6sD7+rUniNXoDSlZvjkiYJpUC65FAqCWpcb6ZLoEcloJpk7vLpNRwwuOFNYyRAvzm28odTsIFAPNCiswAACAAQAAgAAAAIACAACATwEENYfPBMtS+WKAAAACIN1+5Cw5eeTBSKSY3g/NXrRBfXXDPEROQpFRHlmMlIECm0FA2Wj3AxUKxq9C1G9QJ2Ar5TvlMy3/VPUkfQS1HJ4UD4iQRDAAAIABAACAAAAAgAIAAIAAAQCJAgAAAAF1X+6fnEE2Mfa3mgKXygqWGWw2qQb3t1I4fdYJ3cIFowAAAAAA/f///wIA4fUFAAAAACIAIMpj8X3shRYalzfqac0USxW9AqloiW42GgwJjS3jLvSVWxAQJAEAAAAiUSBXg7Hc/rsd/34P6AqwBEDsuXzW+aNgcOsTxa+zGiHOXmsAAAABASsA4fUFAAAAACIAIMpj8X3shRYalzfqac0USxW9AqloiW42GgwJjS3jLvSVAQMEAQAAAAEFaVIhAlnU4yc1877LybCWrJke1kaZFO7WCoP2vDyEog2ERtyfIQKyV23E2SQWvjjaPhSNsRbfaZpPrORdY1Tr73Hm0Ub4nyEDy3sMBTuWlna6t45bdHdl/NzROoKeDVDMwLcIObQE9ZVTriIGAlnU4yc1877LybCWrJke1kaZFO7WCoP2vDyEog2ERtyfHA+4gv8wAACAAQAAgAAAAIACAACAAAAAAAAAAAAiBgKyV23E2SQWvjjaPhSNsRbfaZpPrORdY1Tr73Hm0Ub4nxwDzQorMAAAgAEAAIAAAACAAgAAgAAAAAAAAAAAIgYDy3sMBTuWlna6t45bdHdl/NzROoKeDVDMwLcIObQE9ZUcD4iQRDAAAIABAACAAAAAgAIAAIAAAAAAAAAAAAA="
    MULTISIG_NESTED_SEGWIT_1_INPUT   = "cHNidP8BADMCAAAAAbtbjTfAfTR/t88dfkGmcZBz0l/uzrLuJEyf0WMHl94vAQAAAAD9////AHEAAABPAQQ1h88EmoSnUYAAAAF+MfPe6kyaEEX91G1HKwksGaixXN6RMBTxIcHKjNYYoQJBzkFqUsm3ttoRsGfx+CMj/77pmyyjitqjWZPG4d3RrxQPuIL/MAAAgAEAAIAAAACAAQAAgE8BBDWHzwRA+hbPgAAAAcRAG6PxSUPbFp8IvKVuNlIQn4W5TK1ceLGdKkxdSfktA8QjWNuOjADhspq0onHkGp117FftE91lAYTev8snQsNRFAPNCiswAACAAQAAgAAAAIABAACATwEENYfPBMtS+WKAAAAB6inmZ+P+TS/JJhI/Fog5q8Rx2Nik9EJVEugTuPSDcI4CbvN4qeJalXMOlJpoKnL9Y64icQtz01M9NG6SOhcG8uQUD4iQRDAAAIABAACAAAAAgAEAAIAAAQBzAgAAAAHCfPUdyeETNxf9pkzBP2oOUfgSISrrZi4uj0boKN2PeQEAAAAA/f///wKwqEIGAQAAABepFOV0lUEDO1EMcpnbm8u5gOS//denhwDh9QUAAAAAF6kUURslNGksU91RDOgpxCM7IQOoQaSHAAAAAAEBIADh9QUAAAAAF6kUURslNGksU91RDOgpxCM7IQOoQaSHAQMEAQAAAAEEIgAgDHlipQ8OV+Wko64bycNh+v4LfTW5d8cTv3T1n4XDS/sBBWlSIQIsxclipQM/Gs3kdO+Mlg1gbcMRf1ukSklJhhQ8iMXpSSEDjvwJUpUWl14h2ma/DH5VeAEhM9PxTz70b6lOAgDiWrshA8FwdXOWiPDUIOtV4aCz/ZxfLr9fwrpHQLCUeAtGctJiU64iBgOO/AlSlRaXXiHaZr8MflV4ASEz0/FPPvRvqU4CAOJauxwPuIL/MAAAgAEAAIAAAACAAQAAgAAAAAAAAAAAIgYCLMXJYqUDPxrN5HTvjJYNYG3DEX9bpEpJSYYUPIjF6UkcA80KKzAAAIABAACAAAAAgAEAAIAAAAAAAAAAACIGA8FwdXOWiPDUIOtV4aCz/ZxfLr9fwrpHQLCUeAtGctJiHA+IkEQwAACAAQAAgAAAAIABAACAAAAAAAAAAAAA"
    MULTISIG_LEGACY_P2SH_1_INPUT     = "cHNidP8BADMCAAAAAarS4QMzScnPvNBT2B1I3h80UrSoNuKd9vZkjSl7j2WKAQAAAAD9////AHQAAABPAQQ1h88BD7iC/4AAAC16oZcoUbg2ksYGYWMICvKISPS51jTZLJ3tu4schhGxcAJ/o4LdLxGZHyVDceUz5n6ZtABk9X6nBk3yz/f+eXxkpQgPuIL/LQAAgE8BBDWHzwEDzQorgAAALaD15sHGuMCJCZiW09JfCCZEKGcn9WtB395d/8vj/WC7Am982IdFkEBytDXikxzoeLV5q3kpHg+bfmsmj7ncr1lgCAPNCistAACATwEENYfPAQ+IkESAAAAtcUAwLhCloJPpswRwhGdyG3KP1kY0VAetU6FdAmNrqQoDKFgD/CXYCi5ZHqx4HImYJZtoxpjx60Ki7kvK4Ean8FkID4iQRC0AAIAAAQBzAgAAAAFOE/9Gl/ZpjWR8ioftAB2GPhLXScZ3TEa2tIJ+EDwmXQAAAAAA/f///wI+TSQYAQAAABepFE+Jek+WpV0vCjnVpkLqKfoiLvPAhwDh9QUAAAAAF6kUdHD4u+bbshVEAVKkqRQxu+KR8FKHaAAAAAEDBAEAAAABBGlSIQLUf/ihLNEohwIQiCxVNGmPROLzi8t9FnV6DmfCuEhXHCEDK1QlMflvscOGZmSDWJi90FPUQvNFTQUbkkRdowbR0RghA2T1w+njATChE10XcsbguMj0J5RIzJ5TVN7sbVckbzUWU64iBgLUf/ihLNEohwIQiCxVNGmPROLzi8t9FnV6DmfCuEhXHBAPuIL/LQAAgAAAAAAAAAAAIgYDZPXD6eMBMKETXRdyxuC4yPQnlEjMnlNU3uxtVyRvNRYQA80KKy0AAIAAAAAAAAAAACIGAytUJTH5b7HDhmZkg1iYvdBT1ELzRU0FG5JEXaMG0dEYEA+IkEQtAACAAAAAAAAAAAAA"

    # Unlike the fixtures above, this is a complete psbt: its outputs are intact and it
    # has its own wallet. Use it wherever a test needs more than one input, or needs
    # inputs and change at known, differing address indices.
    #
    #   PSBT Tx and Wallet Details
    #   - Single Sig Wallet P2WPKH (Native Segwit) with no passphrase
    #   - Regtest 394aed14 m/84'/1'/0' tpubDC4rddHCzuinGFEKhiD8A3Ku5GRcNVAz3BitfwL4wn7zKPCya4i2CZLX8uoP8oCdC8VEe4jXb5u9ePCSrRA68YRSgBQra5YzBajyxKFDz4C
    #   - 2 Inputs
    #       - 56,522,834 sats at 1/6
    #       - 1,990,245,069 sats at 1/0
    #   - 4 Outputs
    #       - 1 Output spend to another wallet: 123,456 sats to bcrt1q7cw0wzy8g6mq5qvkpvhnk5gsps5ncy3srp0n2j
    #       - 3 Outputs change
    #           - 1/7 address bcrt1q53j0xwuskuf5gnvynadh0hlazyy8srydlucrhg with amount 123,456 sats
    #           - 1/8 address bcrt1q5gtw3zfp4cx67yk5q42q6j6rfza8aqcwpyyslv with amount 56,399,242 sats
    #           - 1/9 address bcrt1q9rrg7399m43cn0yg4tz0v0ate89jgf2d6kpz7v with amount 1,990,121,477 sats
    #       - Fee 272 sats
    two_input_seed = Seed("goddess rough corn exclude cream trial fee trumpet million prevent gaze power".split())
    SINGLE_SIG_NATIVE_SEGWIT_2_INPUTS = "cHNidP8BANgCAAAAAsTXZs3fz/dmGb6M80+jjvJZdYya+cw5bT/dGuhZFdSlAAAAAAD9////qo6xg/UZAvUkcbse1F+C9zbP/FeZNjThx7SCIn6eMCgBAAAAAP3///8EQOIBAAAAAAAWABSkZPM7kLcTRE2En1t33/0RCHgMjQXYnnYAAAAAFgAUKMaPRKXdY4m8iKrE9j+rycskJU1A4gEAAAAAABYAFPYc9wiHRrYKAZYLLztREAwpPBIwipVcAwAAAAAWABSiFuiJIa4NrxLUBVQNS0NIun6DDtoRAABPAQQ1h88DBcQGZIAAAAA+0J+jlNL3dpWwlnBi8Dx+Ipg4e6uvB3HdjzFPX7r9CAOOlAIxgII+/xCcj+XoEenKH7wj5s5wlu7Q7CCZWFLGLhA5Su0UVAAAgAEAAIAAAACAAAEA7QIAAAAEE6njX/fnvn7hbkKIRcxzNYFOSfbCdNeWnd7Fe/1UcQ0BAAAAAP3///8TqeNf9+e+fuFuQohFzHM1gU5J9sJ015ad3sV7/VRxDQMAAAAA/f///xOp41/3575+4W5CiEXMczWBTkn2wnTXlp3exXv9VHENBAAAAAD9////E6njX/fnvn7hbkKIRcxzNYFOSfbCdNeWnd7Fe/1UcQ0GAAAAAP3///8CUnheAwAAAAAWABRCfygPJ+Fjsx4BknYvvm3A3qKn2xJ/XQcAAAAAF6kU1I4TAst5nAj15ey7vwe5cM3OFq+HlhEAAAEBH1J4XgMAAAAAFgAUQn8oDyfhY7MeAZJ2L75twN6ip9sBAwQBAAAAIgYCo7sfm78RQY3B5n0ac/QF8VtMAzFnci+h5D1MtpgRY7oYOUrtFFQAAIABAACAAAAAgAEAAAAGAAAAAAEAcQIAAAABxY7wh0nsfJQfzWrD/9rN9BYsM+iOmPaO6I0ANFgO/PcAAAAAAP3///8CptiUAAAAAAAWABRIm4HhQY/TzOjeWSPRrbuJo9MlW826oHYAAAAAFgAU0z+0L2QSLGtyQTn8FhbCpcI7jbliAQAAAQEfzbqgdgAAAAAWABTTP7QvZBIsa3JBOfwWFsKlwjuNuQEDBAEAAAAiBgITHmebEANk81CraV4xZIpqkNjjw0tIvezl1Ism1NRH3Rg5Su0UVAAAgAEAAIAAAACAAQAAAAAAAAAAIgICuTT7WnuiUTpObjWnZFHzIeEvW9PTB+1LLVFNQJVFeIIYOUrtFFQAAIABAACAAAAAgAEAAAAHAAAAACICAk8f3hpc5C35chgSg+Pe2zZ9IhHREd4aKW2+yAMRIFeqGDlK7RRUAACAAQAAgAAAAIABAAAACQAAAAAAIgIDjt1CjvrnMMnjbmTNKUAYoKEDRbmKjNjbq+6Ppqj3bqQYOUrtFFQAAIABAACAAAAAgAEAAAAIAAAAAA=="

    # Also complete and on the same wallet as the fixture above. Taproot records its
    # derivation paths in a separate map from the segwit-v0 one, so this is what tests of
    # that split need.
    #
    #   PSBT Tx and Wallet Details
    #   - Single Sig Wallet P2TR (Taproot) with no passphrase
    #   - Regtest 394aed14 m/86'/1'/0' tpubDCawGrRg7YdHdFb9p4mmD8GBaZjJegL53FPFRrMkGoLcgLATJfksUs2y1Q7dVzixAkgecazsxEsUuyj3LyDw7eVVYHQyojwrc2hfesK4wXW
    #   - 1 Input
    #       - 3,190,493,401 sats at 1/0
    #   - 2 Outputs
    #       - 1 Output change: 2,871,443,918 sats to bcrt1prz4g6saush37epdwhvwpu78td3q7yfz3xxz37axlx7udck6wracq3rwq30 at 1/1
    #       - 1 Output spend to another wallet: 319,049,328 sats to bcrt1p6p00wazu4nnqac29fvky6vhjnnhku5u2g9njss62rvy7e0yuperq86f5ek
    #       - Fee 155 sats
    SINGLE_SIG_TAPROOT_WITH_CHANGE = "cHNidP8BAIkCAAAAAf8upuiIWF1VTgC/Q8ZWRrameRigaXpRcQcBe8ye+TK3AQAAAAAXCgAAAs7BJqsAAAAAIlEgGKqNQ7yF4+yFrrscHnjrbEHiJFExhR903ze43FtOH3BwTgQTAAAAACJRINBe93RcrOYO4UVLLE0y8pzvblOKQWcoQ0obCey8nA5GAAAAAE8BBDWHzwNMUx9OgAAAAJdr+WtwWfVa6IPbpKZ4KgRC0clbm11Gl155IPA27n2FAvQCrFGH6Ac2U0Gcy1IH5f5ltgUBDz2+fe8iqL6JzZdgEDlK7RRWAACAAQAAgAAAAIAAAQB9AgAAAAGAKOOUFIzw9pbRDaZ7F0DYhLImrdMn//OSm++ff5VNdAAAAAAAAQAAAAKsjLwAAAAAABYAFKEcuxvXmB3rWHSqSviP5mrKMZoL2RArvgAAAAAiUSBGU0Lg5fx/ECsB1Z4ZUqXQFSLFnlmpm0rm5R2l599h2AAAAAABASvZECu+AAAAACJRIEZTQuDl/H8QKwHVnhlSpdAVIsWeWambSublHaXn32HYAQMEAAAAACEWF7hZVn7pIDR429kAn/WDeQiWjZey1iGHztsL1H83QLMZADlK7RRWAACAAQAAgAAAAIABAAAAAAAAAAEXIBe4WVZ+6SA0eNvZAJ/1g3kIlo2XstYhh87bC9R/N0CzACEHbJdqWyMxF2eOPr6YRXUJmry04HUbgKyeM2IZeG+NI9AZADlK7RRWAACAAQAAgAAAAIABAAAAAQAAAAEFIGyXalsjMRdnjj6+mEV1CZq8tOB1G4CsnjNiGXhvjSPQAAA="

    SINGLE_SIG_INPUTS = [
        SINGLE_SIG_NATIVE_SEGWIT_1_INPUT,
        SINGLE_SIG_NESTED_SEGWIT_1_INPUT,
        SINGLE_SIG_TAPROOT_1_INPUT,
        SINGLE_SIG_LEGACY_P2PKH_1_INPUT,
    ]

    MULTISIG_INPUTS = [
        MULTISIG_NATIVE_SEGWIT_1_INPUT,
        MULTISIG_NESTED_SEGWIT_1_INPUT,
        MULTISIG_LEGACY_P2SH_1_INPUT
    ]

    ALL_INPUTS = SINGLE_SIG_INPUTS + MULTISIG_INPUTS

    MULTISIG_NATIVE_SEGWIT_DESCRIPTOR = "wsh(sortedmulti(2,[0fb882ff/48h/1h/0h/2h]tpubDF3QYaRazZ44jHz3jaSPRGCLVYj7D8j4mVVUTCr3CHsfuvoV2Z73eTcvHc8sP3Dj58yEfkG57iBpKTuHv3dNAUcFufCxx26SAbrWque5gts/<0;1>/*,[03cd0a2b/48h/1h/0h/2h]tpubDEPEYgTj1ddmZqDdpiq5Gjttx3CnNSFppSaUa5eHAUVNMD2FE1ihGA2EMP92mzmSUGJsTAgMhBTACd9xsRDB5K4GKJH8RzbRuFUrmVVLR15/<0;1>/*,[0f889044/48h/1h/0h/2h]tpubDFQDKbH2mDqNDPNaUVxM6R5mHhzC4u5F6mNnUkCf6gBMbcENMQ1ZGFLZc3QwgdEv2f34wkTvLMG5kD8AZEZRhat1HQDj42eVxQSxbcqxn31/<0;1>/*))#jsc5nnpk"
    MULTISIG_NESTED_SEGWIT_DESCRIPTOR = "sh(wsh(sortedmulti(2,[03cd0a2b/48h/1h/0h/1h]tpubDEPEYgTj1ddmXAEnYZG8LjUxRcYNX8xw2QkVEkHj8HVsH3bt3QcS9tgXdfrm31SgNxFY7EfgYcc2BNxcMtg6cB4pdXjND9GjA895aJNsBQp/<0;1>/*,[0fb882ff/48h/1h/0h/1h]tpubDF3QYaRazZ44hqgAAHf16EbhRGBfokgLHcQ5pWB1iQsqLgtTK6rR7XHUBVmwAcv5iU4hQR78PLThbHf5427oAk1hz7Ph8K1r3PUgstnZBvx/<0;1>/*,[0f889044/48h/1h/0h/1h]tpubDFQDKbH2mDqNCqnWUKyj9N2GsGmfJ1mTaoz6BBJ1PRj8FMfd7f3XhFeGBadLtszMp3gRboRmmkWa8TCY8HJN85ouYUALSDnGCzg3vpVDLgd/<0;1>/*)))#per3463t"
    MULTISIG_LEGACY_P2SH_DESCRIPTOR   = "sh(sortedmulti(2,[0fb882ff/45h]tpubD8Nq4eMvojKe9yL3k7vVq42NdriZpkPMCduzQedPRe9Cy6kCfMiGD49oQvomKgrzk4qUb1NVsg6gJeP4MsVTKDUWaubTWHvqTwNg2GCpbZK/<0;1>/*,[0f889044/45h]tpubD8NkS3Gngj7L4FJRYrwojKhsx2seBhrNrXVdvqaUyvtVe1YDCVcziZVa9g3KouXz7FN5CkGBkoC16nmNu2HcG9ubTdtCbSW8DEXSMHmmu62/<0;1>/*,[03cd0a2b/45h]tpubD8HkLLgkdJkVitn1i9CN4HpFKJdom48iKm9PyiXYz5hivn1cGz6H3VeS6ncmCEgamvzQA2Qofu2YSTwWzvuaYWbJDEnvTUtj5R96vACdV6L/<0;1>/*))#8pfqnxa2"

    # Internal self-transfer and change outputs
    SINGLE_SIG_NATIVE_SEGWIT_CHANGE        = "2202022c15efd08c822a6287f1b42b6c30ecced47f1c5484c3e7d72e7680a305893d27180fb882ff5400008001000080000000800100000000000000010308e8fcf105000000000104160014acc1340709e9b7babeff921806f0570c652bd05800"
    SINGLE_SIG_NATIVE_SEGWIT_SELF_TRANSFER = "2202028d0b3faac6bd38acc2075191bec98612b87100047a7a8d77ed9ef4e3ae03dfc3180fb882ff540000800100008000000080000000000600000001030890d00300000000000104160014f8b609a3b82d8091fb2c99f4f0302bbb838e48ed00"
    SINGLE_SIG_NESTED_SEGWIT_CHANGE        = "01001600145f801cc93ce9357afef02087213775e98b95923d22020236cdb1b950a92dc2f72182c88af0c898a3d8db06dcf57c3ea662850beffc2793180fb882ff3100008001000080000000800100000000000000010308aef3c90500000000010417a9148f71f1b34439b80a1c37a9501d0facf4fa9bf8d38700"
    SINGLE_SIG_NESTED_SEGWIT_SELF_TRANSFER = "0100160014b574a614ffb9a43ee85f7a08e6ba6f444908406622020212d8d9d112a7b45aae931f59fb459150b8e5fc5377d9efc176253e284e8443a0180fb882ff31000080010000800000008000000000010000000103084cd82b0000000000010417a914a89b66ac7d9de4d7d5da4dae71065147355643148700"
    SINGLE_SIG_TAPROOT_CHANGE              = "010308d50ff205000000000104225120f7fae84e379ba7acfef153518f35c109be2e69dd1658e3a5d2b445abd4b6cf730105200a891a9b5600abef50c78e1c9e5d1ebf95d515667c2033098f8f843fa7f459ae21070a891a9b5600abef50c78e1c9e5d1ebf95d515667c2033098f8f843fa7f459ae19000fb882ff560000800100008000000080010000000000000000"
    SINGLE_SIG_TAPROOT_SELF_TRANSFER       = "01030890d0030000000000010422512045d38d7d2f9b3b2135f93ea1d771495f02eea63deb0bd94c365d8387cf9f5c740105209b36fb4d174ca5ed1a4c0d118bcb75fa4bb5408002b242c773e23df4599f9e6c21079b36fb4d174ca5ed1a4c0d118bcb75fa4bb5408002b242c773e23df4599f9e6c19000fb882ff560000800100008000000080000000000100000000"
    SINGLE_SIG_LEGACY_P2PKH_CHANGE         = "220203b6390d6aa2516f1004fecb1439cfdb2038f6e1f2504376eae6df3dc1634ac191180fb882ff2c000080010000800000008001000000000000000103088e0ff2050000000001041976a9140de643ba8e5659f365b10da0c879a3999f4a348588ac00"
    SINGLE_SIG_LEGACY_P2PKH_SELF_TRANSFER  = "220202c168e3f31b9a7c31aa16b33b3ee47cd64ac5d30d31d9c709e7616bc9389d835e180fb882ff2c0000800100008000000080000000000100000001030890d003000000000001041976a914fef98f1e7c7d975710b8b8b0c12d5737be81e7a688ac00"
    MULTISIG_NATIVE_SEGWIT_CHANGE          = "01016952210234886728fde2bc0e8b9d7f6c4c452c700add80b2690bb237a3c3a6f4e7714c5221025485ce74baeeb49296f486e6780e1e2b46187943de4da3bb8f1a202cd6695393210355da420fc1b72af894a8532bc917528bd0e3bfbc435c33f8f0d9100671084b2353ae22020234886728fde2bc0e8b9d7f6c4c452c700add80b2690bb237a3c3a6f4e7714c521c0fb882ff3000008001000080000000800200008001000000040000002202025485ce74baeeb49296f486e6780e1e2b46187943de4da3bb8f1a202cd66953931c03cd0a2b30000080010000800000008002000080010000000400000022020355da420fc1b72af894a8532bc917528bd0e3bfbc435c33f8f0d9100671084b231c0f88904430000080010000800000008002000080010000000400000001030887f3f105000000000104220020751780ba145dd0a289a88bdccff824116518df23cb674e810654313520eb74db00"
    MULTISIG_NATIVE_SEGWIT_SELF_TRANSFER   = "010169522102519fb0e4b5de132efb1c603e37007baa8de848609627fb1c8af6670f97dba8162102523b7ebc26a2a23d5f863428bf6047cf146904a5ec33724c0be5444c22e2b9d5210302d297b3658cb2643df5bbb5b8edd8d015d96c0a1547e69ef440e6a72b3af70653ae22020302d297b3658cb2643df5bbb5b8edd8d015d96c0a1547e69ef440e6a72b3af7061c0fb882ff300000800100008000000080020000800000000002000000220202523b7ebc26a2a23d5f863428bf6047cf146904a5ec33724c0be5444c22e2b9d51c03cd0a2b300000800100008000000080020000800000000002000000220202519fb0e4b5de132efb1c603e37007baa8de848609627fb1c8af6670f97dba8161c0f88904430000080010000800000008002000080000000000200000001030890d0030000000000010422002074ef7b55285cc4fe433074ed87e54ffc3a2d2d1e89e411112b8869e28d480eaf00"
    MULTISIG_NESTED_SEGWIT_CHANGE          = "0100220020b10852265d3992de36ba959d0ffedac561941910f3c64305c55329c3eded6723010169522102ecf1ff790b21ac813fd16ae103adf49e8783d4e1c69efab0dc65ff21f9e2d0fc21038427b43c1e5009b51c4a52aba48157aa2cb0f3e650ee4abd26578767c2915f882103dad1dced2f90f7d9723a67afbde437ac1a4a3ab7e991502a62442212056bdea653ae220203dad1dced2f90f7d9723a67afbde437ac1a4a3ab7e991502a62442212056bdea61c0fb882ff3000008001000080000000800100008001000000000000002202038427b43c1e5009b51c4a52aba48157aa2cb0f3e650ee4abd26578767c2915f881c03cd0a2b300000800100008000000080010000800100000000000000220202ecf1ff790b21ac813fd16ae103adf49e8783d4e1c69efab0dc65ff21f9e2d0fc1c0f8890443000008001000080000000800100008001000000000000000103089a0ff20500000000010417a914e158e224d933585dcf9077e6f0556ddf0b82c3b18700"
    MULTISIG_NESTED_SEGWIT_SELF_TRANSFER   = "01002200201dc4bf10ca0b4a1106650e2459e8a917a231fd24b4ecdbf1711f4ec063a34df101016952210234361c2816115f8745e95d14243651f622fded6e1f3e30b32ac480e53e3fed3b2102cfd9087055c61d1226649885397872d5f0174186fb2919a7ce0e5149224f78c92103c68ecdc19777b9179b3185a8af96a72baaf3975b7abb125733532031d3b034ab53ae220202cfd9087055c61d1226649885397872d5f0174186fb2919a7ce0e5149224f78c91c0fb882ff300000800100008000000080010000800000000001000000220203c68ecdc19777b9179b3185a8af96a72baaf3975b7abb125733532031d3b034ab1c03cd0a2b30000080010000800000008001000080000000000100000022020234361c2816115f8745e95d14243651f622fded6e1f3e30b32ac480e53e3fed3b1c0f88904430000080010000800000008001000080000000000100000001030890d0030000000000010417a9149c28aee05bdbe48728adc4155c24ab180f899fce8700"
    MULTISIG_LEGACY_P2SH_CHANGE            = "0100695221031ce6ddb7a26336264b132c1b45c3e631e8502bc155226d46fc38d73d57f9e4ff21031d9e6e094413dc3a508518f729af23a35b3943ca79bafbc55afab631595e5ccf2103c3a6cb2786d860aa1ccff81fae79c1a973bc8a79938af6ff3c75fc4f54333d7353ae220203c3a6cb2786d860aa1ccff81fae79c1a973bc8a79938af6ff3c75fc4f54333d73100fb882ff2d00008001000000000000002202031d9e6e094413dc3a508518f729af23a35b3943ca79bafbc55afab631595e5ccf1003cd0a2b2d00008001000000000000002202031ce6ddb7a26336264b132c1b45c3e631e8502bc155226d46fc38d73d57f9e4ff100f8890442d0000800100000000000000010308000ff20500000000010417a91402e6f3cb4a98d88fbedf0e43869ce9e1a01e8d9f8700"
    MULTISIG_LEGACY_P2SH_SELF_TRANSFER     = "01006952210283a03b8fa4cce258e536514416f448cf20aca8ef42492413c149a329029adb4e210346b5d12c00554bce6920e60d647893db6555e0844b8583747bc0ca1ecaba3e1c2103bfc0f7151411ace2d2eef986efca7873dabdc0f6f1bbea7bd3c863be1f2e00de53ae220203bfc0f7151411ace2d2eef986efca7873dabdc0f6f1bbea7bd3c863be1f2e00de100fb882ff2d000080000000000100000022020346b5d12c00554bce6920e60d647893db6555e0844b8583747bc0ca1ecaba3e1c1003cd0a2b2d000080000000000100000022020283a03b8fa4cce258e536514416f448cf20aca8ef42492413c149a329029adb4e100f8890442d000080000000000100000001030890d0030000000000010417a914505efc1adc72f354e827da94b49dec46d80717068700"

    # Fingerprint-collision pair: two unrelated seeds whose master fingerprints collide,
    # for tests of the honest-collision case (a genuine foreign key that names our
    # fingerprint without any forgery involved). Any two seeds collide with probability 1
    # in 2^32.
    collision_seed_a = Seed("trend local ecology client torch face wink soup right craft nerve bread".split())
    collision_seed_b = Seed("oval stadium chimney tone deny catch idea gasp absorb short vibrant tribe".split())

    # External receive outputs
    recipient_seed = Seed("shove album flame dad equal cook spike cheap hollow exit great forest".split())
    recipient_multisig_key_2 = Seed("grow curve arrive reflect alarm water black funny comfort match attend tired".split())
    recipient_multisig_key_3 = Seed("hunt air season climb grocery shadow monitor please virtual cave young denial".split())
    SINGLE_SIG_NATIVE_SEGWIT_RECEIVE = "01030890d00300000000000104160014fc243291eec14337ce81817778c251e92da7c45600"
    SINGLE_SIG_NESTED_SEGWIT_RECEIVE = "01030890d0030000000000010417a914094a43bc6e1632bd092f1beb8a67dc63160be6ff8700"
    SINGLE_SIG_TAPROOT_RECEIVE       = "01030890d003000000000001042251200d30561bed15df986cafbfb58150a2208cf422b4efa6891d0534fba834bf06c600"
    SINGLE_SIG_LEGACY_P2PKH_RECEIVE  = "01030890d003000000000001041976a91467df58b6a9c4c0a2569595036fe6f928390ecd9588ac00"
    MULTISIG_NATIVE_SEGWIT_RECEIVE   = "01030890d003000000000001042200200936ff1943bbe5c037ad9e9839ca3effe24d8b22fd38cc2601c9007cc0f210a100"
    MULTISIG_NESTED_SEGWIT_RECEIVE   = "01030890d0030000000000010417a9141d3c080d4b05358b8cc439ef12534250563f34a08700"
    MULTISIG_LEGACY_P2SH_RECEIVE     = "01030890d0030000000000010417a914fa70ebb69e283b493770c5a8fa19ec76da321de68700"

    # The same output as MULTISIG_NATIVE_SEGWIT_RECEIVE, but populated the way a
    # coordinator that also holds the recipient's descriptor populates it: the 2-of-3
    # script the output pays, plus a derivation path entry for each of its cosigners.
    # Built from recipient_seed, recipient_multisig_key_2 and recipient_multisig_key_3,
    # each at m/48h/1h/0h/2h/0/0.
    MULTISIG_NATIVE_SEGWIT_RECEIVE_ANNOTATED = "0101695221027d99f92952795d306ef9b87a9d16c94bedc4b17613042a6f1b80af0e9c7839a32103208d94f8b4df19bcb76c309887904920064ccc417225520790426cb0e40fe6552103d36ac409c6198fee6eae72bf5c38424f3f2e2077a67aaf14d535fd1021b97c4953ae2202027d99f92952795d306ef9b87a9d16c94bedc4b17613042a6f1b80af0e9c7839a31c0f7d3df0300000800100008000000080020000800000000000000000220203208d94f8b4df19bcb76c309887904920064ccc417225520790426cb0e40fe6551ccd063d44300000800100008000000080020000800000000000000000220203d36ac409c6198fee6eae72bf5c38424f3f2e2077a67aaf14d535fd1021b97c491c2f54d8a930000080010000800000008002000080000000000000000001030890d003000000000001042200200936ff1943bbe5c037ad9e9839ca3effe24d8b22fd38cc2601c9007cc0f210a100"

    ALL_EXTERNAL_OUTPUTS = [
        SINGLE_SIG_NATIVE_SEGWIT_RECEIVE,
        SINGLE_SIG_NESTED_SEGWIT_RECEIVE,
        SINGLE_SIG_TAPROOT_RECEIVE,
        SINGLE_SIG_LEGACY_P2PKH_RECEIVE,
        MULTISIG_NATIVE_SEGWIT_RECEIVE,
        MULTISIG_NESTED_SEGWIT_RECEIVE,
        MULTISIG_LEGACY_P2SH_RECEIVE,
    ]


    """
    Utils to generate the above PSBT data snippets
    """
    def dump_outputs(psbt_base64: str):
        psbt = PSBT.parse(a2b_base64(psbt_base64))
        for output in psbt.outputs:
            out_type = "external recipient"
            if output.bip32_derivations:
                pubkey, der = list(output.bip32_derivations.items())[0]
                if der.derivation[-2] == 1:
                    out_type = "change"
                else:
                    out_type = "self-transfer"

            elif output.taproot_bip32_derivations:
                pubkey, (leaf_hashes, der) = list(output.taproot_bip32_derivations.items())[0]
                if der.derivation[-2] == 1:
                    out_type = "change"
                else:
                    out_type = "self-transfer"

            # Must specify `version=2` so script_pubkey is included
            print(output.script_pubkey.address(NETWORKS["regtest"]), out_type, output.serialize(version=2).hex(), '\n')


    def strip_psbt_outputs(psbt_base64: str):
        psbt = PSBT.parse(a2b_base64(psbt_base64))
        psbt.outputs.clear()
        print(psbt)



def create_output(output_hex: str, value: int = None) -> OutputScope:
    """
    Given a change, self-transfer, or receive output's serialized hex, create the
    corresponding OutputScope that can be added to a PSBT.

    Optionally override the output's `value`.
    """
    output = OutputScope.read_from(BytesIO(unhexlify(output_hex)))
    if value is not None:
        output.value = value
    return output


def root_for_seed(seed: Seed) -> bip32.HDKey:
    """
    A seed's master key, built the way PSBTParser builds it.

    The network only picks the version bytes, and neither the fingerprint nor any of the
    key material compared below depends on those, so the fixtures' regtest is used
    throughout.
    """
    return bip32.HDKey.from_seed(seed.seed_bytes, version=NETWORKS["regtest"]["xprv"])


def foreign_public_key(derivation_path: str = "m/84h/1h/0h/0/0", seed: Seed = None) -> PublicKey:
    """
    A genuine public key belonging to some seed other than the signing seed, for building
    scopes that name a key the signing seed does not control.
    """
    if seed is None:
        seed = PSBTTestData.recipient_seed
    return root_for_seed(seed).derive(derivation_path).get_public_key()


def tapleaf_hash(public_key: PublicKey, leaf_version: int = 0xC0) -> bytes:
    """
    The BIP-341 leaf hash of the simplest tapscript (a lone key checksig), built the same
    way embit builds it when it signs a script path spend.
    """
    OP_PUSHBYTES_32 = b"\x20"
    OP_CHECKSIG = b"\xac"
    leaf_script = script.Script(OP_PUSHBYTES_32 + public_key.xonly() + OP_CHECKSIG)
    return tagged_hash("TapLeaf", bytes([leaf_version]) + leaf_script.serialize())


# BIP-341's provably unspendable internal key (aka "NUMS" point: "Nothing Up My Sleeve"):
# the SHA256 of the standard uncompressed encoding of the secp256k1 generator point,
# lifted to a curve point. A taproot address built for script path spends only uses this
# as its internal key, so that nobody holds a key path to it.
NUMS_INTERNAL_KEY = PublicKey.from_xonly(unhexlify("50929b74c1a04954b78b4b6035e97a5e078a5a0f28ec96d547bfee9ace803ac0"))


def p2tr_with_script_tree(internal_public_key: PublicKey, merkle_root: bytes) -> script.Script:
    """
    The scriptPubKey of a taproot output whose internal key is tweaked by a script tree's
    merkle root, built the same way embit builds the empty-tree form. embit's script.p2tr
    cannot build this one: it asks the script tree for its own tweak, and embit defines no
    script tree type to ask.
    """
    OP_1 = b"\x51"  # segwit version byte
    OP_PUSHBYTES_32 = b"\x20"
    return script.Script(OP_1 + OP_PUSHBYTES_32 + internal_public_key.taproot_tweak(merkle_root).xonly())


def claim_seed_owns_key(scope: InputScope | OutputScope, claimed_derivation_path: str, public_key: PublicKey, seed: Seed = None, is_taproot: bool = False, leaf_hashes: list = None):
    """
    Writes a derivation into the scope claiming that seed owns public_key at
    claimed_derivation_path.

    Building one of these needs no key material from the seed, because nothing in a psbt
    ties a fingerprint to the key written beside it. The fingerprint is all it takes, and
    that is published in every psbt the seed has ever been sent. So pass a public_key the
    seed does not own and the result is a psbt asserting ownership that does not exist.

    For taproot, leaf_hashes names the leaf scripts the key is used in. An entry naming
    none of them is claiming to be the output's internal key; see tapleaf_hash.
    """
    if seed is None:
        seed = PSBTTestData.seed

    derivation_path = DerivationPath(
        root_for_seed(seed).my_fingerprint, bip32.parse_path(claimed_derivation_path))

    if is_taproot:
        scope.taproot_bip32_derivations[public_key] = (leaf_hashes or [], derivation_path)
    else:
        scope.bip32_derivations[public_key] = derivation_path
