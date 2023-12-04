# Smartcard Seed Storage Support
## Background
Smart Cards are specifically designed to securely store digital data. Javacards are a type of Smart Cards that implement open standards development tools, making them ideal for DIY.

SeedKeeper is a open source seed storage product from Satochip which can be used to securely store multiple BIP39 seeds & passphrases. (And other types of secrets, but these aren't relevant to SeedSigner) In addition to providing the nessesary functionality, along with security features like secure-channel to protect the data exchange from eavesdropping, etc, the SeedKeeper also has standalone software available for users who may need to securely retrieve their data without access to a SeedSigner... 

This guide focuses on DIY SeedKeeper cards (which are the best for testing) but this will also work with retail SeedKeeper cards for those who prefer that simplicity...

## Hardware Requirements
### USB Smart Card Readers 
Any USB smart card reader that is compatible with will work, either hard-wired (Contact) or NFC (Contactless).

If you are running SeedSigner on a system image that is derived from a standard Raspberry Pi OS image, USB devices should be plug and play once PC/SC services are installed.

**Compatibility Notes**

The **ACS ACR 122U reader** is unreliable for flashing applets and may brick your card. (Though works fine for normal operation after they have been flashed)

### GPIO Connected Smart Card Readers
The PN352 NFC V3 module is low cost ($5 on Aliexpress) can be connected via available IO pins and is well supported by LibNFC.

Instructions on how to physically connect it can be found here: https://blog.stigok.com/2017/10/12/setting-up-a-pn532-nfc-module-on-a-raspberry-pi-using-i2c.html (Stop when you get to the section on LibNFC, as that part is not relevant)

## Software Installation

The following guide assumes that you have completed the [Manual Installation guide...](./manual_installation.md)

### SeedSigner with SeedKeeper Support
You will need to clone this repository in the place of the existing seedsigner folder in `/home/pi/seedsigner`

### Smartcard Libraries

Install the following additional software

    sudo apt-get install git autoconf libtool libusb-dev libusb-dev libpcsclite-dev i2c-tools pcscd libpcsclite1 swig

### PySatoChip
While you can install PySatoChip directly from pip, the current (Nov 2023) release of PySatoChip needs a few tweaks before it will work with the code here. (Which may have been merged into the Master by the time you read this)

For now, you can download and build my fork using the code below. This will manually build the cryptography module which will take a few hours and also requires that you have a working installation of the Rust Compiler.

**Install Rust**

    curl https://sh.rustup.rs -sSf | sh

_Choose option 1 to install Rust_

**Install PySatoChip**

    cd ~
    git clone https://github.com/3rdIteration/pysatochip
    cd pysatochip
    pip3 install -r requirements.txt
    cd pysatochip
    python setup.py install

### LibNFC + IFDNFC (Optional: Needed for PN352 connected via GPIO Pins)

**Install LibNFC**

    cd ~
    git clone https://github.com/nfc-tools/libnfc
    cd libnfc
    autoreconf -vis
    ./configure --with-drivers=pn532_i2c
    make
    sudo make install
    sudo sh -c "echo /usr/local/lib > /etc/ld.so.conf.d/usr-local-lib.conf"
    sudo ldconfig

**Install IfdNFC**

    cd ~
    git clone https://github.com/nfc-tools/ifdnfc
    cd ifdnfc
    autoreconf -vis
    ./configure
    make
    sudo make install

**Note Concerning IfdNFC**
You may get a message like `Insufficient buffer` you run `idfnfc-activate`, or a message like `ifdnfc inactive` but it is actually working. (Even on x86 platforms when it doesn't work with other tools like pcsc_scan) 

**Add Configuration Files** 
Create the folder 

    sudo mkdir /usr/local/etc/nfc/

Create the file `/usr/local/etc/nfc/libnfc.conf` and add the following (`sudo nano /usr/local/etc/nfc/libnfc.conf`)

    device.name = "IFD-NFC"
    device.connstring = "pn532_i2c:/dev/i2c-1"

Create the file `/etc/reader.conf.d/libifdnfc` and add the following (`sudo nano /etc/reader.conf.d/libifdnfc`)

    FRIENDLYNAME      "IFD-NFC"
    LIBPATH           /usr/local/lib/libifdnfc.so
    CHANNELID         0

**Restart PCSCD**

    sudo service pcscd restart

**Activating IFD-NFC**

You will notice that there is a menu option to `Start PN532(PN532)` under the tools->SeedKeeper menu. Basically IFDNFC only needs to be run once on each boot, after which you need to restart the SeedSigner app. (But not the device)

Applet management operations (Installing, uninstalling, etc) often terminate the `idfnfc` process after completing, so if you can no longer do SeedKeeper operations like change PIN, load or save secrets, immediatly after flashing the applet, then this is likely why. (Just re-run the `ifdnfc-activate` process I mention above, restart the app and it should work fine)

### Javacard Managment Tools (Optional: Needed to flash SeedKeeper to Javacards)

You just need to install openjdk-8-jdk and Apache Ant

Follow the guide here: https://github.com/3rdIteration/Satochip-DIY

_The applet management (install/uninstall) in the SeedSigner menu assume that the Satochip-DIY repository was cloned into /home/pi/Satochip-DIY and built as per the guide in the repository._

The commands that the menu items run are currently hardcoded to be:

    java -jar /home/pi/Satochip-DIY/gp.jar --install /home/pi/Satochip-DIY/build/SeedKeeper-official-3.0.4.cap

    java -jar /home/pi/Satochip-DIY/gp.jar --uninstall /home/pi/Satochip-DIY/build/SeedKeeper-official-3.0.4.cap

### Javacard Build Environment (Optional: Needed to build SeedKeeper from Source)

Follow the guide here: https://github.com/3rdIteration/Satochip-DIY

### OpenCT and Generic/Old Blue "Sim Readers" (Optional: Get a more modern Smart Card reader if possible... )
**Included only for Reference/Education/Backup, as these can be built from Scratch...**

It's possible to obtain very cheap USB "Sim Readers" (Often Blue) for under $5 USD that can be used to access the Seedkeeper. (Or you can build on using the schematic here: https://circuitsarchive.org/circuits/smartcard/smartcard-pc-serial-reader-writer-phoenix/) 

These types of devices will *not* be automatically detected or usable on modern Systems (Windows will give you an explicit error that the PL2302 USB-to-Serial converter is not supported) but can be made to work on Linux and/or Raspberry Pi through using OpenCT and configuring it to work as a Phoenix type reader.

_Note: The version of OpenSC that can be installed via APT is buggy and will not work, it must be built from source..._

To Install and configure OpenCT

    cd ~
    git clone https://github.com/OpenSC/openct
    cd openct
    ./bootstrap
    ./configure --enable-pcsc
    make
    sudo make install
    sudo ldconfig
    sudo mkdir -p /usr/local/var/run/openct/

Then Add configuration files to use it with PCSC tools

Add it to the list of readers `sudo nano /etc/reader.conf.d/openct`

    FRIENDLYNAME     "OpenCT"
    DEVICENAME       /dev/null
    LIBPATH          /usr/local/lib/openct-ifd.so
    CHANNELID        0

Enable the Phoenix Driver in OpenCT `sudo nano /usr/local/etc/openct.conf`

and add the following to the end of the file

    reader phoenix {
        driver = phoenix;
        device = serial:/dev/ttyUSB0;
    };


Once you have done this, you can boot the device with the USB SIM reader connected.

Once the device is started, go into `tools->seedkeeper>Start OpenCT(SIM)` and the USB reader should then work until the next restart.

_Adapted from https://timesinker.blogspot.com/2016/04/using-cheap-sim-card-readers.html_