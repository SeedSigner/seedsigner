# SeedSigner Electrum seed phrase support

SeedSigner supports loading of Electrum's Segwit seed phrases.  This is considered an Advanced feature that is disabled by default.  

To load an Electrum Segwit seed phrase, first enable Electrum seed support in Settings -> Advanced -> Electrum seed support.  After this option is enabled, the user will now be able to enter an Electrum seed phrase by selecting "Enter Electrum seed" in the Load Seed screen.

Some SeedSigner functionality is deliberately disabled when using an Electrum mnemonic:

- BIP-85 child seeds
	- Not applicable for Electrum seed types
- SeedQR backups
	- Since Electrum seeds are not supported by other SeedQR implementations, it would be dangerous to use SeedQR as a backup tool for Electrum seeds and is thus disabled
- Custom derivations
	- Like BIP-85 child seeds, custom derivations are not applicable to Electrum seeds and thus disabled
