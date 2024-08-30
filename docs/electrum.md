# SeedSigner Electrum seed phrase support

SeedSigner supports loading of [Electrum's Standard(P2PKH) and Native Segwit seed phrases](https://electrum.readthedocs.io/en/latest/seedphrase.html#electrum-seed-version-system).  The "old" mnemonics used prior to Electrum wallet software version 2.0 are not currently supported.

To load an Electrum Segwit seed phrase, first enable Electrum seed support in Settings -> Advanced -> Electrum seed support.  After an electrum seed length is selected, the user will now be able to enter an Electrum seed phrase by selecting "Enter Electrum seed" in the Load Seed screen.

The user has the option to load a 12 word or 13 word seed phrase.  Note that the 13th word does NOT refer to the custom extension words (passphrase), but rather Electrum wallet software used 13 word seed phrases from version 2.0 up until prior to version 2.7.  If you need to enter the words you used for "Extend this seed with custom words" in the electrum software, first enter the seed, then before finalizing you will be given the option to add a custom extension similar to the workflow for entering a BIP-39 seed and BIP-39 passphrase.

Some SeedSigner functionality is deliberately disabled when using an Electrum mnemonic:

- BIP-85 child seeds
	- Not applicable for Electrum seed types
- SeedQR backups
	- Since Electrum seeds are not supported by other SeedQR implementations, it would be dangerous to use SeedQR as a backup tool for Electrum seeds and is thus disabled
- Custom derivations
	- Hard coded derivation path and script types in SeedSigner to match Electrum wallet software. These are m/0h for single sig and m/1h for multisig
	- User-chosen custom derivations are thus not supported for Electrum seeds
