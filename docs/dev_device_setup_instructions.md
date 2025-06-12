# Raspberry Pi OS Local Dev Build Instructions



##
```bash

curl -LsSf https://astral.sh/uv/install.sh | sh
source $HOME/.local/bin/env

uv python install 3.11

sudo apt install git

git clone https://github.com/lightningspore/seedsigner.git
cd seedsigner

uv python list
uv venv --managed-python
source .venv/bin/activate

uv pip install -i https://piwheels.org/simple \
    -r requirements.txt \
    -r requirements-raspi.txt


sudo raspi-config

sudo apt install libzbar0 libzbar-dev zbar-tools


```

```
export DISABLE_TIFF=1
export DISABLE_WEBP=1
```
libtiff5-dev


```
sudo apt install libopenblas-base libopenblas-dev liblapack3 liblapack-dev
```

uv pip install --reinstall --no-binary pillow pillow==10.0.1
uv pip install --reinstall --no-binary numpy numpy==1.25.2 -v


uv pip install pytest


## Modernize

Use Raspberry Pi Imager Software: Raspberry Pi OS Lite Bookworm

```
"spidev.bufsiz=250000" -> /bootfs/cmdline.txt
```