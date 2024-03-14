import copy
import logging
from threading import Event, Thread, Lock
from typing import Generic, TypeVar

logger = logging.getLogger(__name__)


T = TypeVar("T")



class BaseThread(Thread):
    def __init__(self, event: Event = None):
        super().__init__(daemon=True)
        if event is None:
            # Have to instantiate a default Event here; if we do it as a default value
            # for the kwarg, we inadvertently end up re-using the same Event instance.
            event = Event()
        self.event = event


    def stop(self):
        # Set the thread's Event; the thread's execution loop will exit on its next
        # iteration.
        self.event.set()


    def run(self):
        """
            while not self.event.is_set():
                # Do something
        """
        raise Exception(f"Must implement run() in {self.__class__.__name__}")



class ThreadsafeVar(Generic[T]):
    def __init__(self, initial_value: T = None):
        self.data: T = initial_value
        self._lock = Lock()


    @property
    def cur_value(self) -> T:
        # Reads don't require the lock
        return copy.copy(self.data)


    def set_value(self, value: T):
        # Updates must be locked
        with self._lock:
            self.data = value



class ThreadsafeCounter(ThreadsafeVar[int]):
    def __init__(self, initial_value: int = 0):
        # Must initialize to some starting int value
        super().__init__(initial_value)


    def increment(self, step: int = 1):
        # Updates must be locked
        with self._lock:
            self.data += step
