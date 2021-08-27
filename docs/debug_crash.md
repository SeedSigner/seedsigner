## Debugging a Crash for advanced (technical) users

These instructions are intended to help users of SeedSigner provide crash exception and traceback logs to developers to aid in troubleshooting and resolving bugs.

### Testnet vs Mainnet

Whenever possible recreate a crash in testnet. This will help avoid accidently revealing private information about yourself, your bitcoin transactions, or lose any funds.

### Network connected SeedSigner

If you are using SeedSigner for development and testing, then I recommend network access via ssh to view crash logs. Follow [these](https://github.com/SeedSigner/seedsigner/blob/main/docs/usb_relay.md) instructions to setup a USB relay for internet access. You can also connect your SeedSigner to Wifi if you have a rasp pi zero w/ wifi.

### Airgapped debugging setup

If you are using SeedSigner for mainnet transactions, then do not connect your device to a network or the internet. Instead connect your SeedSigner to a HDMI display (without internet) and a USB keyboard. This will require an HDMI adapter and micro USB to USB A adapter. Plug in the HDMI display and keyboard before powering on SeedSigner. The password for the SeedSigner pi user is `raspberry`.

### Debugging steps

At this point you should be signed into the pi user either on a HDMI display (via command line) or a ssh connection.

Follow these steps to setup a debug session.

`cd seedsigner/src`

`nano settings.ini`

in nano editor change `debug = False` to `debug = True` (case sensitive). Save and exit settings.ini.

stop the seedsigner systemd process by running

`sudo systemctl stop seedsigner.service`

now start the python app manually by running

`python3 main.py`

SeedSigner should now be up and running. Keep it connected to the display and keyboard. Recreate the steps to cause the crash. The traceback log and exception will be displayed on the HDMI display.