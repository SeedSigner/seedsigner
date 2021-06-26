# External Dependencies
from multiprocessing import Queue
from threading import Timer
import time

class CameraProcess:

    def start(out_queue, in_queue):

        print("CameraProcess start")

        from imutils.video import VideoStream
        from pyzbar import pyzbar

        print("CameraProcess finish import")

        running = True

        while running == True:

            camera_on = False

            msg = []
            msg = in_queue.get()

            if msg[0] == "start":
                print("start camera!!")
                vs = VideoStream(usePiCamera=True,resolution=(512, 384),framerate=12).start()  # For Pi Camera
                time.sleep(2.0)

                msg[0] = ""
                camera_on = True

                while camera_on:
                    frame = vs.read()
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
                        camera_on = False

            elif msg[0] == "stop":
                print("stop camera!!")

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