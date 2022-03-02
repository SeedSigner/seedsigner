from pathlib import Path
from time import sleep
from threading import Thread
import os

import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk
import tkinter.font as font
# myFont = font.Font(family='Helvetica')

from pprint import pprint

from .buttons import B


class touchscreen(tk.Tk):
    def __init__(self, q):
        super().__init__()
        # Thread.__init__(self)
        print("inside touchscreen _init_")
        # self.window = tk.Tk()
        # self.window.attributes('-fullscreen', True)
        self.config(cursor="circle")
        self.latest_img = None
        self.q = q
        sleep(1)
        self.title('SeedSigner')
        if not os.getenv("NOTAPI", False):
            self.attributes("-fullscreen", True)
        else:
            self.geometry("640x480")
        
        self.myFont = font.Font(family='Helvetica', size=35, weight='bold')
        self.myFont2 = font.Font(family='Helvetica', size=20, weight='bold')

        # self.img_path = Path("/home/pi/seedsigner/src/seedsigner/resources")

        self.img_path = Path("seedsigner/resources")


    def Init(self):
        """Initialize display"""
        print("inside Init")

        self.button_state = {
            "UP": True,
            "DOWN": True,
            "LL": True,
            "RR": True,
            "PRESS": True,
            "KEY1": True,
            "KEY2": True,
            "KEY3": True
        }

        self.style = ttk.Style()
        self.style.theme_use("clam")
        self.style.configure('TButton', font=('Helvetica', 20))

        self.btn_right = Image.open(self.img_path.joinpath("buttons/RR.png"))
        self.btn_up = Image.open(self.img_path.joinpath("buttons/UP.png"))
        self.btn_left = Image.open(self.img_path.joinpath("buttons/LL.png"))
        self.btn_down = Image.open(self.img_path.joinpath("buttons/DOWN.png"))
        self.btn_select = Image.open(self.img_path.joinpath("buttons/SELECT.png"))
        self.btn_k1 = Image.open(self.img_path.joinpath("buttons/K1.png"))
        self.btn_k2 = Image.open(self.img_path.joinpath("buttons/K2.png"))
        self.btn_k3 = Image.open(self.img_path.joinpath("buttons/K3.png"))

        self.btn_right_tk = ImageTk.PhotoImage(self.btn_right)
        self.btn_up_tk = ImageTk.PhotoImage(self.btn_up)
        self.btn_left_tk = ImageTk.PhotoImage(self.btn_left)
        self.btn_down_tk = ImageTk.PhotoImage(self.btn_down)
        self.btn_select_tk = ImageTk.PhotoImage(self.btn_select)
        self.btn_k1_tk = ImageTk.PhotoImage(self.btn_k1)
        self.btn_k2_tk = ImageTk.PhotoImage(self.btn_k2)
        self.btn_k3_tk = ImageTk.PhotoImage(self.btn_k3)


        self.label = tk.Label(self)
        self.label.place(x=160, y=0)

        self.btn_KEY_PRESS = tk.Button(self, text="PRESS", image=self.btn_select_tk)
        self.btn_KEY_PRESS.place(x=160,y=400)
        # self.btn_KEY_PRESS.configure(ipady=10, ipadx=10)
        # self.btn_KEY_PRESS.configure(width=30, height=5)

        self.btn_KEY_UP = tk.Button(self, text="UP", image=self.btn_up_tk)
        self.btn_KEY_UP.place(x=0,y=0)
        # self.btn_KEY_UP.configure(width=5, height=5)

        self.btn_KEY_DOWN = tk.Button(self, text="DOWN", image=self.btn_down_tk)
        self.btn_KEY_DOWN.place(x=0,y=320)
        # self.btn_KEY_DOWN.configure(width=5, height=5)

        self.btn_KEY_LEFT = tk.Button(self, text="LL", image=self.btn_left_tk)
        self.btn_KEY_LEFT.place(x=0,y=160)
        # self.btn_KEY_LEFT.configure(width=5, height=5)

        self.btn_KEY_RIGHT = tk.Button(self, text="RR", image=self.btn_right_tk)
        self.btn_KEY_RIGHT.place(x=80,y=160)
        # self.btn_KEY_RIGHT.configure(width=5, height=5)

        self.btn_KEY_1 = tk.Button(self, text="KEY1", image=self.btn_k1_tk)
        self.btn_KEY_1.place(x=560, y=0)
        # self.btn_KEY_1.configure(width=5, height=5)

        self.btn_KEY_2 = tk.Button(self, text="KEY2", image=self.btn_k2_tk)
        self.btn_KEY_2.place(x=560, y=160)
        # self.btn_KEY_2.configure(width=5, height=5)

        self.btn_KEY_3 = tk.Button(self, text="KEY3", image=self.btn_k3_tk)
        self.btn_KEY_3.place(x=560, y=320)
        # self.btn_KEY_3.configure(width=5, height=5)

        self.btn_KEY_UP.bind("<ButtonPress>", self.update_button_state)
        self.btn_KEY_DOWN.bind("<ButtonPress>", self.update_button_state)
        self.btn_KEY_PRESS.bind("<ButtonPress>", self.update_button_state)
        self.btn_KEY_LEFT.bind("<ButtonPress>", self.update_button_state)
        self.btn_KEY_RIGHT.bind("<ButtonPress>", self.update_button_state)
        self.btn_KEY_1.bind("<ButtonPress>", self.update_button_state)
        self.btn_KEY_2.bind("<ButtonPress>", self.update_button_state)
        self.btn_KEY_3.bind("<ButtonPress>", self.update_button_state)


        # self.btn_KEY_UP.bind("<ButtonRelease>", self.update_button_state)
        # self.btn_KEY_DOWN.bind("<ButtonRelease>", self.update_button_state)
        # self.btn_KEY_PRESS.bind("<ButtonRelease>", self.update_button_state)
        # self.btn_KEY_LEFT.bind("<ButtonRelease>", self.update_button_state)
        # self.btn_KEY_RIGHT.bind("<ButtonRelease>", self.update_button_state)
        # self.btn_KEY_1.bind("<ButtonRelease>", self.update_button_state)
        # self.btn_KEY_2.bind("<ButtonRelease>", self.update_button_state)
        # self.btn_KEY_3.bind("<ButtonRelease>", self.update_button_state)


        self.refresh()
        # self.mainloop()

    def run(self):
        self.window = tk.Tk()
        self.window.attributes('-fullscreen', True)



        # self.btn_KEY_LEFT = tk.Button(self.window, text="LL")
        # self.btn_KEY_RIGHT = tk.Button(self.window, text="RR")

        # self.btn_KEY_1 = tk.Button(self.window, text="KEY1")
        # self.btn_KEY_2 = tk.Button(self.window, text="KEY2")
        # self.btn_KEY_3 = tk.Button(self.window, text="KEY3")


        # while True:
        #     r = self.q.get()
        #     print(r)
        #     self.ShowImage(r[0],r[1],r[2])
        #     self.window.update()
        #     sleep(0.05)
        
        self.refresh()
        print("after refresh")
        self.mainloop()

    def refresh(self):
        self.draw()
        self.after(2, self.refresh)

    def draw(self):
        try:
            data = self.q.get(timeout=0.25)
            print("got data")
            self.ShowImage(*data)
        except Exception as e:
            pass

    def update_button_state(self, event):
        button_name = event.widget.cget("text")
        event_type = event.type.value
        set_value = None
        # 4 is press, 5 is release
        # Active HIGH
        # set_value = True if event_type == "4" else False
        # Active LOW
        set_value = False if event_type == "4" else True

        # if set_value == True:
        #     print("releasing lock")
        #     B.release_lock = True

        print(f"Setting button {button_name} to {set_value}\n")
        self.button_state[button_name] = set_value
        pprint(self.button_state)
        self.after(5, self.reset_press, button_name, True)

    def reset_press(self, button_name, button_value):
        self.button_state[button_name] = button_value
        print("releasing lock")
        B.release_lock = True

    def ShowImage(self, Image, Xstart, Ystart):
        """Set buffer to value of Python Imaging Library image."""
        """Write display buffer to physical display"""
        print("inside ShowImage")

        Image = Image.resize(size=(400,400))
        img = ImageTk.PhotoImage(Image)
        self.latest_img = img


        self.label["image"] = self.latest_img
        # self.label.place(x=Xstart, y=Ystart)
        # sleep(1)
        print("updated")


    def reset(self):
        """Reset the display"""
        print("DO SOMETHING!")