# Build an offline, airgapped Bitcoin signing device for less than $50!

![Image of SeedSigners in Open Pill Enclosures](docs/img/Open_Pill_Star.JPG)![Image of SeedSigner in an Orange Pill enclosure](docs/img/Orange_Pill.JPG)

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
* Built for compatibility with Specter-desktop, Sparrow and BlueWallet Vaults
* Device takes up to 60 seconds to boot before menu appears (be patient!)
* Always test your setup before transfering larger amounts of bitcoin (try testnet first!)
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

* Raspberry Pi Zero (preferably version 1.3 with no WiFi/Bluetooth capability, but any Raspberry Pi 2/3/4 or Zero model will work)
* Waveshare 1.3" 240x240 pxl LCD (correct pixel count is important, more info at https://www.waveshare.com/wiki/1.3inch_LCD_HAT)
* Pi Zero-compatible camera (tested to work with the Aokin / AuviPal 5MP 1080p with OV5647 Sensor)

Notes:
* You will need to solder the 40 GPIO pins (20 pins per row) to the Raspberry Pi Zero board. If you don't want to solder, purchase "GPIO Hammer Headers" for a solderless experience.
* Other cameras with the above sensor module should work, but may not fit in the Orange Pill enclosure
* Choose the Waveshare screen carefully; make sure to purchase the model that has a resolution of 240x240 pixels

---------------

# Important Note on Software Installation

The quickest and easiest way to install the software is to download the most recent "seedsigner_X_X_X.zip" file in the [software releases](https://github.com/SeedSigner/seedsigner/releases) section of this repository. After downloading the .zip file, extract the seedsigner .img file, and write it to a MicroSD card (at least 4GB in size or larger). Then install the MicroSD in the assembled hardware and off you go. If your goal is a more trustless installation, you can follow the manual software installation instructions below.

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

# Manual Software Installation Instructions:

Begin by acquiring a specific copy of the Raspberry Pi Lite operating system, dated 2021-05-28; this version can be found here:

https://downloads.raspberrypi.org/raspios_lite_armhf/images/raspios_lite_armhf-2021-05-28/

Best practice is to verify the downloaded .zip file containing the Raspberry Pi Lite OS matches the published SHA256 hash of the file; for additional reference that hash is: c5dad159a2775c687e9281b1a0e586f7471690ae28f2f2282c90e7d59f64273c. After verifying the file's data integrity, you can decompress the .zip file to obtain the operating system image that it contains. You can then use Balena's Etcher tool (https://www.balena.io/etcher/) to write the Raspberry Pi Lite software image to a memory card (4 GB or larger). It's important to note that an image authoring tool must be used (the operating system image cannot be simply copied into a file storage partition on the memory card).

The manual SeedSigner installation and configuration process requires an internet connection on the device to download the necessary libraries and code. But because the Pi Zero 1.3 does not have onboard wifi, you have two options:

1. Run these steps on a separate Raspberry Pi 2/3/4 or Zero W which can connect to the internet and then transfer the SD card to the Pi Zero 1.3 when complete.
2. OR configure the Pi Zero 1.3 directly by relaying through your computer's internet connection over USB. See instructions [here](docs/usb_relay.md).

For the following steps you'll need to either connect a keyboard & monitor to the network-connected Raspberry Pi you are working with, or SSH into the Pi if you're familiar with that process.

### Configure the Pi

First things first, verify that you are using the correct version of the Raspberry Pi Lite operating system by typing the command:
```
cat /etc/os-release
```
The output of this command should match the following text:
```
PRETTY_NAME="Raspbian GNU/Linux 10 (buster)"
NAME="Raspbian GNU/Linux"
VERSION_ID="10"
VERSION="10 (buster)"
VERSION_CODENAME=buster
ID=raspbian
ID_LIKE=debian
HOME_URL="http://www.raspbian.org/"
SUPPORT_URL="http://www.raspbian.org/RaspbianForums"
BUG_REPORT_URL="http://www.raspbian.org/RaspbianBugs"
```

Now launch the Raspberry Pi's System Configuration tool using the command:
```
sudo raspi-config
```

Set the following:
* `Interface Options`:
    * `Camera`: enable
    * `SPI`: enable
* `Localisation Options`:
    * `Locale`: arrow up and down through the list and select or deselect languages with the spacebar.
        * Deselect the default language option that is selected
        * Select `en_US.UTF-8 UTF-8` for US English
* You will also need to configure the WiFi settings if you are using the #1 option above to connect to the internet

When you exit the System Configuration tool, you will be prompted to reboot the system; allow the system to reboot and continue with these instructions.

Install these dependencies (you can use this entire text string to install them all at once):
```
sudo apt-get update && sudo apt-get install -y wiringpi python3-pip python3-numpy python-pil libopenjp2-7 git python3-opencv libzbar0 python3-picamera libatlas-base-dev qrencode
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

Install the "virtualenvwrapper" tool:
```
pip3 install virtualenvwrapper
```

Edit your bash profile with the command `nano ~/.profile` and add the following to the end:
```
export WORKON_HOME=$HOME/.envs
export VIRTUALENVWRAPPER_PYTHON=/usr/bin/python3
source /home/pi/.local/bin/virtualenvwrapper.sh
```
Then `CTRL-X` and `y` to exit and save changes.

Now create the python virtualenv for SeedSigner with these two commands:
```
source ~/.profile
mkvirtualenv --python=python3 seedsigner-env
```

Now download the SeedSigner code:
```
git clone https://github.com/SeedSigner/seedsigner
```

Install the necessary Python dependencies:
```
cd seedsigner
pip3 install -r requirements.txt
cd ..
```

Modify the systemd to run SeedSigner at boot:
```
sudo nano /etc/systemd/system/seedsigner.service
```

Add the following contents to the text file that was created:
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

Use `CTRL-X` and `y` to exit and save changes.

Run `sudo systemctl enable seedsigner.service` to enable service on boot. (This will restart the seedsigner code automatically at startup and if it crashes.)

Now reboot the Raspberry Pi with the command:
```
sudo reboot
```

After the Raspberry Pi reboots, you should see the SeedSigner splash screen and the SeedSigner menu subsequently appear on the LCD screen (note that it can take up to 60 seconds for the menu to appear).

Next, disable and remove the system's virtual memory / swap file with the commands:
```
sudo apt remove dphys-swapfile
sudo rm /var/swap
```

For those who will use the SeedSigner installation for testing/development, it can be helpful to change the system's host name so it doesn't potentially conflict with other Raspberry Pi's that may already be present on your network. (For those who don't plan to use the installation for testing or development, you can skip this portion of the process.) To change the host name first edit the "hostname" with the command:
```
sudo nano /etc/hostname
```
and change "raspberrypi" to "seedsigner" (or another name). Use `CTRL-X` and `y` to exit and save changes. You'll also need to edit the "hosts" file with the command:
```
sudo nano /etc/hosts
```
and change "raspberrypi" to "seedsigner" (or the other name you previously chose). Use `CTRL-X` and `y` to exit and save changes.

It's also a good idea to change the system's password from the default "raspberry". Do do this, use the command:
```
passwd
```
You will be prompted to enter the current password (raspberry) and then to enter a new password twice. In our prepared release image, the password used is "AirG@pped!" (without quotes).

If you plan to use your installation on a Raspberry Pi that is not a Zero version 1.3, but rather on a Raspberry Pi that has WiFi and Bluetooth capabilities, it is a good idea to disable the following WiFi & Bluetooth, as well as other relevant services (assuming you are not creating this installation for testing/development purposes). Enter the followiing commands to disable WiFi, Bluetooth, & other relevant services:
```
sudo systemctl disable bluetooth.service
sudo systemctl disable wpa_supplicant.service
sudo systemctl disable dhcpcd.service
sudo systemctl disable sshd.service
sudo systemctl disable networking.service
sudo systemctl disable dphys-swapfile.service
sudo ifconfig wlan0 down
```
Please note that if you are using WiFi to connect/interact with your Raspberry Pi, the last command will sever that connection.

You can now safely power the Raspberry Pi off from the SeedSigner main menu.

If you do not plan to use your installation for testing/development, it is also a good idea to disable WiFi and Bluetooth by editing the config.txt file found in the installation's "boot" partition. You can add the following text to the end of that file with any simple text editor (Windows: Notepad, Mac: TextEdit, Linux: nano):
```
dtoverlay=disable-bt
dtoverlay=pi3-disable-wifi
```

If you used option #2 above and don't plan to continue to access your SeedSigner via SSH over USB, it is a good idea to reverse the steps you took to enable it -- those instructions can be found near the end of [this guide](docs/usb_relay.md).

Please remember that it can take up to a minute for the GUI to appear when subsequently powering your SeedSigner on.

### Optional: Run the tests
see: [tests/README.md](tests/README.md)
