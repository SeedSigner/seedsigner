# Forked and modifed from @ltcmweb
# https://github.com/ltcmweb/seedsigner/blob/3d321d50d488919d94fe407f538d8e655ba13eb4/src/seedsigner/hardware/buttons.py#L198

import threading
import socket


class MockGPIO:
    LOW = 0
    HIGH = 1
    BOARD = 10
    IN = 1
    PUD_UP = 22
    RPI_INFO = {"P1_REVISION": 3}

    def __init__(self):
        self._states = {}
        self.lock = threading.Lock()
        self._initialized = False

    def setmode(self, mode):
        pass

    def setup(self, pin, mode, pull_up_down=None):
        if not self._initialized:
            self.init()

    def init(self, socket_path="gpio.sock"):
        if self._initialized:
            return
        self._initialized = True
        self._states = {}
        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.sock.connect(socket_path)
        threading.Thread(target=self._read_loop, daemon=True).start()

    def _read_loop(self):
        f = self.sock.makefile("r")
        while True:
            line = f.readline()
            if not line:
                break
            try:
                pin, val = line.strip().split()
                with self.lock:
                    self._states[int(pin)] = int(val)
            except Exception:
                pass

    def input(self, pin):
        with self.lock:
            return self._states.get(pin, self.HIGH)
