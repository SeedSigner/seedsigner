Hello World!

Build your own offline, airgapped Bitcoin transaction signing device for less than $50! Also generate seed word 12/24 or generate a seed phrase from dice rolls!

![Image of SeedSigner in an Orange Pill enclosure](https://github.com/SeedSigner/seedsigner/blob/main/Orange_Pill.JPG)

LATEST UPDATE
------ ------

The Orange Pill enclosure design has been open-sourced! Check out the "Orange_Pill" folder in this repo. You'll need the following additional hardware to assemble it:

* 4 x F-F M2.5 spacers, 10mm length
* 4 x M2.5 pan head screws, 6mm length
* 4 x M2.5 pan head screws, 12mm length

The upper and lower portions of the enclosure can be printed with a conventional FDM 3D printer, 0.2mm layer height is fine, no supports necessary. The buttons and joystick nub should be produced with a SLA/resin printer (orient the square hole on the joystick nub away from the build plate). An overview of the entire assembly process can be found here:

https://youtu.be/aIIc2DiZYcI

---------------
NOTE TO POTENTIAL CONTRIBUTORS: The current code base is being reorganized to allow for multithreading and other efficiency improvements; we are hoping to merge the new code structure in early May. After the transition to the new structure, issues and pull requests from any and all interested contributors should follow a much more conventional process. If you are currently auditing the code or doing any work to improve the structure, you may consider pausing your efforts until the reorganized code has been merged. Thank you!!!

---------------

The code is designed to ultimately be run on a Raspberry Pi Zero (version 1.3 with no wireless capability) with a Waveshare 1.3" 240x240 pxl LCD (more info at https://www.waveshare.com/wiki/1.3inch_LCD_HAT) and a Pi Zero-compatible camera (tested to work with the Aokin / AuviPal 5MP 1080p with OV5647 Sensor Video Camera Module; other brands with that sensor module may work as well, but may not fit in the Orange Pill enclosure). Choose the Waveshare screen carefully (there are several similar models); make sure to purchase the model that has a resolution of 240x240 pixels.

The easiest way to get the signer up and running is to downloaded the "seedsigner_0_1_0.zip" file in the current release, extract the seedsigner .img file, and write it to a MicroSD card (at least 4GB in size or larger). Then install the MicroSD in the assembled hardware and off you go.

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

KNOWN ISSUE:
* The seed word "yellow" was inadvertently replaced with the word "ORANGE" in the hard-coded BIP 0039 seed word list. It will not be possible to enter the word "yellow" if your seed contains that word. This issue will be corrected in the next release.

Considerations:
* Built for compatibility with Specter v1.1.0 and up
* Be patient, it takes a couple of minutes for the menu to come up after applying power to the Pi Zero (when you see the "static" you're almost there!)
* Use Specter's "other" device type when adding
* For now, ALWAYS opt to use animated QR codes in Specter-desktop
* On Mainnet, initially test with SMALL AMOUNTS of bitcoin (try Testnet first)
* Currently ONLY generating Native Segwit Multisig Xpubs
* Scanning animated QRs into a PC is tricky, be aware of ambient light, glare and focus
* (Holding the screen upside-down significantly reduces glare for some reason)
* Display text is small; comes with 240x240 territory but ever trying to optimize
* Check out our "seedsigner" telegram community for community help / feedback: (https://t.me/joinchat/GHNuc_nhNQjLPWsS)
* If you think SeedSigner adds value to the Bitcoin ecosystem, please help me spread the word! (tweets, pics, videos, etc.)

Coming Improvements/Functionality:
* Add support for single QR codes
* Support for single signature Xpub key generation
* Select from different display colors
* Other optimizations based on user feedback!

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
create file with contents
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
Run `sudo systemctl enable seedsigner.service` to enable service on boot. This will restart the seedsigner code automatically at startup and if it crashes.

Use Control + O, then [enter], to write the file.
Then use Control + X, to exit the program.

(Optional) Modify the system swap configuration to disable virtual memory:
* `sudo nano /etc/dphys-swapfile`
add `CONF_SWAPSIZE=100` to `CONF_SWAPSIZE=0`

Use Control + O, then [enter], to write the file.
Then use Control + X, to exit the program.

To shut down the pi:
* `sudo shutdown --poweroff now`

Now either move the MicroSD card to a Pi Zero 1.3 with the 1.3-inch LCD Hat and camera installed, or the LCD Hat will also run fine on a Raspberry Pi 2/3/4 or Zero W; just remember to disable networking if you want to run the software in isolation.

It will take a couple of minutes after the Pi is powered on for the GUI to launch -- be patient!
