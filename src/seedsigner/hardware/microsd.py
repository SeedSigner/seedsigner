import time

from seedsigner.models.singleton import Singleton
from seedsigner.models.threads import BaseThread
from seedsigner.models.settings import Settings
#from seedsigner.views.view import MicroSDToastView
from seedsigner.gui.screens.screen import MicroSDToastScreen

class MicroSD(Singleton, BaseThread):
	
	ACTION__INSERTED = "add"
	ACTION__REMOVED = "remove"

	settings_handler = None
	
	@classmethod
	def get_instance(cls):
		# This is the only way to access the one and only instance
		if cls._instance is None:
			# Instantiate the one and only instance
			microsd = cls.__new__(cls)
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
							
					toastscreen = MicroSDToastScreen(action=action)
					toastscreen.display()
