import logging
from threading import Thread, Lock

logger = logging.getLogger(__name__)


class BaseThread(Thread):
    def __init__(self):
        super().__init__(daemon=True)
    
    def start(self):
        logger.debug(f"{self.__class__.__name__} STARTING")
        self.keep_running = True
        super().start()

    def stop(self):
        logger.debug(f"{self.__class__.__name__} EXITING")
        self.keep_running = False
    
    def run(self):
        while self.keep_running:
            # Do something
            raise Exception(f"Must implement run() in {self.__class__.__name__}")



class ThreadsafeCounter:
    def __init__(self, initial_value: int = 0):
        self.count = initial_value
        self._lock = Lock()
    
    @property
    def cur_count(self):
        # Reads don't require the lock
        return self.count

    def increment(self, step: int = 1):
        # Updates must be locked
        with self._lock:
            self.count += step
    
    def set_value(self, value: int):
        with self._lock:
            self.count = value


