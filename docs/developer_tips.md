# Developer Tips

### Quickly generate a new seed to test with
Generate a new 12- or 24-word seed via [https://iancoleman.io/bip39/](https://iancoleman.io/bip39/).

Access a `python3` environment that has the `embit` library installed (e.g. your own local machine, ssh into the SeedSigner, etc)

Start a python REPL session by just typing: `python3`

Paste in the following but insert your newly generated mnemonic:
```
from embit import bip39
seed_phrase = "smoke chimney announce candy glory tongue refuse fatigue cricket once consider beef treat urge wing deny gym robot tobacco adult problem priority wheat diagram"
data = ""
for word in seed_phrase.split(" "):
    index = bip39.WORDLIST.index(word)
    data += "%04d" % index

print(data)
```

For the seed in the snippet, you should see:
```
163803200074026607961827144306700411123603780160185419152013046908321497181700301371136719990487
```

Take the output and paste it into a [QR code generator](https://www.the-qrcode-generator.com/).

Start up SeedSigner's UI to import a seed from a QR code. Scan the new QR code and you're good to go!


# Advanced developer notes

## Backup an SD card

You can back up and restore any size SD card but the process is a little inefficient so the bigger the source SD card, the bigger the backup will be and the longer it'll take to create (and even longer to image back to a new SD card), even if most of the card is blank.

You can restore a backup image to an SD card of the same or larger size. So it's strongly recommended to do repetitive development work on a smaller card that's easier to backup and restore. Once the image is stabilized, then write it to a bigger card, if necessary (that being said, there's really no reason to use a large SD card for SeedSigner. An 8GB SD card is more than big enough).

Insert the SD card into a Mac/Linux machine and create a compressed img file.

First verify the name of your SD card:

```
# Mac:
diskutil list

# Linux:
sudo fdisk -l
```

It will most likely be `/dev/disk1` on most systems.

Now we use `dd` to clone and `gzip` to compress it. Note that we reference the SD card by adding an `r` in front of the disk name. This speeds up the cloning considerably.

```
sudo dd if=/dev/rdisk1 conv=sparse bs=4m | gzip -9 > seedsigner.img.gz
```

The process should take about 15 minutes and will typically generate a roughly 1.1GB image.

To restore from your backup image, just use the Raspberry Pi Imager. Remember that you can only write it to an SD card of equal or greater size than the original SD card.
