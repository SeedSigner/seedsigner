# SeedSigner Electrum seed phrase support

SeedSigner supports loading of [Electrum's Segwit seed phrases](https://electrum.readthedocs.io/en/latest/seedphrase.html#electrum-seed-version-system).  This is considered an Advanced feature that is disabled by default.  

To load an Electrum Segwit seed phrase, first enable Electrum seed support in Settings -> Advanced -> Electrum seed support.  After this option is enabled, the user will now be able to enter an Electrum seed phrase by selecting "Enter Electrum seed" in the Load Seed screen.

Some SeedSigner functionality is deliberately disabled when using an Electrum mnemonic:

- BIP-85 child seeds
	- Not applicable for Electrum seed types
- SeedQR backups
	- Since Electrum seeds are not supported by other SeedQR implementations, it would be dangerous to use SeedQR as a backup tool for Electrum seeds and is thus disabled
- Custom derivations
	- Hard coded derivation path and script types in SeedSigner to match Electrum wallet software. These are m/0h for single sig and m/1h for multisig
	- User-chosen custom derivations are thus not supported for Electrum seeds
