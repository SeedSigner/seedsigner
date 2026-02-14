# Local SeedSigner Simulator Setup

This guide adds a method to setup SeedSigner testing locally through a simulator GUI for easy development.

It was tested on macOS (26) using Homebrew and Python 3.14. With additional effort it would work on other operating systems and python version or it may still way directly I've not tested it as I don't own any other devices.

<img src="img/simulator.png" width=320 />

---

### Prerequisites

- A desktop / laptop with webcam

---

### Installing system dependencies

SeedSigner’s simulator depends on native libraries for QR scanning and camera access.

```bash
brew install opencv zbar
```

These provide:

- Camera capture backend (OpenCV)
- QR decoding backend (zbar, used by `pyzbar`)



### Setting up dev environment

The GUI uses tkinter that usually bundles with python installation, but for any reason it is not present follow the guide to setup tkinter https://coderivers.org/blog/installing-tkinter-in-python

```bash
git clone https://github.com/SeedSigner/seedsigner

python3.14 -m venv env
source env/bin/activate

# should not fail loading tkinter
python3.14 -m tkinter

pip install -r requirements.txt
```

#### Camera Permissions (macOS Security)

On first run, macOS will block camera access. You may see logs like:

```
OpenCV: not authorized to capture video
OpenCV: camera failed to properly initialize
```

#### Grant Camera Permission

Go to: System Settings → Privacy & Security → Camera

Enable camera access for:

- Terminal (if you run from Terminal)
- VS Code (if you run from VS Code)

Then restart Terminal and rerun the simulator.

You can also reset permissions if macOS didn’t prompt:

```bash
tccutil reset Camera
```

### Running the Simulator

From the simulator directory:

```bash
python src/gui.py
```

### Notes

- The simulator environment is **not security-hardened** and should never be used with real funds.
- Camera access, QR decoding, and GUI rendering are all platform-dependent; macOS quirks differ from Raspberry Pi OS.
- For hardware deployment, follow the official Raspberry Pi OS instructions in the main project README.
