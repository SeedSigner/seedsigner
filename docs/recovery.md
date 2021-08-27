# SeedSigner Recovery Information

SeedSigner creates extended public keys for the coordinator following [slip-0132](https://github.com/satoshilabs/slips/blob/master/slip-0132.md) to encode the extended public key. SeedSigner only supports native segwit for single sig (P2WPKH) and native segwit multisig (P2WSH).

SeedSigners default settings for "Script Policy" (2021-08-21) is Multi Sig Native Segwit. The second option is Single Sig Native Segwit.

- Single Sig Derivation Path: m/84'/0'/0'
- Single Sig Public Key Encoding: 0x04b24746 - zpub
- Multisig Dervivation Path: m/48'/0'/0'/2'
- Multisig Public Key Encoding: 0x02aa7ed3 - Zpub

Changing the network settings from main to test will change the public key encoding and derivation path following bip-0084, bip-0048 and slip-0132 standards.

Custom derivation paths will be optional in the future.
