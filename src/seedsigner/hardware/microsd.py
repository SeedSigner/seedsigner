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
		import socket, os, time
		
		# explicitly only microsd add/remove detection in seedsigner-os
		if Settings.HOSTNAME == Settings.SEEDSIGNER_OS:
			
			if os.path.exists("/tmp/mdev_socket"):
				os.remove("/tmp/mdev_socket")
			
			server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
			server.bind("/tmp/mdev_socket")
			while self.keep_running:
				
				server.listen(1)
				conn, addr = server.accept()
				data = conn.recv(1000) # 1000 bytes limit
				action = ""
				mount_dir = ""
				if data:
					msg = data.decode("utf-8").strip().split("|")
					action = msg[0]
					print(f"socket message: {action}")
				conn.close()
				
				Settings.microsd_handler(action=action)
				
				toastscreen = MicroSDToastScreen(action=action)
				toastscreen.display()