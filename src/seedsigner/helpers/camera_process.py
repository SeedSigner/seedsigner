# External Dependencies
from multiprocessing import Queue
from threading import Timer
import io
import time
import traceback
import operator


class CameraProcess():

    def scan_qr_code(in_queue, out_queue):
        from pyzbar import pyzbar
        from .pivideostream import PiVideoStream
        try:
            print("Instantiate PiVideoStream start")
            start_time = int(time.time() * 1000)
            video_stream = PiVideoStream(resolution=(512, 384),framerate=12)
            end_time = int(time.time() * 1000)
            print(f"Instantiate PiVideoStream finish: {end_time - start_time}ms")

            video_stream.start()

            msg = [""]

            while True:
                # Loop the reader until we get a result or receive "stop"
                frame = video_stream.read()

                if frame is None:
                    # Camera isn't returning data yet
                    time.sleep(0.1)
                    continue

                barcodes = pyzbar.decode(frame)
                for barcode in barcodes:
                    data = barcode.data.decode("utf-8")
                    out_queue.put([data])
                    break
                if len(barcodes) == 0:
                    out_queue.put(["nodata"])

                try:
                    # Get any updates from the message queue, but don't wait
                    msg = in_queue.get(block=False)
                except:
                    pass

                if msg[0] == "stop":
                    break
        finally:
            try:
                video_stream.stop()
            except:
                pass



    def capture_single_frame(in_queue, out_queue):
        from PIL import Image
        import picamera

        print("Instantiate PiCamera start")
        start_time = int(time.time() * 1000)
        camera = picamera.PiCamera(resolution=(720, 480), framerate=8)
        end_time = int(time.time() * 1000)
        print(f"Instantiate PiCamera finish: {end_time - start_time}ms")

        try:
            print("camera ready")
            out_queue.put(["ready"])

            # Wait for the "click" command
            while True:
                try:
                    msg = in_queue.get(block=False)
                    break
                except:
                    time.sleep(0.1)

            if msg[0] == "stop":
                print("Received 'stop'")
                return

            elif msg[0] == "click":
                print("Received 'click'")

                # Wait for the automatic gain control to settle
                time.sleep(0.25)
                # Now fix the values
                camera.shutter_speed = camera.exposure_speed
                camera.exposure_mode = 'off'
                g = camera.awb_gains
                camera.awb_mode = 'off'
                camera.awb_gains = g

                stream = io.BytesIO()
                camera.capture(stream, format='jpeg')

                # "Rewind" the stream to the beginning so we can read its content
                stream.seek(0)

                out_queue.put([Image.open(stream)])

        except Exception as e:
            traceback.print_exc()

        finally:
            camera.close()
            print("Cleaned up capture_single_frame")


    @classmethod
    def start(cls, out_queue, in_queue):
        print("CameraProcess start")
        start_time = int(time.time() * 1000)
        from .pivideostream import PiVideoStream
        end_time = int(time.time() * 1000)
        print(f"CameraProcess finish import: {end_time - start_time}ms")

        is_running = True

        while is_running:
            is_camera_on = False

            msg = []
            msg = in_queue.get()

            if msg[0] == "start":
                CameraProcess.scan_qr_code(in_queue, out_queue)

            elif msg[0] == "single_frame":
                CameraProcess.capture_single_frame(in_queue, out_queue)

            elif msg[0] == "stop":
                print("stop camera!!")

            time.sleep(0.25)    # No need to poll all that frequently



class CameraPoll(object):

    def __init__(self, interval, function, *args, **kwargs):
        self._timer     = None
        self.interval   = interval
        self.function   = function
        self.args       = args
        self.kwargs     = kwargs
        self.is_running = False
        self.start()

    def _run(self):
        self.is_running = False
        self.start()
        self.function(*self.args, **self.kwargs)

    def start(self):
        if not self.is_running:
            self._timer = Timer(self.interval, self._run)
            self._timer.start()
            self.is_running = True

    def stop(self):
        self._timer.cancel()
        self.is_running = False