## Relaying internet access to the Pi Zero 1.3 over USB
Insert the SD card with your Raspberry Pi OS image into a regular computer. Open a terminal window (macOS: Terminal; Windows: Command Prompt) and navigate to the SD card:
```
# mac/Linux:
cd /Volumes/boot

# Windows (alter with correct drive letter)
cd e:
```

We need to create an empty file called "ssh" to enable us to remotely terminal into the Pi via SSH.
```
# max/Linux:
touch ssh

# Windows
type nul > ssh
```

Now we have some incomprensible configuration steps to set up the internet access relay.

Add a line to the end of `config.txt`:
```
# mac/Linux/Windows:
echo dtoverlay=dwc2 >> config.txt
```

Open `cmdline.txt` in a basic text editor:
```
# mac/Linux:
nano cmdline.txt

# Windows
notepad cmdline.txt
```

Add `modules-load=dwc2,g_ether` **directly after** `rootwait`:
```
blah blah rootwait modules-load=dwc2,g_ether [possibly more blah]
```

Then if on mac/Linux, hit `CTRL-X` to exit and `y` to save your changes. In Notepad just save and close. 

Eject the SD card and insert it into your Pi Zero 1.3. Plug a USB cable into your computer and into the Pi's USB connector that is closer to the center. It will draw power from the USB cable and begin powering up.

The Pi will take a minute or so to boot up its OS. After waiting a bit, try to communicate with the Pi over SSH:
```
ssh pi@raspberrypi.local
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