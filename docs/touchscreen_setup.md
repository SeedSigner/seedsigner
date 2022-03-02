# Initial Pi Setup
touch /media/skorn/boot/ssh

nano /media/skorn/boot/wpa_supplicant.conf
```
country=us
update_config=1
ctrl_interface=/var/run/wpa_supplicant

network={
 scan_ssid=1
 ssid="MyNetworkSSID"
 psk="Pa55w0rd1234"
}
```

https://wirelessthings.io/index.php/2021/05/01/720x720-lcd-screen-using-dpi-on-raspberry-pi-4/



Download and extract overlay files:
https://www.waveshare.com/wiki/File:28DPIB_DTBO.zip

copy files to /media/user/boot/overlays
cp ~/Downloads/28DPI_DTBO/waveshare-28dpi-* /media/skorn/boot/overlays



```bash
nano /media/skorn/boot/config.txt
```

```
# Update existing
#dtoverlay=vc4-kms-v3d
dtparam=i2c_arm=on
dtparam=i2s=on
dtparam=spi=on

# Add new
gpio=0-9=a2
gpio=12-17=a2
gpio=20-25=a2
dtoverlay=dpi24
enable_dpi_lcd=1
display_default_lcd=1
extra_transpose_buffer=2
dpi_group=2
dpi_mode=87
dpi_output_format=0x7F216
hdmi_timings=480 0 26 16 10 640 0 25 10 15 0 0 0 60 0 32000000 1
dtoverlay=waveshare-28dpi-3b-4b
dtoverlay=waveshare-28dpi-3b
dtoverlay=waveshare-28dpi-4b
display_rotate=1
```


sudo raspi-config

set to boot to desktop
set screen resolution: DMT 4 480 x 640
expand filesystem


# rotate display
sudo apt install xserver-xorg-input-libinput
sudo mkdir /etc/X11/xorg.conf.d
sudo cp /usr/share/X11/xorg.conf.d/40-libinput.conf /etc/X11/xorg.conf.d/
sudo nano /etc/X11/xorg.conf.d/40-libinput.conf
```
# add to touchscreen section
Option "CalibrationMatrix" "0 1 0 -1 0 1 0 0 1"
```

# current seedsigner application installs
sudo apt-get update && sudo apt-get install -y  \
python3-pip \
python-pil \
libopenjp2-7 \
git \
libatlas-base-dev \
qrencode \
python3-opencv \
python3-numpy \
python3-picamera

sudo apt-get update && sudo apt-get install -y wiringpi python3-pip \
   python3-numpy python-pil libopenjp2-7 git python3-opencv \
   python3-picamera libatlas-base-dev qrencode


apt-get install python-tk

sudo apt install imagemagick 


pip install pillow tk pyautogui


sudo apt-get install -y python3-pip \
   python3-numpy  libopenjp2-7 git python3-opencv \
   python3-picamera libatlas-base-dev qrencode


# Tkinter
sudo apt install python3-tk

# OPENBOX
sudo apt install openbox xinit lightdm


To run Openbox from the commandline, setup the .xinitrc file in your home directory and insert the following line:

exec openbox-session


application startup config
/etc/xdg/openbox/autostart
```
. /home/pi/env/bin/activate
cd /home/pi/seedsigner/src
nohup python3 main.py > /home/pi/seedsigner.log &
```


# Lightdm
sudo apt install lightdm

https://gist.github.com/kuanyui/2972b15639e78940cd1349844ca0e4fc

sudo nano /etc/lightdm/lightdm.conf
```
start-default-seat=true
autologin-user=pi
autologin-user-timeout=0
autologin-session=openbox
```

# ENV Vars
export DISPLAY=:0.0
export NOTAPI=true

# TKINTER Examples
https://tkdocs.com/tutorial/eventloop.html
https://python-textbok.readthedocs.io/en/1.0/Introduction_to_GUI_Programming.html
https://www.journaldev.com/48165/tkinter-working-with-classes

```
from PIL import Image
i = Image.open("cube.png")
i.show()
```

```
import tkinter as tk
from PIL import Image, ImageTk

def callback(event):
    print("clicked at", event.x, event.y)

window = tk.Tk()
window.attributes('-fullscreen',True)


x = window.winfo_pointerx()
y = window.winfo_pointery()



window.bind("<Button-1>", callback)


imagefile2 = "../../cube.png"
imgpil2 = Image.open(imagefile)
img2 = ImageTk.PhotoImage(imgpil)

imagefile = "seedsigner/resources/logo_black_240.png"
imgpil = Image.open(imagefile)
img = ImageTk.PhotoImage(imgpil)

#lbl = tk.Label(window, image = img).pack()
frame = tk.Label(window)
frame.configure(image=img)
frame.place(x=333,y=233)

lbl.configure(image=img2)

def button_press_move():
    frame.place(x=random.randint(0,640), y=random.randint(0,480))

btn_KEY_UP = tk.Button(window, text="KEY1")
btn_KEY_UP.place(x=50, y=50)
btn_KEY_UP.configure(width=10,height=4)
btn_KEY_UP.configure(command=button_press_move)


myglobal = None
myglobal1 = None


def press(event):
    print(event.state)
    print(dir(event))
    global myglobal
    myglobal1 = event

def release(event):
    print(event.state)
    print(dir(event))
    global myglobal1
    myglobal1 = event

btn_KEY_UP.bind("<ButtonPress>", press)
btn_KEY_UP.bind("<ButtonRelease>", release)

window.mainloop()
```

```
w = tk.Canvas(window, width=240, height=240, bg="green").pack()
```


```
from queue import Queue
from seedsigner.helpers import touchscreen
import tkinter as tk
from PIL import Image, ImageTk
import threading

a = Queue()
sq = touchscreen.touchscreen(a)
sq.Init()

import random
from time import sleep

def showimages():
    while True:
        print("looping images")
        imagefile2 = "../../cube.png"
        imgpil2 = Image.open(imagefile2)
        a.put((imgpil2, random.randint(0,400), random.randint(0,400)))
        sleep(0.1)

x = threading.Thread(target=showimages)
x.start()



img2 = ImageTk.PhotoImage(imgpil)
```


```
import tkinter as tk
import threading
import signal
import sys


class MyTkApp(object):
    def poll(self):
        sys.stderr.write("poll\n")
        self.root.after(500, self.poll)
    def quit(self, event):
        print("you pressed control c")
        self.root.quit()
    def run(self):
        self.root = tk.Tk()
        self.root.after(500, self.poll)
        self.root.bind('<Control-c>', self.quit)
        self.root.mainloop()


app = MyTkApp()
app.start()

import time

while app.is_alive():
    try:
        time.sleep(0.5)
    except KeyboardInterrupt:
        app.root.destroy()
        break
```


```
from queue import Queue
from seedsigner.helpers import touchscreen

```