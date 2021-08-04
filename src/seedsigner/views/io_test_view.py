# External Dependencies
from threading import Thread
from pyzbar import pyzbar
from pyzbar.pyzbar import ZBarSymbol
import time

# Internal file class dependencies
from . import View
from seedsigner.helpers import B

class IOTestView(View):

    def __init__(self) -> None:
        View.__init__(self)
        self.redraw = False
        self.redraw_complete = False
        self.qr_text = "Scan ANY QR Code"
        self.exit = False

    def display_io_test_screen(self):
        
        # display loading screen
        self.draw_modal(["Initializing I/O Test"])
        print("Initializing I/O Test")
        self.qr_text = "Scan ANY QR Code"

        try:
            self.controller.get_instance().camera.start_video_stream_mode()
            t = Thread(target=self.qr_loop)
            t.start()
        except:
            self.qr_text = "No Camera"
            self.controller.get_instance().camera.stop_video_stream_mode()

        while True:

            self.draw_io_screen()

            input = self.buttons.wait_for([B.KEY_UP, B.KEY_DOWN, B.KEY_PRESS, B.KEY_RIGHT, B.KEY_LEFT, B.KEY1, B.KEY2, B.KEY3], False)
            if input == B.KEY_UP:
                ret_val = self.up_button()
            elif input == B.KEY_DOWN:
                ret_val = self.down_button()
            elif input == B.KEY_RIGHT:
                ret_val = self.right_button()
            elif input == B.KEY_LEFT:
                ret_val = self.left_button()
            elif input == B.KEY_PRESS:
                ret_val = self.press_button()
            elif input == B.KEY1:
                ret_val = self.a_button()
            elif input == B.KEY2:
                ret_val = self.b_button()
            elif input == B.KEY3:
                ret_val = self.c_button()
                return True

    def qr_loop(self):
        while True:
            frame = self.controller.get_instance().camera.read_video_stream()
            if frame is not None:
                barcodes = pyzbar.decode(frame, symbols=[ZBarSymbol.QRCODE])
                if len(barcodes) > 0:
                    self.draw_scan_detected()

            time.sleep(0.05)

            if self.controller.get_instance().camera._video_stream is None:
                break

            if self.exit == True:
                break

    def draw_io_screen(self):
        self.redraw_complete = False
        self.redraw = False
        self.draw.rectangle((0,0,View.canvas_width, View.canvas_height), outline=0, fill=0)
        self.draw.text((45, 5), "Input/Output Check:", fill=View.color, font=View.IMPACT18)
        self.draw.polygon([(61, 89), (80, 46), (99, 89)], outline=View.color, fill=0)
        self.draw.polygon([(51, 100), (8, 119), (51, 138)], outline=View.color, fill=0)
        self.draw.polygon([(109, 100), (152, 119), (109, 138)], outline=View.color, fill=0)
        self.draw.polygon([(61, 151), (80, 193), (99, 151)], outline=View.color, fill=0)
        self.draw.ellipse([(61, 99), (99, 141)], outline=View.color, fill=0)
        self.draw.ellipse([(198, 40), (238, 80)], outline=View.color, fill=0)
        self.draw.ellipse([(198, 95), (238, 135)], outline=View.color, fill=0)
        self.draw.text((200, 160), "EXIT", fill=View.color, font=View.IMPACT18)
        self.draw.rectangle((30, 205, 210, 235), outline=View.color, fill="BLACK")
        tw, th = self.draw.textsize(self.qr_text, font=View.IMPACT22)
        self.draw.text(((240 - tw) / 2, 205), self.qr_text, fill=View.color, font=View.IMPACT22)
        View.DispShowImage()
        self.redraw_complete = True

    def a_button(self):
        if self.redraw == False and self.redraw_complete == True:
            self.draw.ellipse([(198, 40), (238, 80)], outline=View.color, fill=View.color)
            View.DispShowImage()
            self.redraw = True

    def b_button(self):
        if self.redraw == False and self.redraw_complete == True:
            self.draw.ellipse([(198, 95), (238, 135)], outline=View.color, fill=View.color)
            View.DispShowImage()
            self.redraw = True

    def c_button(self):
        self.exit = True
        self.controller.get_instance().camera.stop_video_stream_mode()
        return

    def up_button(self):
        if self.redraw == False and self.redraw_complete == True:
            self.draw.polygon([(61, 89), (80, 46), (99, 89)], outline=View.color, fill=View.color)
            View.DispShowImage()
            self.redraw = True
        
    def down_button(self):
        if self.redraw == False and self.redraw_complete == True:
            self.draw.polygon([(61, 151), (80, 193), (99, 151)], outline=View.color, fill=View.color)
            View.DispShowImage()
            self.redraw = True
        
    def left_button(self):
        if self.redraw == False and self.redraw_complete == True:
            self.draw.polygon([(51, 100), (8, 119), (51, 138)], outline=View.color, fill=View.color)
            View.DispShowImage()
            self.redraw = True
        
    def right_button(self):
        if self.redraw == False and self.redraw_complete == True:
            self.draw.polygon([(109, 100), (152, 119), (109, 138)], outline=View.color, fill=View.color)
            View.DispShowImage()
            self.redraw = True
        
    def press_button(self):
        if self.redraw == False and self.redraw_complete == True:
            self.draw.ellipse([(61, 99), (99, 141)], outline=View.color, fill=View.color)
            View.DispShowImage()
            self.redraw = True
    
    def draw_scan_detected(self):
        self.qr_text = "QR Scanned"
        if self.redraw == False and self.redraw_complete == True:
            self.draw.rectangle((30, 205, 210, 235), outline=View.color, fill=View.color)
            tw, th = self.draw.textsize(self.qr_text, font=View.IMPACT22)
            self.draw.text(((240 - tw) / 2, 205), self.qr_text, fill="BLACK", font=View.IMPACT22)
            View.DispShowImage()
            self.redraw = True
        