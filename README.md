# Build an offline, airgapped Bitcoin signing device for less than $50!

![Image of SeedSigners in Open Pill Enclosures](docs/img/Open_Pill_Star.JPG)![Image of SeedSigner in an Orange Pill enclosure](docs/img/Orange_Pill.JPG)

---------------

* [Project Summary](#project-summary)
* [Shopping List](#shopping-list)
* [Software Installation](#software-installation)
  * [Verifying the Software](#verifying-the-software)
* [Enclosure Designs](#enclosure-designs)
* [SeedQR Printable Templates](#seedqr-printable-templates)
* [Manual Installation Instructions](#manual-installation-instructions)


---------------

# Project Summary

The goal of SeedSigner is to lower the cost and complexity of Bitcoin multi-signature wallet use. To accomplish this goal, SeedSigner offers anyone the opportunity to build a verifiably air-gapped, stateless Bitcoin signing device using inexpensive, publicly available hardware components (usually < $50). SeedSigner helps users save with Bitcoin by assisting with trustless private key generation and multi-signature wallet setup, and helps users transact with Bitcoin via a secure, air-gapped QR-exchange signing model.

Additional information about the project can be found at [seedsigner.com](https://seedsigner.com).

You can follow [@SeedSigner](https://twitter.com/SeedSigner) on Twitter for the latest project news and developments.

If you have specific questions about the project, our [Telegram Group](https://t.me/joinchat/GHNuc_nhNQjLPWsS) is a great place to ask them.

### Feature Highlights:
* Calculate word 12/24 of a BIP39 seed phrase
* Create a 24-word BIP39 seed phrase with 99 dice rolls
* Create a 24-word BIP39 seed phrase by taking a digital photo 
* Temporarily store up to 3 seed phrases while device is powered
* Guided interface to manually create a SeedQR for instant input [(demo video here)](https://youtu.be/c1-PqTNx1vc)
* BIP39 passphrase / word 25 support
* Native Segwit Multisig XPUB generation w/ QR display
* Scan and parse transaction data from animated QR codes
* Sign transactions & transfer XPUB data using animated QR codes [(demo video here)](https://youtu.be/LPqvdQ2gSzs)
* Live preview during photo-to-seed and QR scanning UX
* Optimized seed word entry interface
* Support for Bitcoin Mainnet & Testnet
* Support for custom user-defined derivation paths
* On-demand receive address verification
* User-configurable QR code display density
* Responsive, event-driven user interface

### Considerations:
* Built for compatibility with Specter Desktop, Sparrow, and BlueWallet Vaults
* Device takes up to 60 seconds to boot before menu appears (be patient!)
* Always test your setup before transferring larger amounts of bitcoin (try Testnet first!)
* Taproot not quite yet supported
* Slightly rotating the screen clockwise or counter-clockwise should resolve lighting/glare issues
* If you think SeedSigner adds value to the Bitcoin ecosystem, please help us spread the word! (tweets, pics, videos, etc.)

### Planned Upcoming Improvements / Functionality:
* Single-sig and multi-sig change address verification
* Re-imagined, graphically-focused user interface
* Multi-language support
* Customized Linux live-boot OS to allow MicroSD card removal
* Other optimizations based on user feedback!

---------------

# Shopping List

To build a SeedSigner, you will need:

* Raspberry Pi Zero (preferably version 1.3 with no WiFi/Bluetooth capability, but any Raspberry Pi 2/3/4 or Zero model will work, Raspberry Pi 1 devices will require a hardware modification to the Waveshare LCD Hat, as per the [instructions here](./docs/legacy_hardware.md))
* Waveshare 1.3" 240x240 pxl LCD (correct pixel count is important, more info at https://www.waveshare.com/wiki/1.3inch_LCD_HAT)
* Pi Zero-compatible camera (tested to work with the Aokin / AuviPal 5MP 1080p with OV5647 Sensor)

Notes:
* You will need to solder the 40 GPIO pins (20 pins per row) to the Raspberry Pi Zero board. If you don't want to solder, purchase "GPIO Hammer Headers" for a solderless experience.
* Other cameras with the above sensor module should work, but may not fit in the Orange Pill enclosure
* Choose the Waveshare screen carefully; make sure to purchase the model that has a resolution of 240x240 pixels

---------------

# Software Installation

## A Special Note On Minimizing Trust
As is the nature of pre-packaged software downloads, downloading and using the prepared SeedSigner release images means implicitly placing trust in the individual preparing those images; in our project the release images are prepared and signed by the eponymous creator of the project, SeedSigner "the person". That individual is additionally the only person in possession of the PGP keys that are used to sign the release images.

However, one of the many advantages of the open source software model is that the need for this kind of trust can be negated by our users' ability to (1) review the project's source code and (2) assemble the operating image necessary to use the software themselves. From our project's inception, instructions to build a SeedSigner operating image (using precisely the same process that is used to create the prepared release images) have been made availabile. We have put a lot of thought and work into making these instructions easy to understand and follow, even for less technical users. These instructions can be found [here](docs/manual_installation.md).

## Downloading the Software

To download the most recent software version, click here [here](https://github.com/SeedSigner/seedsigner/releases), and then expand the *Assets* sub-heading. 
Download these files to your computer.
1. seedsigner_0_5_x.img.zip 
2. seedsigner_0_5_x.img.zip.sha256 
3. seedsigner_0_5_x.img.zip.sha256.sig 

After the files have finished downloading, follow the steps below to write the software onto a MicroSD card. Then insert the MicroSD into your assembled hardware and turn on the power. Wait about 45 secs for our logo to appear.

**Note:** The version numbers of the latest files will be higher than this example, but the naming format will be the same.  


## Verifying that the downloaded files are authentic (optional but recommended!)
You can quickly verify that the downloaded software is both genuine and unaltered, by following these instructions.

This step assumes you are running the commands from a computer where both [GPG](https://gnupg.org/download/index.html) and [shasum](https://command-not-found.com/shasum) are already installed, and that you know [how to navigate on a terminal](https://terminalcheatsheet.com/guides/navigate-terminal) 
Begin in the same folder where you have saved the download files.   
(Which will most likely be your Downloads folder.)


###Import the public key of the SeedSigner Project into your computer
The *fetch-keys*  command below will import the SeedSigner projects public key from a popular online keyserver called *Keybase.io*, into your computers *keychain*. 
The Keybase.io website service allows you to verify that the key belongs to the organization it claims to represent. It is checked cryptographically and saved in 3 separate online locations (Twitter, Seedsigner.com and github.com) 

If you need more information, open the website <a href="https://www.Keybase.io/SeedSigner" target="_blank">KeyBase.io/SeedSigner</a> (it opens in a separate tab or window) 

else simply run this command (inside the same folder as the downloaded files):
```
gpg --fetch-keys https://keybase.io/SeedSigner/pgp_keys.asc
```
When  the command completes successfully, it will display a numeric ID, as circled in red in the example below. We will use that numeric ID in the next step.

![SS - Keybase PubKey import with Fingerprint shown (New import or update of the key)](https://user-images.githubusercontent.com/91296549/174248861-7961c038-1fbf-47a1-a110-146cb218b1c8.jpg)  

###Verifying that your signature file is signed by the right person(s) 
 
The next steps will allow you how to confirm that your downloaded .zip file is the genuine and unaltered SeedSigner software.

The *verify* command below, identifies *who exactly* made the signature file. 
The output of this verify command is the all-important *signers* fingerprint, and it is this fingerprint that you will visually (and match!) to the fingerprint ID shown at Keybase.io/SeedSigner.  If the ID matches, then you know it was seedsigner who signed it.  

(More specifically, the verify command determines *which* key pair already on your computer, signed the sha256.sig file.  It does this comparing the file  cryptographically to its unsigned equivalent (the .sha256 file).)  

```
gpg --verify seedsigner_0_*_*.img.zip.sha256.sig
```
**Note:** The `*`s in the command will auto-match to the version number in your current folder. It should be copied and pasted as-is.

The response you receive **must** include the phrase **"Good signature"**, like this: 

>Good signature from "seedsigner <btc.hardware.solutions @ gmail.com>" [unknown]  

The email address is JUST informational. Completely ignore it.  *Only* the matching fingerprints count.   
<br>
If the response displays "BAD signature", then you must stop here immediately. Do not continue. Contact us for assistance at the Telegram address above.

If you receive the warning message below, it can be safely ignored *because* you are going to be matching the fingerprint ID manually, to Keybase.io/seedsigner.

> gpg: WARNING: This key is not certified with a trusted signature!  
> gpg:          There is no indication that the signature belongs to the owner.


If you received the phase **"good Signature"**, then the last output line will display a fingerprint ID. That is the all-important *signers* fingerprint ID. you must now visually compare that ID to the fingerprint ID shown at Keybase.io/SeedSigner.  If the fingerprint ID matches, then you have successfully verified that seedsigner signed the software you have just downloaded.
<br>
If it does not match perfectly, then you must stop here immediately. Do not continue. Contact us for assistance at the Telegram address above.
<br>
<br>

The final verification step is to make sure that the other downloaded files (eg the files inside the zip file) were not altered or added to in any way. Even a single character being changed or removed, would show up here.   

**On Linux or OSX**
```
shasum -a 256 -c seedsigner_0_*_*.img.zip.sha256
```

**On Windows (Powershell)**
```
CertUtil -hashfile  seedsigner_0_*_*.img.zip SHA256 | findstr /v "hash"
```

The response must include the text **seedsigner_[VersionNumber].img.zip OK**, like this:   
```
seedsigner_0_5_x.img.zip: OK
```
**If you have received the OK message above then your verification has suceeded! - well done, the download files are now all confirmed as authentic and unaltered**!   

If the result did not display "OK", then you must stop here immediately. Do not continue. Contact us for assistance at the Telegram address above.

Please recognize that this process can only validate the software to the extent that the entity that first published the key is an honest actor, and their private key is not compromised or somehow being used by a malicious actor. 
---------------

# Enclosure Designs

### Open Pill

The Open Pill enclosure design is all about quick, simple and inexpensive depoloyment of a SeedSigner device. The design does not require any additional hardware and can be printed using a standard FDM 3D printer in about 2 hours, no supports necessary. A video demonstrating the assembly process can be found [here](https://youtu.be/gXPFJygZobEa). To access the design file and printable model, click [here](https://github.com/SeedSigner/seedsigner/tree/main/enclosures/open_pill).

### Orange Pill

The Orange Pill enclosure design offers a more finished look that includes button covers and a joystick topper. You'll also need the following additional hardware to assemble it:

* 4 x F-F M2.5 spacers, 10mm length
* 4 x M2.5 pan head screws, 6mm length
* 4 x M2.5 pan head screws, 12mm length

The upper and lower portions of the enclosure can be printed using a standard FDM 3D printer, no supports necessary. The buttons and joystick nub should ideally be produced with a SLA/resin printer. An overview of the entire assembly process can be found [here](https://youtu.be/aIIc2DiZYcI). To access the design files and printable models, click [here](https://github.com/SeedSigner/seedsigner/tree/main/enclosures/orange_pill).

### Community Designs

* [Lil Pill](https://cults3d.com/en/3d-model/gadget/lil-pill-seedsigner-case) by @_CyberNomad
* [OrangeSurf Case](https://github.com/orangesurf/orangesurf-seedsigner-case) by @OrangeSurfBTC
* [PS4 Seedsigner](https://www.thingiverse.com/thing:5363525) by @Silexperience
* [OpenPill Faceplate](https://www.printables.com/en/model/179924-seedsigner-open-pill-cover-plates-digital-cross-jo) by @Revetuzo 
* [Waveshare CoverPlate](https://cults3d.com/en/3d-model/various/seedsigner-coverplate-for-waveshare-1-3-inch-lcd-hat-with-240x240-pixel-display) by @Adathome1

---------------

# SeedQR Printable Templates
You can use SeedSigner to export your seed to a hand-transcribed SeedQR format that enables you to instantly load your seed back into SeedSigner.

[More information about SeedQRs](docs/seed_qr/README.md)

<table align="center">
    <tr><td><img src="docs/seed_qr/img/handmade_qr.jpg"></td></tr>
</table>

Standard SeedQR templates:
* [12-word SeedQR template (25x25)](docs/seed_qr/printable_templates/12words_seedqr_template.pdf)
* [24-word SeedQR template (29x29)](docs/seed_qr/printable_templates/24words_seedqr_template.pdf)
* [Baseball card template: 24-word SeedQR (29x29)](docs/seed_qr/printable_templates/Seed_QR_Card.pdf)

CompactSeedQR templates:
* [12-word CompactSeedQR template (21x21)](docs/seed_qr/printable_templates/compact_seedqr/12words_compactseedqr_template.pdf)
* [24-word CompactSeedQR template (25x25)](docs/seed_qr/printable_templates/compact_seedqr/24words_compactseedqr_template.pdf)

_note: CompactSeedQR is an advanced feature that can be enabled in Settings_

---------------

# Manual Installation Instructions
see the docs: [Manual Installation Instructions](docs/manual_installation.md)
