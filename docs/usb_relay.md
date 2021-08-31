## Relaying internet access to the Pi Zero 1.3 over USB

Note that this is an optional, alternate way to initialize your SeedSigner. The default method is to work on a separate Raspberry Pi device that has internet access. Be aware that by enabling internet access over USB you are obviously creating a link to the outside world that this project seeks to avoid.

If you use this setup route, we recommend that you disable internet access over USB when these steps are complete.


### Get started

Insert the SD card with your Raspberry Pi OS image into a regular computer. Open a terminal window (macOS: Terminal; Windows: Command Prompt) and navigate to the SD card:
```
# mac/Linux:
cd /Volumes/boot

# Windows (alter with correct drive letter):
cd e:
```

We need to create an empty file called "ssh" to enable us to remotely terminal into the Pi via SSH.
```
# mac/Linux:
touch ssh

# Windows:
type nul > ssh
```


Now we have some incomprensible configuration steps to set up the internet access relay.

Edit `config.txt`:
```
# mac/Linux:
nano config.txt

# Windows:
notepad config.txt
```

Add `dtoverlay=dwc2` to the end of `config.txt`. Exit and save changes (CTRL-X, then "y" in nano).


Alternatively, add to `config.txt` via the command line:
```
# mac/Linux/Windows:
echo dtoverlay=dwc2 >> config.txt
```


Next, edit `cmdline.txt`:
```
# mac/Linux:
nano cmdline.txt

# Windows:
notepad cmdline.txt
```

Add `modules-load=dwc2,g_ether` **directly after** `rootwait`:
```
blah blah rootwait modules-load=dwc2,g_ether [possibly more blah]
```

Exit and save changes (CTRL-X, then "y" in nano).


Eject the SD card and insert it into your Pi Zero 1.3. Plug a USB cable into your computer and into the Pi's USB connector that is closer to the center. It will draw power from the USB cable and begin powering up.

The Pi will take a minute or so to boot up its OS. After waiting a bit, try to communicate with the Pi over SSH:
```
# Manual builds:
ssh pi@raspberrypi.local

# Pre-built image:
ssh pi@seedsigner.local
```

If you see the following prompt, type `yes` to continue:
```
The authenticity of host 'raspberrypi.local (192.168.2.3)' can't be established.
ECDSA key fingerprint is SHA256:go4yVgii1GcvyxzhOe03atLn5bl2NhZlOR04tJHBo+k.
Are you sure you want to continue connecting (yes/no/[fingerprint])?
```

At the password prompt enter the Pi's default password: `raspberry`

If you now see the Pi's command prompt, you're in!
<img src="img/usb_relay_01.png">

Notice this warning in particular:
```
SSH is enabled and the default password for the 'pi' user has not been changed.
This is a security risk - please login as the 'pi' user and type 'passwd' to set a new password.
```

If someone savvy got access to your SeedSigner, they could sign into it and potentially upload malicious code. To add an extra layer of protection, change the default 'pi' user's password now by typing `passwd`:
```
pi@raspberrypi:~ $ passwd
Changing password for pi.
Current password: 
New password: 
Retype new password: 
passwd: password updated successfully
```


## Configure host computer to share internet access with the Pi

### macOS
Open the "Network" system settings. You should see an entry called "RNDIS/Ethernet Gadget":

<img src="img/usb_relay_mac_01.png">

Click "Advanced" and change "Configure IPv6" to "Link-local only":

<img src="img/usb_relay_mac_02.png">

Click "OK" and save your changes.

Now go to the "Sharing" system settings. Click on "Internet Sharing" and check the "RNDIS/Ethernet Gadget". 

<img src="img/usb_relay_mac_03.png">

Click the "Internet Sharing" checkbox to activate.

Back at your SSH terminal, test the connection:
```
ping 8.8.8.8
```

_Hit `CTRL-C` to abort the ping_

If you see a ping response, the Pi has internet access!

<img src="img/usb_relay_mac_04.png">


### Windows
see: https://www.circuitbasics.com/raspberry-pi-zero-ethernet-gadget/


## Complete the setup
Return to the main [README](../README.md) and complete the setup steps. But remember to come back here and disable internet access over USB on your SeedSigner.


## Disable internet access
Power down the SeedSigner and remove the SD card. Put the SD card back into your computer and use a terminal to navigate to the `boot` drive (same process as above).

Edit `config.txt`:
```
# mac/Linux:
nano config.txt

# Windows:
notepad config.txt
```

Delete the `dtoverlay=dwc2` line that we added to the end of the file. Exit and save changes (CTRL-X, then "y" in nano).


Edit `cmdline.txt`:
```
# mac/Linux:
nano cmdline.txt

# Windows:
notepad cmdline.txt
```

Delete `modules-load=dwc2,g_ether`. Exit and save changes (CTRL-X, then "y" in nano).

Eject the SD card and put it back in the SeedSigner. Connect the SeedSigner to your computer with a USB cable. It should no longer show up as a "RNDIS/Ethernet Gadget".

SSH into the pi and try to `ping 8.8.8.8`. It should fail with no responses.

For full security, put the SD card back in your computer one last time and delete the `ssh` file from `boot`:
```
# mac/Linux:
rm ssh

# Windows:
del ssh
```

You're now good to go with a SeedSigner that is back to being fully air-gapped!