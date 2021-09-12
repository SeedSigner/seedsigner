# import the necessary packages
from picamera.array import PiRGBArray
from picamera import PiCamera
from threading import Thread
import time
import cv2
import numpy as np

# Modified from: https://github.com/jrosebr1/imutils
class PiVideoStream:
	def __init__(self, resolution=(320, 240), framerate=32, format="bgr", **kwargs):
		# initialize the camera
		# self.camera = PiCamera(resolution=resolution, framerate=framerate, **kwargs)

		# initialize the stream
		# self.rawCapture = PiRGBArray(self.camera, size=resolution)
		# self.stream = self.camera.capture_continuous(self.rawCapture,
		# 	format=format, use_video_port=True)

		self.cap = cv2.VideoCapture(0)
		self.cap.set(3, 320)
		self.cap.set(4, 240)

		# img1 = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)


		# initialize the frame and the variable used to indicate
		# if the thread should be stopped
		self.frame = None
		self.should_stop = False
		self.is_stopped = True

	def start(self):
		# start the thread to read frames from the video stream
		t = Thread(target=self.update, args=())
		t.daemon = True
		t.start()
		self.is_stopped = False
		return self

	def update(self):
		# keep looping infinitely until the thread is stopped
		# for f in self.stream:
		while True:
			ret, frame = self.cap.read()
			self.frame = frame
			# grab the frame from the stream and clear the stream in
			# preparation for the next frame
			# self.frame = f.array
			# self.rawCapture.truncate(0)

			# if the thread indicator variable is set, stop the thread
			# and resource camera resources
			if self.should_stop:
				print("PiVideoStream: closing everything")
				# self.stream.close()
				# self.rawCapture.close()
				# self.camera.close()
				self.cap.release()
				self.should_stop = False
				self.is_stopped = True
				return

	def get_frame(self):
		ret, frame = self.cap.read()
		self.frame = frame
		return frame

	def read(self):
		# return the frame most recently read
		return self.frame

	def stop(self):
		# indicate that the thread should be stopped
		self.should_stop = True

		# Block in this thread until stopped
		while not self.is_stopped:
			pass
