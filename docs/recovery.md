# SeedSigner Recovery Information

SeedSigner creates extended public keys for the coordinator following [slip-0132](https://github.com/satoshilabs/slips/blob/master/slip-0132.md) to encode the extended public key. SeedSigner supports native and nested segwit for single sig and multisig.

Derivation paths for standard script types for mainnet:

- Single Sig
	- Native Segwit
		- Derivation Path: m/84'/0'/0'
		- Script Type: P2WPKH
		- Public Key Encoding: 0x04b24746 - zpub
	- Nested Segwit
		- Derivation Path: m/49'/0'/0'
		- Script Type: P2WPKH in P2SH
		- Public Key Encoding: 0x049d7cb2 - ypub
	- Taproot
		- Derivation Path: m/86'/0'/0'
		- Script Type: P2TR
		- Public Key Encoding: 0x0488b21e - xpub
- Multisig
	- Native Segwit
		- Derivation Path: m/48'/0'/0'/2'
		- Script Type: P2WSH
		- Public Key Encoding: 0x02aa7ed3 - Zpub
	- Nested Segwit
		- Derivation Path: m/48'/0'/0'/1'
		- Script Type: P2WSH in P2SH
		- Public Key Encoding: 0x0295b43f - Ypub

Custom derivation paths are also optional when generating an xpub from SeedSigner. The Public Key Encodings are detected based on the derivation path configured. The `embit` bitcoin library does this detection and is documented [here](https://github.com/diybitcoinhardware/embit/blob/master/docs/api/bip32.md#detect_version). For a video explanation of these standards see a presentation by Stepan of `embit` on this topic: https://youtube.com/watch?v=JCaC5DG2HTM

Changing the network settings from main to test in SeedSigner will change the public key encoding and derivation path following [slip-0132](https://github.com/satoshilabs/slips/blob/master/slip-0132.md) standards.

Related Standards:
- [bip-0032](https://github.com/bitcoin/bips/blob/master/bip-0032.mediawiki)
- [bip-0044](https://github.com/bitcoin/bips/blob/master/bip-0044.mediawiki)
- [bip-0048](https://github.com/bitcoin/bips/blob/master/bip-0048.mediawiki)
- [bip-0049](https://github.com/bitcoin/bips/blob/master/bip-0049.mediawiki)
- [bip-0084](https://github.com/bitcoin/bips/blob/master/bip-0084.mediawiki)
- [bip-0086](https://github.com/bitcoin/bips/blob/master/bip-0086.mediawiki)
