# Manual Installation Instructions

Begin by acquiring a specific copy of the Raspberry Pi Lite operating system, dated 2021-05-28; this version can be found here:

https://downloads.raspberrypi.org/raspios_lite_armhf/images/raspios_lite_armhf-2021-05-28/

Best practice is to verify the downloaded .zip file containing the Raspberry Pi Lite OS matches the published SHA256 hash of the file; for additional reference that hash is: c5dad159a2775c687e9281b1a0e586f7471690ae28f2f2282c90e7d59f64273c. After verifying the file's data integrity, you can decompress the .zip file to obtain the operating system image that it contains. You can then use Balena's Etcher tool (https://www.balena.io/etcher/) to write the Raspberry Pi Lite software image to a memory card (4 GB or larger). It's important to note that an image authoring tool must be used (the operating system image cannot be simply copied into a file storage partition on the memory card).

The manual SeedSigner installation and configuration process requires an internet connection on the device to download the necessary libraries and code. But because the Pi Zero 1.3 does not have onboard wifi, you have two options:

1. Run these steps on a separate Raspberry Pi 2/3/4 or Zero W which can connect to the internet and then transfer the SD card to the Pi Zero 1.3 when complete.
2. OR configure the Pi Zero 1.3 directly by relaying through your computer's internet connection over USB. See instructions [here](usb_relay.md).

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


### Change the default password
Change the system's default password from the default "raspberry". Run the command:
```
passwd
```
You will be prompted to enter the current password ("raspberry") and then to enter a new password twice. In our prepared release image, the password used is `AirG@pped!`.


### Install dependencies
Copy this entire box and run it as one command (will take 15-20min to complete):
```
sudo apt-get update && sudo apt-get install -y wiringpi python3-pip \
   python3-numpy python-pil libopenjp2-7 git python3-opencv \
   python3-picamera libatlas-base-dev qrencode
```

### Install `zbar`
`zbar` is "an open source software suite for reading bar codes" (more info here: [https://github.com/mchehab/zbar](https://github.com/mchehab/zbar)).

SeedSigner requires `zbar` at 0.23.x or higher.

Download the binary:
```
curl -L http://raspbian.raspberrypi.org/raspbian/pool/main/z/zbar/libzbar0_0.23.90-1_armhf.deb --output libzbar0_0.23.90-1_armhf.deb
```

And then install it:
```
sudo apt install ./libzbar0_0.23.90-1_armhf.deb
```

Cleanup:
```
rm libzbar0_0.23.90-1_armhf.deb
```

### Install the [C library for Broadcom BCM 2835](http://www.airspayce.com/mikem/bcm2835/)
This library "provides functions for reading digital inputs and setting digital outputs, using SPI and I2C, and for accessing the system timers."

Run each of the following individual steps:
```
wget http://www.airspayce.com/mikem/bcm2835/bcm2835-1.60.tar.gz
tar zxvf bcm2835-1.60.tar.gz
cd bcm2835-1.60/
sudo ./configure
sudo make && sudo make check && sudo make install
cd ..
rm bcm2835-1.60.tar.gz
sudo rm -rf bcm2835-1.60
```

### Set up `virtualenv`
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

For convenience you can configure your `.profile` to auto-activate the SeedSigner virtualenv when you ssh in. Once again `nano ~/.profile` and add at the end:
```
workon seedsigner-env
```

Optional: If you're going to be testing new code on the SeedSigner, you'll find yourself often needing to kill the SeedSigner code that automatically runs at startup (we'll be configuring this further down). As an extra convenience you can list the process id so that you can then kill it from the terminal:
```
ps aux | grep main.py
```

Save your changes with `CTRL-X` and `y`.

Now when you `ssh` in you'll see something like:
```
pi         297 65.4  9.7  74096 36736 ?        Rsl  09:26  10:29 /home/pi/.envs/seedsigner-env/bin/python main.py
pi         857  0.0  0.4   7332  1876 pts/0    S+   09:42   0:00 grep --color=auto main.py
```

The top line is our SeedSigner code running. To stop it, run:
```
kill 297
```
Where `297` is the process id listed in the output above (it'll be different each time).


### Download the SeedSigner code:
```
git clone https://github.com/SeedSigner/seedsigner
cd seedsigner
```

If you want to run a specific branch within the main SeedSigner repo, switch to it with:
```
git checkout yourtargetbranch
```

And if you want to test a pull request (PR), for example PR #123:
```
git fetch origin pull/123/head:pr_123
git checkout pr_123
```

where `pr_123` is any name you want to give to the new branch in your local repo that will hold the PR.


### Install Python `pip` dependencies:
```
pip3 install -r requirements.txt
```

#### `pyzbar`
Note: The `requirements.txt` installs a fork of the python `pyzbar` repo (for now pointing to the fork in Keith's `kdmukai` github account [https://github.com/kdmukai/pyzbar](https://github.com/kdmukai/pyzbar)).

The fork is required because the main `pyzbar` repo has been abandoned. This [github issue](https://github.com/NaturalHistoryMuseum/pyzbar/issues/124#issuecomment-971967091) discusses the changes needed in order to support reading binary data from `zbar`, which is required for our `CompactSeedQR` format which writes byte data instead of strings. The changes specifically reference the following PRs which have already been merged into Keith's fork:
* [PR 76](https://github.com/NaturalHistoryMuseum/pyzbar/pull/76/files): enables scanning to continue even when a null byte (`x\00`) is found.
* [PR 82](https://github.com/NaturalHistoryMuseum/pyzbar/pull/82): enable `zbar`'s new binary mode. Note that this PR has a trivial bug that was fixed in Keith's fork.

### Configure `systemd` to run SeedSigner at boot:
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

_Note: If you'll be testing new code on the SeedSigner, you'll want to omit the `Restart=always` line._

Use `CTRL-X` and `y` to exit and save changes.

Configure the service to start running (this will restart the seedsigner code automatically at startup and if it crashes):
```
sudo systemctl enable seedsigner.service
```

Now reboot the Raspberry Pi:
```
sudo reboot
```

After the Raspberry Pi reboots, you should see the SeedSigner splash screen and the SeedSigner menu subsequently appear on the LCD screen (note that it can take up to 60 seconds for the menu to appear).

### Further OS modifications
Disable and remove the system's virtual memory / swap file with the commands:
```
sudo apt remove dphys-swapfile -y
sudo apt autoremove -y
sudo rm /var/swap
```

## Local testing and development
For those who will use the SeedSigner installation for testing/development, it can be helpful to change the system's host name so it doesn't potentially conflict with other Raspberry Pis that may already be present on your network. (For those who don't plan to use the installation for testing or development, you can skip this portion of the process.) To change the host name first edit the "hostname" with the command:
```
sudo nano /etc/hostname
```
and change "raspberrypi" to "seedsigner" (or another name). Use `CTRL-X` and `y` to exit and save changes. You'll also need to edit the "hosts" file with the command:
```
sudo nano /etc/hosts
```
and change "raspberrypi" to "seedsigner" (or the other name you previously chose). Use `CTRL-X` and `y` to exit and save changes.

### Set a static IP
Your local machine that `ssh`s into the SeedSigner can sometimes get confused if you're connecting to different SeedSigners that are all identified as `pi@seedsigner.local`. In this case it helps to set a static ip and just `ssh` directly to that instead.

First find your current `nameserver`:
```
sudo cat /etc/resolv.conf
```

This is the address of your local machine that is connected to your SeedSigner via usb (or it'll be the wifi router's address if you're using a Raspi with wifi and are keeping it enabled for `ssh` access).

Set a static ip: `sudo nano /etc/dhcpcd.conf` and add to the end:
```
interface usb0
static ip_address=192.168.1.200/24
static routers=192.168.1.254
static domain_name_servers=192.168.1.254
```

* `interface` will be `usb0` for usb connections; `wlan0` for wifi.
* `static ip_address` is the ip address you want the SeedSigner to use. It should match the `nameserver` ip you found above for all but the last part of the ip (note: the `/24` should always be included as-is).
* `static routers` should be your `nameserver` ip.
* `static domain_name_servers` should also be the `nameserver` ip.

`CTRL-X` and `y` to save changes.

After your next reboot, access this SeedSigner using its new static ip:
```
ssh pi@192.168.1.200
```

### More convenient `ssh` access:
Power SeedSigner devs will find themselves connecting to a lot of different SeedSigners. This can cause headaches with `ssh`'s built-in protections; a different device that uses the same `ssh` credentials is normally a potential spoofing attack. But we're doing this to ourselves on purpose and so we can carve out exceptions.

On your local machine, run `nano ~/.ssh/config` and add to the end:
```
host seedsigner.local
 StrictHostKeyChecking no
 UserKnownHostsFile /dev/null
 User pi
 LogLevel QUIET

host 192.168.1.200
 StrictHostKeyChecking no
 UserKnownHostsFile /dev/null
 User pi
 LogLevel QUIET
```

The first entry prevents warnings for the default `pi@seedsigner.local` connections.

The second entry does the same for a specific static ip; you'll want this if you configure all your SeedSigners to use the same static ip.

`CTRL-X` and `y` to save changes.


#### Bypass `ssh` password
You can also configure the SeedSigner so that you don't have to enter the `pi` password when you `ssh` in.

run `ssh-copy-id` with the same values that you connect via `ssh`:
```
ssh-copy-id pi@seedsigner.local

# or if you're connecting over static ip, something like:
ssh-copy-id pi@192.168.1.200
```

You'll be prompted to enter the password to complete it.

_Note: If you don't have any ssh keys on your local machine, you'll need to create a set with `ssh-keygen -t ed25519 -C "your_email@example.com"`. Then try running `ssh-copy-id` again._


## Disable wifi/Bluetooth when using other Raspi boards
If you plan to use your installation on a Raspberry Pi that is not a Zero version 1.3, but rather on a Raspberry Pi that has WiFi and Bluetooth capabilities, it is a good idea to disable the following WiFi & Bluetooth, as well as other relevant services (assuming you are not creating this installation for testing/development purposes). Enter the following commands to disable WiFi, Bluetooth, & other relevant services:
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

If you used option #2 above and don't plan to continue to access your SeedSigner via SSH over USB, it is a good idea to reverse the steps you took to enable it -- those instructions can be found near the end of [this guide](usb_relay.md).

Please remember that it can take up to a minute for the GUI to appear when powering your SeedSigner on.


### Optional: Run the tests
see: [tests/README.md](../tests/README.md)
