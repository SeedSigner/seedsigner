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

To download the most recent software version, click [here](https://github.com/SeedSigner/seedsigner/releases), and then expand the *Assets* sub-heading. 
Download these files to your computer:
1. seedsigner_0_5_x.img.zip 
2. seedsigner_0_5_x.img.zip.sha256 
3. seedsigner_0_5_x.img.zip.sha256.sig 

Once the files have all finished downloading, follow the steps below to verify, and to write the software onto a MicroSD card. Then insert the MicroSD into your assembled hardware and turn on the USB power. Allow about 45 seconds for our logo to appear, and then you can begin using your Seedsigner! 

**Note:** The version numbers of the latest files will be higher than this example, but the naming format will be the same.  


## Verifying that the downloaded files are authentic (optional but highly recommended!)

You can quickly verify that the downloaded software is both authentic and unaltered, by following these instructions.

These next steps assume you are running the commands from a computer where both [GPG](https://gnupg.org/download/index.html) and [shasum](https://command-not-found.com/shasum) are already installed, and that you also know [how to navigate on a terminal](https://terminalcheatsheet.com/guides/navigate-terminal). 


### 1. Import the public key of the SeedSigner project into your computer:

Run the *fetch-keys* command to import the SeedSigner projects public key from the popular online keyserver called *Keybase.io*, into your computers *keychain*.  


```
gpg --fetch-keys https://keybase.io/SeedSigner/pgp_keys.asc
```
When the command completes successfully, it should display  that a key was either imported or updated.  Ignore any email address shown.

![SS - Keybase PubKey import with Fingerprint shown (New import or update of the key)](https://user-images.githubusercontent.com/91296549/174248861-7961c038-1fbf-47a1-a110-146cb218b1c8.jpg)  

<details><summary>Learn more about how keybase.io helps you check that someone is who they say they are</summary>
<p>
Keybase.io allows you to independently verify that the public key saved on Keybase.io, is both authentic and that it belongs to the organization it claims to represent.  
 Keybase has already checked the three pubkey files cryptographically when they were saved.  However, if you  like, you can further verify the Key publications, either :  
 
 - *via Keybase*: By clicking on any of the three blue badges at [Keybase.io/seedsigner](www.keybase.io/seedsigner) to see what was published there. (The blue badge for the publication on Twitter is in the most human-readable form and it is also bi-directional), or, 
 - *without keybase*: By using these 3 links directly: [Twitter](https://twitter.com/seedsigner/status/1530555252373704707) , [Github](https://gist.github.com/SeedSigner/5936fa1219b07e28a3672385b605b5d2) and [Seedsigner.com](https://seedsigner.com/keybase.txt). This method can be used if you would like to make an even deeper, independent inspection without relying on Keybase at all, or if the Keybase.io site is no longer valid or it is removed entirely. 

Once you have used one of these methods, you will know if  the Public Key stored on Keybase, is genuinely from the SeedSinger Project or not.
</p>
</details>


<BR>

 
### 2. Checking that the *signature file* is genuinely from the SeedSigner Project:
 
Running this *verify* command, will determine *who* created the signature file (.sig) you downloaded already.
The output will display the all-important *signers* fingerprint, and it is this fingerprint ID which you will want to match to keybase, by yourself.  

```
gpg --verify seedsigner_0_*_*.img.zip.sha256.sig
```
**Note:** *Verify* must be run from inside the *same folder* that you downloaded the files into. The `*`'s in the command will auto-fill the version from your current folder, so it should be copied and pasted as-is.

When the command completes successfully, it should look like this:
<BR>
![SS - Verify Command - GPG on Linux - Masked_v3-80pct](https://user-images.githubusercontent.com/91296549/215339119-5326e814-1d60-47bb-980c-1498a2f30baf.jpg)
It must display "**Good** signature". Ignore any email addresses. *Only*  matching fingerprints count here.  Stop here immediately if it displays "*Bad signature*"!
<BR> 
On the *last* output line, look at the *rightmost* 16 characters (circled in red in the picture above). That is *who* made the signature file (.sig).   
<details><summary> About the warning message:</summary>
<p>  Since you are going to now match the outputted fingerprint ID against the source proofs at Keybase.io/seedsigner, you can ignore this warning message:

```
> WARNING: This key is not certified with a trusted signature!  
> There is no indication that the signature belongs to the owner.
 ```
</p>
</details>
<br>

Now open the website [Keybase.io/seedsigner](www.keybase.io/seedsigner) and compare the 16 character fingerprint ID (circled red in the screenshot below),   to the *rightmost* 16 characters from your *verify* command. **Make sure that they match exactly**.  
<BR>
![SS - Keybase Website PubKey visual matching1_Cropped-80pct](https://user-images.githubusercontent.com/91296549/215326193-97c84e35-5570-4e52-bf3f-e86d367c8908.jpg)



If the two fingerprint ID's match exactly, then you have successfully confirmed that your .sig file is authentic!
<BR>
If they do ***not match exactly***, or your verify command displayed "Bad signature", then you must stop here immediately. Do not continue. Contact us for assistance in the Telegram group address above.
<br>

<details><summary>Learn more about signature file verification</summary>
<p>

More specifically, the verify command determines *which* key pair of those already installed on your computer, actually signed the sha256.sig file.  It does this by  cryptographically comparing the sha256.sig file to its unsigned equivalent (the .sha256 file), while looping through the public keys already imported into your computer. Whomever's pre-imported Pubkey is able to perform the comparison successfully, is the Pubkey of the keypair used in the signing process. That 'winning' Public key must match the Public Key we have previously found, and verified as  genuine on keybase.io.

</p>
</details>

<br>

### 3. Verifying that the *software files* are genuine

Running the *shasum* command, is the final verification step and will confirm (via file hashing) that the software code (ie the binary files inside the zip file), were not altered, or added to, since publication or during your download. (Not by even one single character!)

 **On Linux or OSX:** Run this command
```
shasum -a 256 -c seedsigner_0_*_*.img.zip.sha256
```

**On Windows (inside Powershell):** Run this command
```
CertUtil -hashfile  seedsigner_0_*_*.img.zip SHA256 | findstr /v "hash"
```

Wait about 30 seconds for the command to complete   
```
seedsigner_0_5_x.img.zip: OK
shasum: WARNING: 4 Lines are improperly formatted
```
**If you receive the "OK" message** for the **seedsigner_[VersionNumber].img.zip file**, as shown above, then your verification is fully complete!  
**All of your downloaded files have now been confirmed as both authentic and unaltered!** 😄😄 !!     

The warning message describing '4 lines being improperly formatted' can be safely ignored. 
If your file result shows "FAILED", then you must stop here immediately. Do not continue. Contact us for assistance at  the Telegram group address above.


Please recognize that this process can only validate the software to the extent that the entity that first published the key is an honest actor, and their private key is not compromised or somehow being used by a malicious actor.
<BR>


## Writing the software to your MicroSD card
  Insert more instructions here. 
  (to be done by MarcG)

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
