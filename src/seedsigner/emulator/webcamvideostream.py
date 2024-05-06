
from threading import Thread
import time
import cv2


class WebcamVideoStream:
	def __init__(self, resolution=(320, 240), framerate=32, format="bgr", **kwargs):
		# initialize the camera
		self.camera = cv2.VideoCapture(0)
		self.set_resolution(resolution)
				
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

	def hasCamera(self):
		return 	self.camera.isOpened()

	def update(self):

		if self.hasCamera():

			# keep looping infinitely until the thread is stopped
			while(not self.should_stop):
				# grab the frame from the stream and clear the stream in
				# preparation for the next frame
				ret, stream = self.camera.read()
				stream = cv2.resize(stream, (240,240))
				stream = cv2.cvtColor(stream,cv2.COLOR_BGR2RGB)
				time.sleep(0.05)
				self.frame = stream

			self.is_stopped = True
			self.should_stop = False
			return

		else:
			self.is_stopped = True
			self.should_stop = False
			return



	def read(self):
		return self.frame
	
	def single_frame():
		cap = cv2.VideoCapture(0)
		ret, frame = cap.read()
		return frame

	def stop(self):
		# indicate that the thread should be stopped
		self.should_stop = True

		# Block in this thread until stopped
		while not self.is_stopped:
			pass

	def set_resolution(self, resolution):
		self.camera.set(3, resolution[0])
		self.camera.set(4, resolution[1])	
