######################################################################
#  Seedsigner desktop display driver and button emulator
#
#  by: @EnteroPositivo (Twitter, Gmail, GitHub)



import time

from seedsigner.emulator.virtualGPIO import GPIO
from seedsigner.hardware.buttons import HardwareButtons

from tkinter import *
import tkinter as tk


from PIL import ImageTk

import threading
import os

EMULATOR_VERSION = '0.5'
        

class desktopDisplay(threading.Thread):
    """class for desktop display."""
    root=0
    def __init__(self):
        self.width = 240
        self.height = 240

        # Multithreading
        threading.Thread.__init__(self)
        self.start()

    def callback(self):
        self.root.quit()
        self.root.destroy()
        # terminate the main thread forcefully
        pid = os.getpid()
        os.kill(pid,9)

    def run(self):
        """run thread"""    
        self.root = tk.Tk()
        
        from seedsigner.controller import Controller
        controller = Controller.get_instance()
        title= "SeedSigner Emulator v"+EMULATOR_VERSION+ " / "+controller.VERSION;

        print("*****************************************************");
        print(title);
        print("https://github.com/enteropositivo/seedsigner-emulator");
        print("*****************************************************");

        self.root.title(title)

        self.root.protocol("WM_DELETE_WINDOW", self.callback)
        self.root.geometry("480x260+240+240")
        self.root.configure(bg='orange')
        self.root.iconphoto(False, tk.PhotoImage(file='seedsigner/resources/icons/emulator_icon.png'))
        # ....


        self.label=Label(self.root)
        self.label.pack()

        self.joystick=Frame(self.root)
        self.joystick.pack()
        self.joystick.place(x=20, y=85)
        self.joystick.configure(bg='orange')
        
        pixel = tk.PhotoImage(width=1, height=1)
        

        self.btnL = Button(self.joystick, image=pixel,  width=20, height=20,  command = HardwareButtons.KEY_LEFT_PIN, bg='white')
        self.btnL.grid(row=1, column=0)
        self.bindButtonClick(self.btnL)

        self.btnR = Button(self.joystick, image=pixel,  width=20, height=20, command = HardwareButtons.KEY_RIGHT_PIN, bg='white')
        self.btnR.grid(row=1, column=2)
        self.bindButtonClick(self.btnR)

        self.btnC = Button(self.joystick, image=pixel,  width=20, height=20, command = HardwareButtons.KEY_PRESS_PIN)
        self.btnC.grid(row=1, column=1)
        self.bindButtonClick(self.btnC)

        self.btnU = Button(self.joystick, image=pixel,  width=20, height=20, command = HardwareButtons.KEY_UP_PIN, bg='white')
        self.btnU.grid(row=0, column=1)
        self.bindButtonClick(self.btnU)

        self.btnD = Button(self.joystick, image=pixel,  width=20, height=20, command = HardwareButtons.KEY_DOWN_PIN, bg='white')
        self.btnD.grid(row=2, column=1)
        self.bindButtonClick(self.btnD)

        self.btn1 = Button(self.root, image=pixel,  width=40, height=20,  command = HardwareButtons.KEY1_PIN, bg='white')
        self.btn1.place(x=400, y=60)
        self.bindButtonClick(self.btn1)

        self.btn2 = Button(self.root, image=pixel,  width=40, height=20,  command = HardwareButtons.KEY2_PIN, bg='white')
        self.btn2.place(x=400, y=116)
        self.bindButtonClick(self.btn2)

        self.btn3 = Button(self.root, image=pixel,  width=40, height=20,  command = HardwareButtons.KEY3_PIN, bg='white')
        self.btn3.place(x=400, y=172)
        self.bindButtonClick(self.btn3)

        
        def key_handler(event):
            
            if(event.keysym=="Up"): GPIO.set_input(HardwareButtons.KEY_UP_PIN, GPIO.HIGH)
            if(event.keysym=="Down"): GPIO.set_input(HardwareButtons.KEY_DOWN_PIN, GPIO.HIGH)
            if(event.keysym=="Left"): GPIO.set_input(HardwareButtons.KEY_LEFT_PIN, GPIO.HIGH)
            if(event.keysym=="Right"): GPIO.set_input(HardwareButtons.KEY_RIGHT_PIN, GPIO.HIGH)

            if(event.keysym in ("1", "KP_1") ): GPIO.set_input(HardwareButtons.KEY1_PIN, GPIO.HIGH)
            if(event.keysym in ("2", "KP_2") ): GPIO.set_input(HardwareButtons.KEY2_PIN, GPIO.HIGH)
            if(event.keysym in ("3", "KP_3") ): GPIO.set_input(HardwareButtons.KEY3_PIN, GPIO.HIGH)

            if(event.keysym=="Return"): GPIO.set_input(HardwareButtons.KEY_PRESS_PIN, GPIO.HIGH)

        self.root.bind("<Key>", key_handler)

        self.root.resizable(width = True, height = True)
        self.root.mainloop()
     
 
    def bindButtonClick(self, objBtn):
        objBtn.bind("<Button>", self.buttonDown)
        objBtn.bind("<ButtonRelease>", self.buttonUp)

    def buttonDown(self, objBtn):
        gpioID = (objBtn.widget.config('command')[-1])
        GPIO.set_input(gpioID, GPIO.HIGH)

    def buttonUp(self, objBtn):
        gpioID = (objBtn.widget.config('command')[-1])
        GPIO.set_input(gpioID, GPIO.LOW)   

    def setGPIO(self, pin):
        GPIO.fire_raise_event(pin)

    def ShowImage(self,Image2,Xstart,Ystart):
        while(self.root==0): time.sleep(0.1)
        imwidth, imheight = Image2.size
        if imwidth != self.width or imheight != self.height:
            raise ValueError('Image must be same dimensions as display \
                ({0}x{1}).' .format(self.width, self.height))

        self.tkimage= ImageTk.PhotoImage(Image2, master=self.root)
        self.label.configure(image=self.tkimage)
        self.label.image=self.tkimage
        self.label.place(x=125, y=10)
       
        
    def clear(self):
        """Clear contents of image buffer"""
 