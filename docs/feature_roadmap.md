# Feature Roadmap

Current focus: v0.5.0 preview releases.

*Note: It may or may not make sense to do minor bugfix preview releases along the way (e.g. 1.0 -> 1.1).*


## v0.5.0 Pre-Release 1.x
* Scan SeedQR / CompactSeedQR
* Add/Edit passphrase
* View seed words w/configurable warnings
* Export xpub w/configurable warnings and flow determined by Settings
* Scan PSBT
* Full PSBT review screens
* "Full Spend" (no change) warning
* Fully verify PSBT change addrs
* Send signed PSBT via QR
* QR display dimming/brightness UP/DOWN
* Subset of configurable Settings; persistent Settings storage
* SettingsQR integration proof-of-concept

Screens will be functional but not necessarily in their final presentation state (icons, text, positioning, etc).


## v0.5.0 Pre-Release 2.x
* Existing screen refinement (visual presentation, text, etc)
* Create new seed via image entropy
* Manual mnemonic seed word entry
* 12th/24th word calc
* SeedQR/CompactSeedQR manual transcription UI w/configurable UI style (dots vs grid)
* Single sig address scan and verification
* SettingsQR standalone UI refinement
* Fix broken tests
* All GUI Components support scrollable Screens


## v0.5.0 Pre-Release 3.x
* Settings: I/O Test
* Create new seed via dice rolls
* Custom derivation paths in xpub export flow
* QR display dimming/brightness, framerate, density(?) controls in transparent overlay
* HRF partner logo on startup
* Improve test suite coverage
* Further existing screen refinement
* "Final" bugfixes


## Initial v0.5.0 Release
All of the above!


## Beyond v0.5.0
These features will not be included in the initial v0.5.0 release and will have varying degrees of priority for subsequent releases (or possibly not at all).

* Multisig wallet descriptor QR scan(?) and addr verification(?)
* Sign taproot txs
* Multi-language support (Transifex free for open source projects)
* Multisig: sign PSBT with multiple keys at once.
* Custom OS, possibly with swappable SD card PSBT and multisig wallet descriptor storage
* Decoy game mode at launch (Snake, Tetris, Sudoku...?)
* BIP-39 wordlists in additional languages
* Address message signing
* UI color scheme customization
* Specify missing entropy for 12th/24th word calc


# v0.6 and Beyond...?
* Alternate hardware profile / touchscreen
* PGP signer
* Liquid?
