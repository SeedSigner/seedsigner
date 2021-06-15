# Build an offline, airgapped Bitcoin signing device for less than $50!

![Image of SeedSigner in an Orange Pill enclosure](https://github.com/SeedSigner/seedsigner/blob/main/Orange_Pill.JPG)

---------------

## Contributors Welcome!

* Now that the overall code structure has been largely established, we welcome potential feature additions/improvements
* We are also actively seeking contributors to create walkthroughs/tutorials on building and using SeedSigner
* We are seeking a smaller group of more technical users to test new features and upcoming releases

Please contact @SeedSigner on Twitter/Telegram to inquire with any questions about contributing!

---------------

## Shopping List

To build a SeedSigner, you will need:

* Raspberry Pi Zero (version 1.3 with no wireless capability)
* Waveshare 1.3" 240x240 pxl LCD (more info at https://www.waveshare.com/wiki/1.3inch_LCD_HAT)
* Pi Zero-conpatible camera (tested to work with the Aokin / AuviPal 5MP 1080p with OV5647 Sensor)

Notes:
* Other cameras with the above sensor module should work, but may not fit in the Orange Pill enclosure
* Choose the Waveshare screen carefully; make sure to purchase the model that has a resolution of 240x240 pixels

The easiest way to install the software is to download the "seedsigner_X_X_X.zip" file in the current release, extract the seedsigner .img file, and write it to a MicroSD card (at least 4GB in size or larger). Then install the MicroSD in the assembled hardware and off you go.

---------------

## Now make your own "Orange Pill" enclosure too!

The Orange Pill enclosure design has been open-sourced! Check out the "Orange_Pill" folder in this repo. You'll need the following additional hardware to assemble it:

* 4 x F-F M2.5 spacers, 10mm length
* 4 x M2.5 pan head screws, 6mm length
* 4 x M2.5 pan head screws, 12mm length

The upper and lower portions of the enclosure can be printed with a conventional FDM 3D printer, 0.2mm layer height is fine, no supports necessary. The buttons and joystick nub should be produced with a SLA/resin printer (orient the square hole on the joystick nub away from the build plate). An overview of the entire assembly process can be found here:

https://youtu.be/aIIc2DiZYcI

---------------

### Feature Highlights:
* Calculate word 12/24 of a BIP39 seed phrase
* Create 24-word BIP39 seed phrase with 99 dice rolls
* Temporarily store up to 3 seed phrases while device is powered
* Native Segwit Multisig XPUB generation w/ QR display
* Scan and parse transaction data from animated QR codes
* Sign transactions & transfer XPUB data using animated QR codes
* Support for Bitcoin Mainnet & Testnet
* Responsive, event-driven user interface
* Only valid input letters appear during seed word entry (time-saver!)

### Considerations:
* Built for compatibility with Specter v1.1.0 and up (support for other wallet coordinators coming)
* Current release takes ~50 seconds to boot before menu appears (be patient!)
* Use Specter's "other" device type when adding as a new signing device
* ALWAYS opt to use animated QR codes in Specter-desktop
* Always test your setup before transfering larger amounts of bitcoin (try testnet first!)
* Currently ONLY generating Native Segwit Multisig Xpubs
* Scanning animated QRs into a PC is tricky, be aware of ambient light, glare and focus
* (Holding the screen upside-down or at a slight angle can significantly reduce glare)
* Display text is small; comes with 240x240 pixel territory but ever trying to optimize
* Check out our "seedsigner" telegram community for community help / feedback: (https://t.me/joinchat/GHNuc_nhNQjLPWsS)
* If you think SeedSigner adds value to the Bitcoin ecosystem, please help me spread the word! (tweets, pics, videos, etc.)

### Planned Upcoming Improvements / Functionality:
* Support for Sparrow & Bluewallet multisig coordinators!
* Support for single-signature XPUB generation / signing
* Manually step through QR sequences using button/joystick controls
* Other optimizations based on user feedback!

---------------

## MANUAL BUILD INSTRUCTIONS:

The software can also be manually installed using an internet-connected Raspberry Pi 2/3/4 or Zero W are as follows:

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
* `sudo apt-get install python-pil`
* `sudo apt-get install libopenjp2-7`
* `sudo apt-get install ttf-mscorefonts-installer`
* `sudo apt-get install git`
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

Download SeedSigner
* `sudo git clone https://github.com/SeedSigner/seedsigner`

Modify the systemd to run SeedSigner at boot:
* `sudo nano /etc/systemd/system/seedsigner.service`

Add the following contents to the file:
```
[Unit]
Description=Seedsigner

[Service]
WorkingDirectory=/home/pi/seedsigner
ExecStart=/usr/bin/python3 /home/pi/seedsigner/main.py
Restart=always

[Install]
WantedBy=multi-user.target
```

Use Control + O, then [enter], to write the file.
Then use Control + X, to exit the program.

Run `sudo systemctl enable seedsigner.service` to enable service on boot. (This will restart the seedsigner code automatically at startup and if it crashes.)

(Optional) Modify the system swap configuration to disable virtual memory:
* `sudo nano /etc/dphys-swapfile`
add `CONF_SWAPSIZE=100` to `CONF_SWAPSIZE=0`

Use Control + O, then [enter], to write the file.
Then use Control + X, to exit the program.

To shut down the pi:
* `sudo shutdown --poweroff now`

Now either move the MicroSD card to a Pi Zero 1.3 with the 1.3-inch LCD Hat and camera installed, or the LCD Hat will also run fine on a Raspberry Pi 2/3/4 or Zero W; just remember to disable networking if you want to run the software in isolation.

It will take a couple of minutes after the Pi is powered on for the GUI to launch -- be patient!
