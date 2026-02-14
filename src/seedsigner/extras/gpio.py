import socket
import threading
from typing import Final

class _GPIO:
    LOW: Final = 0
    HIGH: Final = 1

    # Fake constants
    BOARD: Final = 10
    IN: Final = 1
    PUD_UP: Final = 22
    RPI_INFO: Final = {"P1_REVISION": 3}

    def setmode(self, a: int):
        pass

    def setup(self, a: int, b: int, *,  pull_up_down: int):
        pass

    def init(self, socket_path="gpio.sock"):
        self._states = {}
        self.lock = threading.Lock()
        self.socket_path = socket_path

        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.sock.connect(self.socket_path)

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


GPIO = _GPIO()
