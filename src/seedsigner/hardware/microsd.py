import time
import base64, binascii, os, glob

from seedsigner.models.singleton import Singleton
from seedsigner.models.threads import BaseThread
from seedsigner.models.settings import Settings
#from seedsigner.views.view import MicroSDToastView
from seedsigner.gui.screens.screen import MicroSDToastScreen

class MicroSD(Singleton, BaseThread):
	
	ACTION__INSERTED = "add"
	ACTION__REMOVED = "remove"
	MOUNT_LOCATION = "/mnt/microsd/"

	MAGIC = b"psbt\xff"
	MAGIC_BASE64 = base64.b64encode(MAGIC)[:-1] # remove last byte base64 padding
	MAGIC_MAX_LENGTH = max(len(MAGIC), len(MAGIC_BASE64))
	
	@classmethod
	def get_instance(cls):
		# This is the only way to access the one and only instance
		if cls._instance is None:
			# Instantiate the one and only instance
			microsd = cls.__new__(cls)
			microsd.psbt_files = []
			microsd.find_psbt_files()
			cls._instance = microsd
			
			# explicitly call BaseThread __init__ since multiple class inheritance
			BaseThread.__init__(microsd)
	
		return cls._instance
	
	def start_detection(self):
		self.start()
	
	def run(self):
		import os
		
		FIFO_PATH = "/tmp/mdev_fifo"
		FIFO_MODE = 0o600
		action = ""
		
		# explicitly only microsd add/remove detection in seedsigner-os
		if Settings.HOSTNAME == Settings.SEEDSIGNER_OS:
			
			if os.path.exists(FIFO_PATH):
				os.remove(FIFO_PATH)
			
			os.mkfifo(FIFO_PATH, FIFO_MODE)
			
			while self.keep_running:
				with open(FIFO_PATH) as fifo:
					action = fifo.read()
					print(f"fifo message: {action}")
			
					Settings.microsd_handler(action=action)
					MicroSD.psbt_files_handler(action=action)
							
					toastscreen = MicroSDToastScreen(action=action)
					toastscreen.display()

	def psbt_files_handler(action):
		from seedsigner.controller import Controller
		controller: Controller = Controller.get_instance()
		if action == MicroSD.ACTION__INSERTED:
			controller.microsd.find_psbt_files()
		elif action == MicroSD.ACTION__REMOVED:
			controller.microsd.psbt_files = []

	def find_psbt_files(self):
		self.psbt_files = []
		# only populate psbt files from the microsd in seedsigner-os
		if Settings.HOSTNAME == Settings.SEEDSIGNER_OS:
			for filepath in sorted(glob.glob(MicroSD.MOUNT_LOCATION + '*')):
				if os.path.exists(filepath):
					with open(filepath, 'rb') as psbt_file:
						file_header = psbt_file.read(MicroSD.MAGIC_MAX_LENGTH)
			
				# binary psbt file check
				if file_header.startswith(MicroSD.MAGIC):
					self.psbt_files.append({
						"name": os.path.splitext(os.path.basename(filepath))[0],
						"filename": os.path.basename(filepath),
						"filepath": filepath,
						"type": "binary"
					})
				# base64 psbt file check
				elif file_header.startswith(MicroSD.MAGIC_BASE64):
					self.psbt_files.append({
						"name": os.path.splitext(os.path.basename(filepath))[0],
						"filename": os.path.basename(filepath),
						"filepath": filepath,
						"type": "base64"
					})
					
			self.psbt_files = sorted(self.psbt_files, key=lambda d: d['name']) 

			if len(self.psbt_files) > 0:
				print("PSBT Files Found:")
			for psbt in self.psbt_files:
				print('{filename}:{type}'.format(**psbt))
