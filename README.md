Hello World!

Build your own offline, airgapped Bitcoin transaction signing device for less than $35! Also generate seed word 24 or generate a seed phrase from dice rolls!

![Image of SeedSigner in an Orange Pill enclosure](https://github.com/SeedSigner/seedsigner/blob/main/Orange_Pill.JPG)

The code is designed to ultimately be run on a Raspberry Pi Zero (version 1.3 with no wireless capability) with a Waveshare 1.3" 240x240 pxl LCD (more info at https://www.waveshare.com/wiki/1.3inch_LCD_HAT) and a Pi Zero-conpatible camera (tested to work with the Aokin 5MP 1080p with OV5647 Sensor Video Camera Module; other brands with that sensor module may work as well).

The easiest way to get the signer up and running is to downloaded the "seedsigner_0_1_0.zip" file in the current release, extract the "seedsigner_0_1_0.img" file, and write it to a MicroSD card (at least 4GB in size or larger). Then install the MicroSD in the assembled hardware and off you go.

Newest Added Features:
* Native Segwit Multisig Xpub generation w/ QR display
* Scan and Parse transaction data from animated QR codes
* Sign transactions & transfer xpub data using animated QR codes
* New extensible menu system
* Improved letter entry responsiveness
* Various UX improvements
* Various code optimizations
* Project donation information
* ORANGE text! (looks great with orange pill enclosure!)

Considerations:
* Built to be compatible with Specter-desktop Bitcoin wallet
* Be patient, it takes a couple of minutes for the menu to come up after applying power to the Pi Zero (when you see the "static" you're almost there!)
* Confirmed bug: a "bad" seed phrase that fails checksum validation will crash the app and you will need to restart the Pi
* For now, ALWAYS opt to use animated QR codes in Specter-desktop
* Mainnet is only option; test with SMALL AMOUNTS of bitcoin
* Currently ONLY generating Native Segwit Multisig Xpubs
* Scanning animated QRs into a PC is tricky, be aware of ambient light, glare and focus
* (Holding the screen upside-down significantly reduces glare for some reason)
* Display text is small; comes with 240x240 territory but ever trying to optimize
* Check out our "seedsigner" telegram community for community help / feedback: (https://t.me/joinchat/GHNuc_nhNQjLPWsS)
* If you think SeedSigner adds value to the Bitcoin ecosystem, please help me spread the word! (tweets, pics, videos, etc.)

Coming Improvements/Functionality:
* Add support for single QR codes
* Support for 12 word seeds
* Reduce signed xpub data to decrease required QR images
* Support for single signature Xpub key generation
* Select from different display colors
* Generate seed from internal entropy (maybe)
* Other optimizations based on user feedback!

The software can also be installed using an internet-connected Raspberry Pi 2/3/4 or Zero W are as follows:

Install the Raspberry Pi Lite operating system (https://www.raspberrypi.org/software/operating-systems/) on a MicroSD card and install the card in a Raspberry Pi 2/3/4 or Zero W.

Connect a keyboard & monitor, or SSH into the Pi if you're familiar with that process.

* `sudo raspi-config`

(set your localization options, configure WiFi if necessary, but most important: navigate to the "interface options" and enable the "SPI" interface; also make sure to enable the camera interface in raspi-config)

Reboot when prompted within the raspi-config interface

Install these dependencies:
* `sudo apt-get update`
* `sudo apt-get install wiringpi`
* `sudo apt-get install python3-pip`
* `sudo apt-get install python3-numpy`
* `sudo apt-get install python3-venv`
* `sudo apt-get install python-pil`
* `sudo apt-get install libopenjp2-7`
* `sudo apt-get install ttf-mscorefonts-installer`
* `sudo apt-get install git`
* `sudo apt-get install libatlas-base-dev`
* `sudo apt-get install python3-opencv`
* `sudo apt-get install libzbar0`
* `sudo apt-get install python3-picamera`

Install this:
* `wget http://www.airspayce.com/mikem/bcm2835/bcm2835-1.60.tar.gz`
* `tar zxvf bcm2835-1.60.tar.gz`
* `cd bcm2835-1.60/`
* `sudo ./configure`
* `sudo make && sudo make check && sudo make install`
* `cd ..`

Create Python Environment
* `python3 -m venv env`

Enter Python Environment
* `source env/bin/activate`

Install these python dependencies:
* `sudo pip3 install --verbose spidev`
* `sudo pip3 install --verbose RPi.GPIO`
* `sudo pip3 install --verbose pillow`
* `sudo pip3 install --verbose embit`
* `sudo pip3 install --verbose qrcode`
* `sudo pip3 install --verbose imutils`
* `sudo pip3 install --verbose pyzbar`
* `sudo pip3 install --verbose argparse`
* `sudo pip3 install --verbose imutils`
* `pip3 install --vebose numpy`


Download SeedSigner
* `git clone https://github.com/SeedSigner/seedsigner`

Download WordLists to seedsigner directory

* `cd seedsigner/wordlists`
* `wget https://raw.githubusercontent.com/bitcoin/bips/master/bip-0039/english.txt`
* `wget https://raw.githubusercontent.com/bitcoin/bips/master/bip-0039/french.txt`
* `cd ..`

Other Wordlists Available Here: [Wordlists](https://github.com/bitcoin/bips/tree/master/bip-0039)

Modify the system config to run SeedSigner at boot:
* `sudo nano /etc/rc.local`

add these lines
to enter python environment
* `export VIRTUAL_ENV=/home/pi/env`
* `export PATH="$VIRTUAL_ENV/bin:$PATH"`
run seedsigner and redirect output
* `nohup python3 /home/pi/main.py > /dev/null &`

to the line above `exit 0`

Use Control + O, then [enter], to write the file.
Then use Control + X, to exit the program.

To reboot and try out the program... remember the device is still online!
* `sudo reboot`

(Optional) Modify the system swap configuration to disable virtual memory:
* `sudo nano /etc/dphys-swapfile`
add `CONF_SWAPSIZE=100` to `CONF_SWAPSIZE=0`

Use Control + O, then [enter], to write the file.
Then use Control + X, to exit the program.

To shut down the pi:
* `sudo shutdown --poweroff now`

Now either move the MicroSD card to a Pi Zero 1.3 with the 1.3-inch LCD Hat and camera installed, or the LCD Hat will also run fine on a Raspberry Pi 2/3/4 or Zero W; just remember to disable networking if you want to run the software in isolation.

It will take a couple of minutes after the Pi is powered on for the GUI to launch -- be patient!
