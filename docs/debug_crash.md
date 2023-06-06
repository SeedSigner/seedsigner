## Debugging a Crash for advanced (technical) users

These instructions are intended to help users of LumenSigner provide crash exception and traceback logs to developers to aid in troubleshooting and resolving bugs.

### Testnet vs Public

Whenever possible recreate a crash in testnet. This will help avoid accidently revealing private information about yourself, your Stellar transactions, or lose any funds.

### Network connected LumenSigner

If you are using LumenSigner for development and testing, then I recommend network access via ssh to view crash logs. Follow [these](https://github.com/LumenSigner/lumensigner/blob/main/docs/usb_relay.md) instructions to setup a USB relay for internet access. You can also connect your LumenSigner to Wifi if you have a rasp pi zero w/ wifi.

### Airgapped debugging setup

If you are using LumenSigner for mainnet transactions, then do not connect your device to a network or the internet. Instead connect your LumenSigner to a HDMI display (without internet) and a USB keyboard. This will require an HDMI adapter and micro USB to USB A adapter. Plug in the HDMI display and keyboard before powering on LumenSigner. The password for the LumenSigner pi user is `raspberry`.

### Debugging steps

At this point you should be signed into the pi user either on a HDMI display (via command line) or a ssh connection.

Follow these steps to setup a debug session.

`cd lumensigner/src`

`export LUMEN_SIGNER_DEV_MODE=1`

stop the lumensigner systemd process by running

`sudo systemctl stop lumensigner.service`

now start the python app manually by running

`python3 main.py`

LumenSigner should now be up and running. Keep it connected to the display and keyboard. Recreate the steps to cause the crash. The traceback log and exception will be displayed on the HDMI display.