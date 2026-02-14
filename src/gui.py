import os
import numpy as np
import socket
import threading
import time

from tkinter import *
from PIL import Image, ImageTk

from seedsigner.hardware.buttons import HardwareButtons


class Display:
    def __init__(self, width: int = 240, height: int = 240):
        self.width = width
        self.height = height

        self.setup_sock()
        self.run()

    def run(self):
        self.root = Tk()
        self.root.title("SeedSigner")

        self.root.geometry(f"{self.width*2}x{self.height}+240+240")
        self.root.resizable(False, False)
        self.root.configure(bg='orange')
        self.root.attributes("-topmost", True)

        self.label=Label(self.root)
        self.label.pack()

        self.joystick=Frame(self.root)
        self.joystick.pack()
        self.joystick.place(x=20, y=85)
        self.joystick.configure(bg='orange')

        pixel = PhotoImage(width=1, height=1)

        self.btnL = Button(self.joystick, image=pixel, width=20, height=20, command=HardwareButtons.KEY_LEFT_PIN)
        self.btnL.grid(row=1, column=0)
        self.bindButtonClick(self.btnL)

        self.btnR = Button(self.joystick, image=pixel, width=20, height=20, command=HardwareButtons.KEY_RIGHT_PIN)
        self.btnR.grid(row=1, column=2)
        self.bindButtonClick(self.btnR)

        self.btnC = Button(self.joystick, image=pixel, width=20, height=20, command=HardwareButtons.KEY_PRESS_PIN)
        self.btnC.grid(row=1, column=1)
        self.bindButtonClick(self.btnC)

        self.btnU = Button(self.joystick, image=pixel, width=20, height=20, command=HardwareButtons.KEY_UP_PIN)
        self.btnU.grid(row=0, column=1)
        self.bindButtonClick(self.btnU)

        self.btnD = Button(self.joystick, image=pixel, width=20, height=20, command=HardwareButtons.KEY_DOWN_PIN)
        self.btnD.grid(row=2, column=1)
        self.bindButtonClick(self.btnD)

        self.btn1 = Button(self.root, image=pixel, width=40, height=20, command=HardwareButtons.KEY1_PIN)
        self.btn1.place(x=self.width+160, y=60)
        self.bindButtonClick(self.btn1)

        self.btn2 = Button(self.root, image=pixel, width=40, height=20, command=HardwareButtons.KEY2_PIN)
        self.btn2.place(x=self.width+160, y=116)
        self.bindButtonClick(self.btn2)

        self.btn3 = Button(self.root, image=pixel, width=40, height=20, command=HardwareButtons.KEY3_PIN)
        self.btn3.place(x=self.width+160, y=172)
        self.bindButtonClick(self.btn3)

        def key_handler(event):
            if event.keysym == "Up": self.key_press(HardwareButtons.KEY_UP_PIN)
            if event.keysym == "Down": self.key_press(HardwareButtons.KEY_DOWN_PIN)
            if event.keysym == "Left": self.key_press(HardwareButtons.KEY_LEFT_PIN)
            if event.keysym == "Right": self.key_press(HardwareButtons.KEY_RIGHT_PIN)

            if event.keysym in ("1", "KP_1"): self.key_press(HardwareButtons.KEY1_PIN)
            if event.keysym in ("2", "KP_2"): self.key_press(HardwareButtons.KEY2_PIN)
            if event.keysym in ("3", "KP_3"): self.key_press(HardwareButtons.KEY3_PIN)

            if event.keysym == "Return": self.key_press(HardwareButtons.KEY_PRESS_PIN)

        self.root.bind("<Key>", key_handler)

        self.periodic_update()
        self.root.mainloop()

    def key_press(self, key):
        self.set_input(key, 0)
        time.sleep(0.1)
        self.set_input(key, 1)

    def bindButtonClick(self, btn):
        btn.bind("<Button>", self.buttonDown)
        btn.bind("<ButtonRelease>", self.buttonUp)

    def buttonDown(self, btn):
        key = btn.widget.config('command')[-1]
        self.set_input(key, 0)

    def buttonUp(self, btn):
        key = btn.widget.config('command')[-1]
        self.set_input(key, 1)

    def load_raw_rgb(self, filename):
        if not os.path.exists(filename):
            return None
        with open(filename, "rb") as f:
            data = f.read()
        img_array = np.frombuffer(data, dtype=np.uint8)
        try:
            img_array = img_array.reshape((self.height, self.width, 3))
        except ValueError:
            return None
        return Image.fromarray(img_array, 'RGB')

    def periodic_update(self, filename="display.bmp", interval=10):
        img = self.load_raw_rgb(filename)
        if img:
            self.tkimage = ImageTk.PhotoImage(img, master=self.root)
            self.label.configure(image=self.tkimage)
            self.label.image = self.tkimage
        self.root.after(interval, lambda: self.periodic_update(filename, interval))

    def set_input(self, key, val):
        try:
            msg = f"{key} {val}\n"
            self.conn.sendall(msg.encode())
        except Exception:
            pass

    def setup_sock(self, path = 'gpio.sock'):
        if os.path.exists(path):
            os.remove(path)

        self.server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.server.bind(path)
        self.server.listen(1)

        threading.Thread(target=self.handle_sock, daemon=True).start()

    def handle_sock(self):
        while True:
            self.conn, _ = self.server.accept()


if __name__ == "__main__":
    Display()
