import logging
from typing import List
import RPi.GPIO as GPIO
import time

from seedsigner.models.singleton import Singleton

logger = logging.getLogger(__name__)


class HardwareButtons(Singleton):
    if GPIO.RPI_INFO['P1_REVISION'] == 3: #This indicates that we have revision 3 GPIO
        logger.info("Detected 40pin GPIO (Rasbperry Pi 2 and above)")
        KEY_UP_PIN = 31
        KEY_DOWN_PIN = 35
        KEY_LEFT_PIN = 29
        KEY_RIGHT_PIN = 37
        KEY_PRESS_PIN = 33

        KEY1_PIN = 40
        KEY2_PIN = 38
        KEY3_PIN = 36

    else:
        logger.info("Assuming 26 Pin GPIO (Raspberry P1 1)")
        KEY_UP_PIN = 5
        KEY_DOWN_PIN = 11
        KEY_LEFT_PIN = 3
        KEY_RIGHT_PIN = 15
        KEY_PRESS_PIN = 7

        KEY1_PIN = 16
        KEY2_PIN = 12
        KEY3_PIN = 8


    @classmethod
    def get_instance(cls):
        # This is the only way to access the one and only instance
        if cls._instance is None:
            cls._instance = cls.__new__(cls)

            #init GPIO
            GPIO.setmode(GPIO.BOARD)
            GPIO.setup(HardwareButtons.KEY_UP_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)    # Input with pull-up
            GPIO.setup(HardwareButtons.KEY_DOWN_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)  # Input with pull-up
            GPIO.setup(HardwareButtons.KEY_LEFT_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)  # Input with pull-up
            GPIO.setup(HardwareButtons.KEY_RIGHT_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP) # Input with pull-up
            GPIO.setup(HardwareButtons.KEY_PRESS_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP) # Input with pull-up
            GPIO.setup(HardwareButtons.KEY1_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)      # Input with pull-up
            GPIO.setup(HardwareButtons.KEY2_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)      # Input with pull-up
            GPIO.setup(HardwareButtons.KEY3_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)      # Input with pull-up

            cls._instance.GPIO = GPIO
            cls._instance.override_ind = False

            # Track state over time so we can apply input delays/ignores as needed
            cls._instance.cur_input = None           # Track which direction or button was last pressed
            cls._instance.cur_input_started = None   # Track when that input began
            cls._instance.last_input_time = int(time.time() * 1000)  # How long has it been since the last input?
            cls._instance.first_repeat_threshold = 225  # Long-press time required before returning continuous input
            cls._instance.next_repeat_threshold = 250  # Amount of time where we no longer consider input a continuous hold
            
            # Long press logic state
            cls._instance.long_press_threshold = 1000 # milliseconds to trigger a long press event
            cls._instance.long_press_fired = False    # Has the long press event already fired for the current press?

        return cls._instance


    @classmethod
    def get_instance_no_hardware(cls):
        # This is the only way to access the one and only instance
        if cls._instance is None:
            cls._instance = cls.__new__(cls)


    def wait_for(self, keys=[], check_release=True) -> int:
        """
        Block execution until one of the target keys is pressed.

        Optionally override the wait by calling `trigger_override()`.
        
        Supports detection of KEY_PRESS_LONG if included in the 'keys' argument.
        If KEY_PRESS_LONG is requested, the standard KEY_PRESS event for that button
        will be deferred until release (trailing edge) to distinguish it from the hold.
        """
        # TODO: Refactor to keep control in the Controller and not here
        from seedsigner.controller import Controller
        controller = Controller.get_instance()
        self.override_ind = False

        while True:
            # 1. Handle External Overrides (e.g. from tests or other threads)
            if self.override_ind:
                # Break out of the wait_for without waiting for user input
                self.override_ind = False
                return HardwareButtonsConstants.OVERRIDE

            # 2. Handle Screensaver Activation
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

            # 3. Determine which Physical Pins to scan based on requested 'keys'
            #    This maps virtual keys (KEY_PRESS_LONG) to their physical counterparts.
            pins_to_scan = set()
            for k in keys:
                if k == HardwareButtonsConstants.KEY_PRESS_LONG:
                    pins_to_scan.add(HardwareButtonsConstants.KEY_PRESS_PIN)
                elif k != HardwareButtonsConstants.OVERRIDE:
                    pins_to_scan.add(k)

            # 4. Scan the Physical Pins
            for pin in pins_to_scan:
                if self.GPIO.input(pin) == GPIO.LOW:
                    # --- PIN IS ACTIVE (PRESSED DOWN) ---

                    if self.cur_input != pin:
                        # A. New Press Detected
                        self.cur_input = pin
                        self.cur_input_started = cur_time
                        self.last_input_time = self.cur_input_started
                        self.long_press_fired = False

                        # Decision: Return immediately or Defer?
                        if pin == HardwareButtonsConstants.KEY_PRESS_PIN and HardwareButtonsConstants.KEY_PRESS_LONG in keys:
                            # DEFER: We need to wait to see if this becomes a Long Press
                            pass 
                        elif pin in keys:
                            # IMMEDIATE: Directional keys or standard buttons usually fire on contact
                            return pin

                    else:
                        # B. Holding the Key
                        if pin == HardwareButtonsConstants.KEY_PRESS_PIN and HardwareButtonsConstants.KEY_PRESS_LONG in keys:
                            # Logic for Long Press Detection
                            if not self.long_press_fired and (cur_time - self.cur_input_started > self.long_press_threshold):
                                # Threshold reached! Fire the Long Press event.
                                self.long_press_fired = True
                                self.last_input_time = cur_time # Update activity timer
                                return HardwareButtonsConstants.KEY_PRESS_LONG
                        
                        else:
                            # Logic for Standard Repeat (Scrolling)
                            # Used mostly for Directional Keys (Up/Down/Left/Right)
                            if cur_time - self.last_input_time > self.next_repeat_threshold:
                                # Too much time has elapsed to consider this the same
                                #   continuous input. Treat as a new separate press.
                                self.cur_input_started = cur_time
                                self.last_input_time = cur_time
                                if pin in keys: return pin

                            elif cur_time - self.cur_input_started > self.first_repeat_threshold:
                                # We're good to relay this immediately as continuous input.
                                self.last_input_time = cur_time
                                if pin in keys: return pin

                else:
                    # --- PIN IS INACTIVE (RELEASED) ---
                    if self.cur_input == pin:
                        # Just Released
                        
                        # Handle Deferred Short Press Trigger
                        # If we were waiting for a potential Long Press, but released early, fire Short Press now.
                        if pin == HardwareButtonsConstants.KEY_PRESS_PIN and HardwareButtonsConstants.KEY_PRESS_LONG in keys:
                            if not self.long_press_fired:
                                # It was a short press
                                self.cur_input = None
                                self.last_input_time = cur_time
                                if HardwareButtonsConstants.KEY_PRESS_PIN in keys:
                                    return HardwareButtonsConstants.KEY_PRESS_PIN
                        
                        # Reset State
                        self.cur_input = None
                        self.long_press_fired = False

            # Free up CPU resources for main thread
            time.sleep(0.01) 


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
            if self.GPIO.input(key) == self.GPIO.LOW:
                self.update_last_input_time()
                return True
        else:
            return False


    def has_any_input(self) -> bool:
        """ Returns True if any of the keys are pressed """
        for key in HardwareButtonsConstants.ALL_KEYS:
            if self.GPIO.input(key) == GPIO.LOW:
                return True
        return False


# class used as short hand for static button/channel lookup values
class HardwareButtonsConstants:
    if GPIO.RPI_INFO['P1_REVISION'] == 3: #This indicates that we have revision 3 GPIO
        KEY_UP = 31
        KEY_DOWN = 35
        KEY_LEFT = 29
        KEY_RIGHT = 37
        KEY_PRESS = 33

        KEY1 = 40
        KEY2 = 38
        KEY3 = 36
    else:
        KEY_UP = 5
        KEY_DOWN = 11
        KEY_LEFT = 3
        KEY_RIGHT = 15
        KEY_PRESS = 7

        KEY1 = 16
        KEY2 = 12
        KEY3 = 8

    OVERRIDE = 1000
    KEY_PRESS_LONG = 1001

    KEY_PRESS_PIN = KEY_PRESS

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
    # Adding KEY_PRESS_LONG here allows it to be detected by default in base Screen.py
    KEYS__ANYCLICK = [KEY_PRESS, KEY1, KEY2, KEY3, KEY_PRESS_LONG]