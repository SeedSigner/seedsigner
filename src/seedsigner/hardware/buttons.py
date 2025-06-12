import logging
from typing import List
from periphery import GPIO
import time

from seedsigner.models.singleton import Singleton
from seedsigner.models.settings import Settings
from seedsigner.models.settings_definition import SettingsConstants

logger = logging.getLogger(__name__)


class HardwareButtons(Singleton):
    # Pin names for lookup
    BUTTON_NAMES = [
        "KEY_UP", "KEY_DOWN", "KEY_LEFT", "KEY_RIGHT", "KEY_PRESS", "KEY1", "KEY2", "KEY3"
    ]

    @classmethod
    def get_instance(cls):
        # This is the only way to access the one and only instance
        if cls._instance is None:
            cls._instance = cls.__new__(cls)

            # Get the current hardware config
            hardware_config = Settings.get_instance().get_value(SettingsConstants.SETTING__HARDWARE_CONFIG)
            pins = None
            pin_mapping = SettingsConstants.ALL_HARDWARE_PIN_CONFIGS__PIN_DEFINITIONS[hardware_config]["buttons"]
            logger.info(f"pin_mapping: {pin_mapping}")
                # if config_key == hardware_config:
                #     pins = config_dict["buttons"]
                #     break
            # if pins is None:
            #     logger.error(f"Unknown hardware config: {hardware_config}")
            #     raise Exception(f"Unknown hardware config: {hardware_config}")

            # Store pin numbers as attributes for compatibility
            # for name in cls.BUTTON_NAMES:
            #     setattr(cls, f"KEY_{name.upper()}_PIN", pins[name])

            # Initialize GPIO pins with periphery
            cls._instance._gpio_pins = {}
            for name in cls.BUTTON_NAMES:
                pin = pin_mapping[name]
                cls._instance._gpio_pins[name] = GPIO("/dev/gpiochip0", pin, "in", bias="pull_up")

            cls._instance.override_ind = False

            # Track state over time so we can apply input delays/ignores as needed
            cls._instance.cur_input = None           # Track which direction or button was last pressed
            cls._instance.cur_input_started = None   # Track when that input began
            cls._instance.last_input_time = int(time.time() * 1000)  # How long has it been since the last input?
            cls._instance.first_repeat_threshold = 225  # Long-press time required before returning continuous input
            cls._instance.next_repeat_threshold = 250  # Amount of time where we no longer consider input a continuous hold

        return cls._instance


    @classmethod
    def get_instance_no_hardware(cls):
        # This is the only way to access the one and only instance
        if cls._instance is None:
            cls._instance = cls.__new__(cls)


    def wait_for(self, keys=[]) -> int:
        """
        Block execution until one of the target keys is pressed.

        Optionally override the wait by calling `trigger_override()`.
        """
        # TODO: Refactor to keep control in the Controller and not here
        from seedsigner.controller import Controller
        controller = Controller.get_instance()
        self.override_ind = False

        while True:
            if self.override_ind:
                # Break out of the wait_for without waiting for user input
                self.override_ind = False
                return HardwareButtonsConstants.OVERRIDE

            cur_time = int(time.time() * 1000)
            if cur_time - self.last_input_time > controller.screensaver_activation_ms and not controller.is_screensaver_running:
                # Start the screensaver. Will block execution until input detected.
                controller.start_screensaver()

                # We're back. Update last_input_time to now.
                self.update_last_input_time()

                # Freeze any further processing for a moment to avoid having the wakeup
                #   input register in the resumed UI.
                time.sleep(self.next_repeat_threshold / 1000.0)

                # Resume from a fresh loop
                continue

            # Check each candidate key to see if it was pressed
            for key in keys:
                if not self._gpio_pins[key].read():  # False means button is pressed (active low)
                    if self.cur_input != key:
                        self.cur_input = key
                        self.cur_input_started = int(time.time() * 1000)  # in milliseconds
                        self.last_input_time = self.cur_input_started
                        return key

                    else:
                        # Still pressing the same input
                        if cur_time - self.last_input_time > self.next_repeat_threshold:
                            # Too much time has elapsed to consider this the same
                            #   continuous input. Treat as a new separate press.
                            self.cur_input_started = cur_time
                            self.last_input_time = cur_time
                            return key

                        elif cur_time - self.cur_input_started > self.first_repeat_threshold:
                            # We're good to relay this immediately as continuous
                            #   input.
                            self.last_input_time = cur_time
                            return key

                        else:
                            # We're not yet at the first repeat threshold; triggering
                            #   a key now would be too soon and yields a bad user
                            #   experience when only a single click was intended but
                            #   a second input is processed because of race condition
                            #   against human response time to release the button.
                            # So there has to be a delay before we allow the first
                            #   continuous repeat to register. So we'll ignore this
                            #   round's input and **won't update any of our
                            #   timekeeping vars**. But once we cross the threshold,
                            #   we let the repeats fly.
                            pass

            time.sleep(0.01) # wait 10 ms to give CPU chance to do other things


    def update_last_input_time(self):
        self.last_input_time = int(time.time() * 1000)


    def trigger_override(self) -> bool:
        """ Set the override flag to break out of the current `wait_for` loop """
        self.override_ind = True


    def check_for_low(self, key: int = None, keys: List[int] = None) -> bool:
        """ Returns True if one of the target keys/key is pressed """
        if key:
            keys = [key]
        for key in keys:
            if not self._gpio_pins[key].read():  # False means button is pressed (active low)
                self.update_last_input_time()
                return True
        return False

    def has_any_input(self) -> bool:
        """ Returns True if any of the keys are pressed """
        for key in HardwareButtonsConstants.ALL_KEYS:
            if not self._gpio_pins[key].read():  # False means button is pressed (active low)
                return True
        return False

    def __del__(self):
        """Cleanup GPIO pins when object is destroyed"""
        if hasattr(self, '_gpio_pins'):
            for pin in self._gpio_pins.values():
                pin.close()


# class used as short hand for static button/channel lookup values
class HardwareButtonsConstants:
    KEY_UP = "KEY_UP"       # HW31 (BCM)
    KEY_DOWN = "KEY_DOWN"   # HW35 (BCM)
    KEY_LEFT = "KEY_LEFT"   # HW29 (BCM)
    KEY_RIGHT = "KEY_RIGHT" # HW37 (BCM)
    KEY_PRESS = "KEY_PRESS" # HW33 (BCM)

    KEY1 = "KEY1"       # HW40 (BCM)
    KEY2 = "KEY2"       # HW38 (BCM)
    KEY3 = "KEY3"       # HW36 (BCM)

    OVERRIDE = 1000

    ALL_KEYS = [
        KEY_UP,
        KEY_DOWN,
        KEY_LEFT,
        KEY_RIGHT,
        KEY_PRESS,
        KEY1,
        KEY2,
        KEY3,
    ]

    KEYS__LEFT_RIGHT_UP_DOWN = [KEY_LEFT, KEY_RIGHT, KEY_UP, KEY_DOWN]
    KEYS__ANYCLICK = [KEY_PRESS, KEY1, KEY2, KEY3]
