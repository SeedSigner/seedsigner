# Smartcard Seed Storage Support
## Background
Smart Cards are specifically designed to securely store digital data. Javacards are a type of Smart Cards that implement open standards development tools, making them ideal for DIY.

SeedKeeper is a open source seed storage product from Satochip which can be used to securely store multiple BIP39 seeds & passphrases. (And other types of secrets, but these aren't relevant to SeedSigner)

## Hardware Requirements
### USB Smart Card Readers
Any USB smart card reader that is compatible with will work, either hard-wired (Contact) or NFC (Contactless).

If you are running SeedSigner on a system image that is derived from a standard Raspberry Pi OS image, USB devices should be plug and play once PC/SC services are installed.

**Compatibility Notes**

The **ACS ACR 122U reader** is unreliable for flashing applets and may brick your card. (Though works fine for normal operation after they have been flashed)

### GPIO Connected Smart Card Readers
The PN352 NFC module is low cost ($5 on Aliexpress) can be connected via available IO pins and is well supported by LibNFC.

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

    git clone https://github.com/3rdIteration/pysatochip
    pip3 install -r requirements.txt
    cd pysatochip
    python setup.py install

### LibNFC + IFDNFC (Optional: Needed for PN352 connected via GPIO Pins)

**Install LibNFC**

    git clone https://github.com/nfc-tools/libnfc
    autoreconf -vis
    ./configure --with-drivers=pn532_i2c
    make
    make install
    sudo sh -c "echo /usr/local/lib > /etc/ld.so.conf.d/usr-local-lib.conf"
    sudo ldconfig

**Install IfdNFC**

    git clone https://github.com/nfc-tools/ifdnfc.git
    autoreconf -vis
    ./configure
    make
    make install

**Add Configuration Files** 
Create the folder 

    mkdir /usr/local/etc/nfc/

Create the file `/usr/local/etc/nfc/libnfc.conf` and add the following 

    device.name = "IFD-NFC"
    device.connstring = "pn532_i2c:/dev/i2c-1"

Create the file `/etc/reader.conf.d/libifdnfc` and add the following

    FRIENDLYNAME      "IFD-NFC"
    LIBPATH           /usr/local/lib/libifdnfc.so
    CHANNELID         0

**Restart PCSCD**

    sudo service pcscd restart

**Activating IFD-NFC**

You will notice that there is a menu option to `ifdnfc-activate` under the tools->SeedKeeper menu. Basically IFDNFC only needs to be run once on each boot, after which you need to restart the SeedSigner app. (But not the device)

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