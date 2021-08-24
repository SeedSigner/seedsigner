# QR Formats

### Scanning QR Codes

SeedSigner supports scanning the following QR formats

Animated QR Formats:
- PSBT
    - Blockchain Commons [UR2 PSBT](https://github.com/BlockchainCommons/Research/blob/master/papers/bcr-2020-006-urtypes.md)
    - Specter Desktop base64 segments animated
    - [Legacy UR](https://github.com/BlockchainCommons/Research/blob/d4d72417a1ff18f9422371b2f71bf2652adce41c/papers/bcr-2020-005-ur.md) Format that should no longer be used

Static QR Formats:
- PSBT
    - Base64 (if the PSBT byte size is too large, SS may have trouble scanning)
- Seed
    - SeedSigner Seed QR format
	- English Bip39 Mnemonic words separated by a space. Currently only supports 12 and 24 word seeds.
	- English Bip39 Mnemonic with only first 4 letters seperated by a space. Currently only supports 12 and 24 word seeds.

### Displaying QR Codes

SeedSigner supports displaying QR's in the following formats

Animated QR Formats:
- PSBT
    - Blockchain Commons [UR2 PSBT](https://github.com/BlockchainCommons/Research/blob/master/papers/bcr-2020-006-urtypes.md)
	- Specter Desktop base64 segments animated

Static QR Formats:
- Seed
    - SeedSigner Seed QR format