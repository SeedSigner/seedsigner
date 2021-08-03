import io
import numpy

from picamera import PiCamera
from PIL import Image
from seedsigner.helpers import PiVideoStream, Singleton



class Camera(Singleton):
    _video_stream = None
    _picamera = None


    def start_video_stream_mode(self, resolution=(512, 384), framerate=12, format="bgr"):
        if self._video_stream is not None:
            self.stop_video_stream_mode()

        self._video_stream = PiVideoStream(resolution=resolution,framerate=framerate, format=format)
        self._video_stream.start()


    def read_video_stream(self, as_image=False):
        if not self._video_stream:
            raise Exception("Must call start_video_stream first.")
        frame = self._video_stream.read()
        if not as_image:
            return frame
        else:
            if frame is not None:
                return Image.fromarray(frame.astype('uint8'), 'RGB').rotate(90)
        return None


    def stop_video_stream_mode(self):
        if self._video_stream is not None:
            self._video_stream.stop()
            self._video_stream = None


    def start_single_frame_mode(self, resolution=(720, 480)):
        if self._video_stream is not None:
            self.stop_video_stream_mode()
        if self._picamera is not None:
            self._picamera.close()

        self._picamera = PiCamera(resolution=resolution, framerate=24)
        self._picamera.start_preview()


    def capture_frame(self):
        if self._picamera is None:
            raise Exception("Must call start_single_frame_mode first.")

        # Set auto-exposure values
        self._picamera.shutter_speed = self._picamera.exposure_speed
        self._picamera.exposure_mode = 'off'
        g = self._picamera.awb_gains
        self._picamera.awb_mode = 'off'
        self._picamera.awb_gains = g

        """
        When outputting to unencoded formats, the camera rounds the requested resolution.
        The horizontal resolution is rounded up to the nearest multiple of 32 pixels,
        while the vertical resolution is rounded up to the nearest multiple of 16 pixels. 
        """
        # resolution = self._picamera.resolution
        # if resolution.width % 32 == 0:
        #     raw_width = resolution.width
        # else:
        #     raw_width = resolution.width - (resolution.width % 32) + 32
            
        # if resolution.height % 16 == 0:
        #     raw_height = resolution.height
        # else:
        #     raw_height = resolution.height + 16

        # print(resolution)
        # print(raw_width, raw_height)
        # np_array = numpy.empty((raw_width, raw_height, 3), dtype=numpy.uint8)
        # self._picamera.capture(np_array, format='rgb')

        # np_array.reshape((raw_width, raw_height, 3))

        # return Image.fromarray(np_array[:resolution.width, :resolution.height, :].astype('uint8'), 'RGB')

        stream = io.BytesIO()
        self._picamera.capture(stream, format='jpeg')

        # "Rewind" the stream to the beginning so we can read its content
        stream.seek(0)
        return Image.open(stream)


    def stop_single_frame_mode(self):
        if self._picamera is not None:
            self._picamera.close()
            self._picamera = None

