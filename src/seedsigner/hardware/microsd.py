import logging
import os
import time

from seedsigner.models.singleton import Singleton
from seedsigner.models.threads import BaseThread

logger = logging.getLogger(__name__)


class MicroSD(Singleton, BaseThread):
    MOUNT_POINT = "/mnt/microsd"
    FIFO_PATH = "/tmp/mdev_fifo"
    FIFO_MODE = 0o600
    ACTION__INSERTED = "add"
    ACTION__REMOVED = "remove"


    @classmethod
    def get_instance(cls):
        # This is the only way to access the one and only instance
        if cls._instance is None:
            # Instantiate the one and only instance
            microsd = cls.__new__(cls)
            cls._instance = microsd

            # explicitly call BaseThread __init__ since multiple class inheritance
            BaseThread.__init__(microsd)

            # Latest hotplug event from mdev FIFO, if any. None until the first event.
            # Used so UI can react as soon as the card is pulled, without waiting for
            # the mount point to disappear (unmount can lag several seconds).
            microsd._hotplug_inserted = None

        return cls._instance


    @property
    def is_inserted(self):
        from seedsigner.models.settings import Settings  # Import here to avoid circular import issues

        if Settings.HOSTNAME == Settings.SEEDSIGNER_OS:
            # Prefer the most recent hotplug event when available so callers (boot gate,
            # toasts) agree on timing. Fall back to the mount point before any event.
            if self._hotplug_inserted is not None:
                return self._hotplug_inserted
            return os.path.exists(MicroSD.MOUNT_POINT)
        else:
            # Always True for Raspi OS
            return True


    def start_detection(self):
        self.start()


    def run(self):
        from seedsigner.controller import Controller
        from seedsigner.gui.toast import SDCardStateChangeToastManagerThread
        from seedsigner.models.settings import Settings  # Import here to avoid circular import issues
        action = ""

        # explicitly only microsd add/remove detection in seedsigner-os
        if Settings.HOSTNAME == Settings.SEEDSIGNER_OS:

            # at start-up, get current status and inform Settings
            Settings.handle_microsd_state_change(
                action=MicroSD.ACTION__INSERTED if self.is_inserted else MicroSD.ACTION__REMOVED
            )

            if os.path.exists(self.FIFO_PATH):
                os.remove(self.FIFO_PATH)

            os.mkfifo(self.FIFO_PATH, self.FIFO_MODE)

            while self.keep_running:
                with open(self.FIFO_PATH) as fifo:
                    action = fifo.read().strip()
                    logger.info(f"fifo message: {action}")

                    if action == MicroSD.ACTION__INSERTED:
                        self._hotplug_inserted = True
                    elif action == MicroSD.ACTION__REMOVED:
                        self._hotplug_inserted = False

                    Settings.handle_microsd_state_change(action=action)
                    Controller.get_instance().activate_toast(SDCardStateChangeToastManagerThread(action=action))

                time.sleep(0.1)
