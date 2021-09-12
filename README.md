# Build an offline, airgapped Bitcoin signing device for less than $50!

![Image of SeedSigners in Open Pill Enclosures](docs/img/Open_Pill_Star.JPG)![Image of SeedSigner in an Orange Pill enclosure](docs/img/Orange_Pill.JPG)

---------------

# Project Summary

The goal of SeedSigner is to lower the cost and complexity of Bitcoin multi-signature wallet use. To accomplish this goal, SeedSigner offers anyone the opportunity to build a verifiably air-gapped Bitcoin signing device using inexpensive, publicly available hardware components (usually < $50). SeedSigner helps users save with bitcoin by assisting with trustless private key generation and multi-signature wallet setup, and helps users transact with bitcoin via a secure, air-gapped QR-exchange signing model.

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
* User-configurable QR code display density
* Responsive, event-driven user interface

### Considerations:
* Built for compatibility with Specter-desktop, Sparrow and BlueWallet Vaults
* Device takes ~45 seconds to boot before menu appears (be patient!)
* Always test your setup before transfering larger amounts of bitcoin (try testnet first!)
* Currently ONLY generating Native Segwit Single-sig & Multi-sig XPUBs
* Slightly rotating the screen clockwise or counter-clockwise should resolve lighting/glare issues
* If you think SeedSigner adds value to the Bitcoin ecosystem, please help us spread the word! (tweets, pics, videos, etc.)

### Planned Upcoming Improvements / Functionality:
* Support for custom user-defined derivation paths
* Single-sig and multi-sig address verification
* Re-imagined, graphically-focused user interface
* Multi-language support
* Customized Linux live-boot OS to allow MicroSD card removal
* Other optimizations based on user feedback!

---------------

# Shopping List

To build a SeedSigner, you will need:

* Raspberry Pi Zero (version 1.3 with no WiFi/Bluetooth capability)
* Waveshare 1.3" 240x240 pxl LCD (more info at https://www.waveshare.com/wiki/1.3inch_LCD_HAT)
* Pi Zero-compatible camera (tested to work with the Aokin / AuviPal 5MP 1080p with OV5647 Sensor)

Notes:
* You will need to solder the 40 GPIO pins (20 pins per row) to the Raspberry Pi Zero board. If you don't want to solder, purchase "GPIO Hammer Headers" for a solderless experience.
* Other cameras with the above sensor module should work, but may not fit in the Orange Pill enclosure
* Choose the Waveshare screen carefully; make sure to purchase the model that has a resolution of 240x240 pixels

---------------

# Important Note on Software Installation

The quickest and easiest way to install the software is to download the most recent "seedsigner_X_X_X.zip" file in the [software releases](https://github.com/SeedSigner/seedsigner/releases) section of this repository. After downloading the .zip file, extract the seedsigner .img file, and write it to a MicroSD card (at least 4GB in size or larger). Then install the MicroSD in the assembled hardware and off you go. If your goal is a more trustless installation, you can follow the manual build instructions below.

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

---------------

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
7. If everything went ok you can unzip the file and use your prefered software to burn a MicroSD with the image extracted.

---------------

# Manual Software Installation Instructions:
Begin by preparing a copy of the Raspberry Pi Lite operating system (https://www.raspberrypi.org/software/operating-systems/) on a MicroSD card. Their [Raspberry Pi Imager](https://www.raspberrypi.org/software/) tool makes this easy.

SeedSigner installation and configuration requires an internet connection on the device to download the necessary libraries and code. But because the Pi Zero 1.3 does not have onboard wifi, you have two options:

1. Run these steps on a separate Raspberry Pi 2/3/4 or Zero W which can connect to the internet and then transfer the SD card to the Pi Zero 1.3 when complete.
2. OR configure the Pi Zero 1.3 directly by relaying through your computer's internet connection over USB. See instructions [here](docs/usb_relay.md).

Connect a keyboard & monitor to the device or SSH into the Pi if you're familiar with that process.

### Configure the Pi
On the Pi bring up its system config:
```
sudo raspi-config
```

Set the following:
* `Interface Options`:
    * `Camera`: enable
    * `SPI`: enable
* `Localisation Options`:
    * `Locale`: arrow up and down through the list and select or deselect languages with the spacebar.
        * `en_US.UTF-8 UTF-8` for US English
* WiFi settings (only necessary for the option #1 setup above)

Exit and reboot when prompted within the raspi-config interface.

Install these dependencies:
```
sudo apt-get update && sudo apt-get install -y wiringpi python3-pip python3-numpy python-pil libopenjp2-7 ttf-mscorefonts-installer git python3-opencv libzbar0 python3-picamera libatlas-base-dev qrencode
```

Install the [C library for Broadcom BCM 2835](http://www.airspayce.com/mikem/bcm2835/):
```
wget http://www.airspayce.com/mikem/bcm2835/bcm2835-1.60.tar.gz
tar zxvf bcm2835-1.60.tar.gz
cd bcm2835-1.60/
sudo ./configure
sudo make && sudo make check && sudo make install
cd ..
rm bcm2835-1.60.tar.gz
```

Set up virtualenv
```
pip3 install virtualenvwrapper
```

Edit your bash profile with `nano ~/.profile` and add the following to the end:
```
export WORKON_HOME=$HOME/.envs
export VIRTUALENVWRAPPER_PYTHON=/usr/bin/python3
source /home/pi/.local/bin/virtualenvwrapper.sh
```
Then `CTRL-X` and `y` to exit and save changes.

Now create the python virtualenv for SeedSigner:
```
source ~/.profile
mkvirtualenv --python=python3 seedsigner-env
```

Download SeedSigner
```
git clone https://github.com/SeedSigner/seedsigner
```

Install python dependencies:
```
cd seedsigner
pip3 install -r requirements.txt
```

Modify the systemd to run SeedSigner at boot:
```
sudo nano /etc/systemd/system/seedsigner.service
```

Add the following contents to the file:
```
[Unit]
Description=Seedsigner

[Service]
User=pi
WorkingDirectory=/home/pi/seedsigner/src/
ExecStart=/home/pi/.envs/seedsigner-env/bin/python main.py
Restart=always

[Install]
WantedBy=multi-user.target
```

Use Control + O, then [enter], to write the file.
Then use Control + X, to exit the program.

Run `sudo systemctl enable seedsigner.service` to enable service on boot. (This will restart the seedsigner code automatically at startup and if it crashes.)

(Optional) Modify the system swap configuration to disable virtual memory:
```sudo nano /etc/dphys-swapfile```
Change `CONF_SWAPSIZE=100` to `CONF_SWAPSIZE=0`

Use Control + O, then [enter], to write the file.
Then use Control + X, to exit the program.

If you completed these steps on a separate Pi (option #1), shut down the pi with `sudo shutdown --poweroff now` and then transfer the SD card to the Pi Zero 1.3 (_note: the LCD Hat will also run fine on a Raspberry Pi 2/3/4 or Zero W; just remember to disable networking if you want to run the software in isolation)_.

OR if you're working directly on the Pi Zero 1.3 (option #2), just reboot it:
```
sudo reboot
```

It will take about a minute after the Pi is powered on for the GUI to launch -- be patient!

_Reminder: If you used option #2, [return the guide](docs/usb_relay.md) to remove the internet access over USB configuration._


### Run the tests
see: [tests/README.md](tests/README.md)
