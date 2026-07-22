# SeedSigner Shamir Secret Sharing support

SeedSigner supports loading of [SLIP-39 Shamir Secret Sharing](https://github.com/satoshilabs/slips/blob/master/slip-0039.md) seed phrases. This is considered an Advanced feature that is disabled by default.

To load SLIP-39 Shamir shares, first enable Shamir support in Settings -> Advanced -> Shamir's Secret Sharing. After this option is enabled, the user will now be able to enter Shamir shares by selecting "Shamir recovery" in the Load Seed screen.

Some SeedSigner functionality is deliberately disabled when using Shamir Secret Sharing:

- BIP-85 child seeds
	- Not applicable for Shamir seed types
- SeedQR backups
	- Since Shamir shares use SLIP-39 wordlist instead of BIP-39, they are not compatible with SeedQR implementations which assume BIP-39 format and are thus disabled for safety
- Custom derivations
	- Shamir seeds use standard derivation paths
- Multi-language wordlists
	- Only English SLIP-39 wordlist is supported
- Seed phrase export
	- Individual shares cannot be displayed as they would be incomplete and potentially misleading
	- The implementation stores multiple shares but can only display fingerprint information

## Technical Details

- Supports both 20-word and 33-word SLIP-39 shares
- SLIP-39 passphrase support (called "Custom Extension" in the interface, equivalent to BIP-39 passphrase)
- Requires multiple valid shares to reconstruct the master seed
- Uses the `embit` library's SLIP-39 implementation for share validation and seed reconstruction
- Share validation occurs during entry to prevent invalid shares from being accepted
- Extendable flag feature is not yet supported and will be added as soon as `embit` supports it
- For testing purposes only (do not use with real secrets), there is an online SLIP-39 tool by Ian Coleman: https://iancoleman.io/slip39/