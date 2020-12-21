Hello World!

Here is a simple program to calculate the word 24 checksum from the first 23 words of a bitcoin wallet seed phrase!

(Newest Feature: Generate a seed phrase with entropy from rolled dice)

![Image of SeedSigner running on a Raspberry Pi Zero](https://github.com/SeedSigner/seedsigner/blob/main/Assembled_SeedSigner.JPG)

More functionality will be added over time, but for now you can calculate word 24 on a very low-cost system without wireless capability -- no need to worry about bluetooth, airplane mode, web caching, etc. etc. 

The code is designed to ultimately be run on a Raspberry Pi Zero (version 1.3 with no wireless capability) with a Waveshare 1.3" 240x240 pxl LCD (more info at https://www.waveshare.com/wiki/1.3inch_LCD_HAT).

The easiest way to get it up and running is to install using an internet-connected Raspberry Pi 2/3/4 or Zero W, and then remove the MicroSD card and install it in the Raspberry Pi Zero 1.3 with the Waveshare 1.3" LCD hat installed. Seedsigner will run when the Zero 1.3 is powered on, and a soft shutdown of the Pi can be done within the interface.

A preconfigured Raspberry Pi image can be downloaded here: https://drive.google.com/file/d/1CdAC09OX5ADRBaDxUJwthePwq11AFF8H/view?usp=sharing

The image can be written to a 4GB (or larger) MicroSD card, then installed in a Raspberry Pi 2/3/4 or Zero.

The steps to install using an internet-connected Raspberry Pi 2/3/4 or Zero W are as follows:

Install the Raspberry Pi Lite operating system (https://www.raspberrypi.org/software/operating-systems/) on a MicroSD card and install the card in a Raspberry Pi 2/3/4 or Zero W.

Connect a keyboard & monitor, or SSH into the Pi if you're familiar with that process.

* `sudo raspi-config`
(set your localization options, configure WiFi if necessary, but most important: navigate to the "interface options" and enable the "SPI" interface)

Reboot when prompted within the raspi-config interface

Install these:
* `sudo apt-get update`
* `sudo apt-get install wiringpi`
* `sudo apt-get install python3-pip`
* `sudo apt-get install python3-numpy`
* `sudo apt-get install python-pil`
* `sudo apt-get install libopenjp2-7`
* `sudo apt-get install ttf-mscorefonts-installer`
* `sudo apt-get install git`

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

Download SeedSigner
* `sudo git clone https://github.com/SeedSigner/seedsigner`

Modify the system config to run SeedSigner at boot:
* `sudo nano /etc/rc.local`
add `sudo python3 /home/pi/seedsigner/seedsigner.py &`
to the line above `exit 0`

Use Control + O, then [enter], to write the file.
Then use Control + X, to exit the program.

To shut down the pi:
* `sudo shutdown --poweroff now`

Now either move the MicroSD card to a Pi Zero 1.3 with the 1.3-inch LCD Hat installed, or the LCD Hat will also run fine on a Raspberry Pi 2/3/4 or Zero W; just remember to disable networking if you want to run the software in network isolation.

It will take a minute or so after the Pi is powered on for the GUI to launch.
