import time
import os

from seedsigner.models.singleton import Singleton
from seedsigner.models.threads import BaseThread
from seedsigner.models.settings import Settings

class MicroSD(Singleton, BaseThread):
    
    MOUNT_POINT = "/mnt/microsd"
    FIFO_PATH = "/tmp/mdev_fifo"
    FIFO_MODE = 0o600
    ACTION__INSERTED = "add"
    ACTION__REMOVED = "remove"
    warn_to_remove = True

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

    def is_inserted(self):
        # could only be False in seedsigner-os, else True
        if Settings.HOSTNAME == Settings.SEEDSIGNER_OS:
            return os.path.exists(self.MOUNT_POINT)
        else:
            return True


    def run(self):
        action = ""
        
        # explicitly only microsd add/remove detection in seedsigner-os
        if Settings.HOSTNAME == Settings.SEEDSIGNER_OS:

            # at start-up, get current status and inform Settings
            if self.is_inserted():
                Settings.microsd_handler(self.ACTION__INSERTED)
            else:
                Settings.microsd_handler(self.ACTION__REMOVED)

            if os.path.exists(self.FIFO_PATH):
                os.remove(self.FIFO_PATH)
            
            os.mkfifo(self.FIFO_PATH, self.FIFO_MODE)

            while self.keep_running:
                with open(self.FIFO_PATH) as fifo:
                    action = fifo.read()
                    print(f"fifo message: {action}")
            
                    Settings.microsd_handler(action=action)

                    if action == self.ACTION__INSERTED:
                        self.warn_to_remove = True
