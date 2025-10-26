## Debugging a Crash for Advanced (Technical) Users

These instructions are intended to help users of SeedSigner provide crash exception and traceback logs to developers to aid in troubleshooting and resolving bugs.

### Testnet vs Mainnet

Whenever possible, recreate a crash in testnet. This will help avoid accidentally revealing private information about yourself, your Bitcoin transactions, or losing any funds.

### Network-Connected SeedSigner

If you are using SeedSigner for development and testing, then we recommend network access via SSH to view crash logs. Follow [these](https://github.com/SeedSigner/seedsigner/blob/main/docs/usb_relay.md) instructions to set up a USB relay for internet access. You can also connect your SeedSigner to WiFi if you have a Raspberry Pi Zero W with WiFi.

### Airgapped Debugging Setup

If you are using SeedSigner for mainnet transactions, then do not connect your device to a network or the internet. Instead, connect your SeedSigner to an HDMI display (without internet) and a USB keyboard. This will require an HDMI adapter and a micro USB to USB A adapter. Plug in the HDMI display and keyboard before powering on SeedSigner. The password for the SeedSigner pi user is `raspberry`.

### Debugging Steps

At this point, you should be signed into the pi user either on an HDMI display (via command line) or an SSH connection.

Follow these steps to set up a debug session:

1. Navigate to the source directory:
   ```bash
   cd seedsigner/src
   ```

2. Edit the settings file:
   ```bash
   nano settings.ini
   ```

3. In the nano editor, change `debug = False` to `debug = True` (case sensitive). Save and exit settings.ini.

4. Stop the SeedSigner systemd process:
   ```bash
   sudo systemctl stop seedsigner.service
   ```

5. Start the Python app manually:
   ```bash
   python3 main.py
   ```

SeedSigner should now be up and running. Keep it connected to the display and keyboard. Recreate the steps to cause the crash. The traceback log and exception will be displayed on the HDMI display.