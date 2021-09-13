# Using provided OS image file

If you want to avoid the long process of installation, you should at least validate you are downloading the official image. You will need gpg installed.

1. Save the public key file [seedsigner_pubkey.gpg](https://raw.githubusercontent.com/seedsigner/seedsigner/main/seedsigner_pubkey.gpg) as seedsigner_pubkey.gpg
2. Import the public key
```
gpg --import seedsigner_pubkey.gpg
```
3. Download the latest release of the image at the [releases page](https://github.com/SeedSigner/seedsigner/releases). It will look something like seedsigner_x_x_x.img.zip
4. Download the related gpg file in the same folder. It will look like seedsigner_x_x_x.img.zip.txt.gpg
5. Verify the downloaded file with the command (adjust the file name to the file you just downloaded):
```
 gpg --verify seedsigner_x_x_x.img.zip.txt.gpg
```
6. You can trust the file if the output of the previous command has a message like:
```
Good signature from "seedsigner <btc.hardware.solutions@gmail.com>"
```
7. If everything went ok you can unzip the file and use your preferred software to burn a MicroSD with the image extracted.
