import time

from seedsigner.models.singleton import Singleton
from seedsigner.models.threads import BaseThread

class MicroSD(Singleton, BaseThread):
	
	ui_handler = None
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
		
		from seedsigner.controller import Controller
		
		# explicitly only microsd add/remove detection in seedsigner-os
		if Controller.HOSTNAME == Controller.SEEDSIGNER_OS:
			
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
					msg = data.decode("utf-8").strip().split(" ")
					action = msg[0]
					mount_dir = msg[1]
					print(f"socket message: {action} {mount_dir}")
				conn.close()
					
				if self.settings_handler:
					self.settings_handler(action, mount_dir)
					
				if self.ui_handler:
					self.ui_handler(action, mount_dir)