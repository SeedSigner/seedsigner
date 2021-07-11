# External Dependencies
from multiprocessing import Queue
from threading import Timer
import time

class CameraProcess:

    def start(out_queue, in_queue):
        print("CameraProcess start")

        import_start_time = int(time.time() * 1000)
        from .pivideostream import PiVideoStream
        from pyzbar import pyzbar
        import_end_time = int(time.time() * 1000)

        print(f"CameraProcess finish import: {import_end_time - import_start_time}ms")

        is_running = True

        while is_running:
            is_camera_on = False

            msg = []
            msg = in_queue.get()

            if msg[0] == "start":
                print("start camera!!")
                vs = PiVideoStream(resolution=(512, 384),framerate=12).start()  # For Pi Camera

                msg[0] = ""
                is_camera_on = True

                while is_camera_on:
                    frame = vs.read()

                    if frame is None:
                        # Camera isn't returning data yet
                        time.sleep(0.125)
                        continue

                    barcodes = pyzbar.decode(frame)
                    for barcode in barcodes:
                        data = barcode.data.decode("utf-8")
                        out_queue.put([data])
                        break
                    if len(barcodes) == 0:
                        out_queue.put(["nodata"])

                    try:
                        msg = in_queue.get(False)
                    except:
                        pass

                    if msg[0] == "stop":
                        vs.stop()
                        is_camera_on = False

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
        self.is_is_running = False
        self.start()

    def _run(self):
        self.is_is_running = False
        self.start()
        self.function(*self.args, **self.kwargs)

    def start(self):
        if not self.is_is_running:
            self._timer = Timer(self.interval, self._run)
            self._timer.start()
            self.is_is_running = True

    def stop(self):
        self._timer.cancel()
        self.is_is_running = False