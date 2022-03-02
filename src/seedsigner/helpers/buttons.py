
import time

import os
if not os.getenv("NOTAPI", False):
    import RPi.GPIO as GPIO

class Buttons:
    KEY_UP_PIN = 6
    KEY_DOWN_PIN = 19
    KEY_LEFT_PIN = 5
    KEY_RIGHT_PIN = 26
    KEY_PRESS_PIN = 13

    KEY1_PIN = 21
    KEY2_PIN = 20
    KEY3_PIN = 16

    def __init__(self, disp) -> None:
        #init GPIO
        # GPIO.setmode(GPIO.BCM)
        # GPIO.setup(Buttons.KEY_UP_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)    # Input with pull-up
        # GPIO.setup(Buttons.KEY_DOWN_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)  # Input with pull-up
        # GPIO.setup(Buttons.KEY_LEFT_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)  # Input with pull-up
        # GPIO.setup(Buttons.KEY_RIGHT_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP) # Input with pull-up
        # GPIO.setup(Buttons.KEY_PRESS_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP) # Input with pull-up
        # GPIO.setup(Buttons.KEY1_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)      # Input with pull-up
        # GPIO.setup(Buttons.KEY2_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)      # Input with pull-up
        # GPIO.setup(Buttons.KEY3_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)      # Input with pull-up

        self.disp = disp


        # self.GPIO = GPIO
        self.override_ind = False

        self.add_events([
            B.KEY_UP,
            B.KEY_DOWN,
            B.KEY_PRESS,
            B.KEY_LEFT,
            B.KEY_RIGHT,
            B.KEY1,
            B.KEY2,
            B.KEY3
        ])

        # Track state over time so we can apply input delays/ignores as needed
        self.cur_input = None           # Track which direction or button was last pressed
        self.cur_input_started = None   # Track when that input began
        self.last_input_time = int(time.time() * 1000)  # How long has it been since the last input?
        self.first_repeat_threshold = 175  # Long-press time required before returning continuous input
        self.next_repeat_threshold = 250  # Amount of time where we no longer consider input a continuous hold




    def wait_for(self, keys=[], check_release=True, release_keys=[]) -> int:
        print("wait_for")
        # TODO: Refactor to keep control in the Controller and not here
        from seedsigner.controller import Controller
        controller = Controller.get_instance()

        if not release_keys:
            release_keys = keys
        self.override_ind = False

        x = 0
        counter = 0
        while True:
            counter += 1
            cur_time = int(time.time() * 1000)
            # DONT WORRY ABOUT SCREENSAVER FOR NOW
            # if cur_time - self.last_input_time > controller.screensaver_activation_ms and not controller.screensaver.is_running:
            #     # Start the screensaver. Will block execution until input detected.
            #     controller.start_screensaver()

            #     # We're back. Update last_input_time to now.
                # self.update_last_input_time()

            #     # Freeze any further processing for a moment to avoid having the wakeup
            #     #   input register in the resumed UI.
            #     time.sleep(self.next_repeat_threshold / 1000.0)

            #     # Resume from a fresh loop
            #     continue

            # x += 1
            # # if x == 10:
            # #     self.window.update()
            if counter == 1000:
                counter = 0
                print(f"lock status: {B.release_lock}")

            for key in keys:
                # self.window.update()
                # print(f"looking for key: {key}")
                # if self.disp.button_state[key] == True:
                #     return key
                # time.sleep(0.1)
                
                if not check_release or \
                    ((check_release and key in release_keys and B.release_lock) or check_release and key not in release_keys):
                    # when check release is False or the release lock is released (True)
                    if self.disp.button_state[key] == False or self.override_ind:
                        B.release_lock = False
                        print("setting lock")
                        print
                        if self.override_ind:
                            self.override_ind = False
                            return B.OVERRIDE

                        if self.cur_input != key:
                            self.cur_input = key
                            self.cur_input_started = int(time.time() * 1000)  # in milliseconds
                            self.last_input_time = self.cur_input_started
                            print(f"new key press: {key}")
                            return key

                        else:
                            # Still pressing the same input
                            if cur_time - self.last_input_time > self.next_repeat_threshold:
                                # Too much time has elapsed to consider this the same
                                #   continuous input. Treat as a new separate press.
                                self.cur_input_started = cur_time
                                self.last_input_time = cur_time
                                print(f"still pressing: {key}")
                                return key

                            elif cur_time - self.cur_input_started > self.first_repeat_threshold:
                                # We're good to relay this immediately as continuous
                                #   input.
                                self.last_input_time = cur_time
                                print(f"continuous press: {key}")
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


    def lock_input(self, lock):
        pass

    def update_last_input_time(self):
        self.last_input_time = int(time.time() * 1000)


    def add_events(self, keys=[]):
        pass
        # for key in keys:
        #     GPIO.add_event_detect(key, self.GPIO.RISING, callback=Buttons.rising_callback)


    def rising_callback(channel):
        B.release_lock = True


    def trigger_override(self, force_release = False) -> bool:
        if force_release:
            B.release_lock = True

        if not self.override_ind:
            self.override_ind = True
            return True
        return False

    def force_release(self) -> bool:
        B.release_lock = True
        return True

    def check_for_low(self, key) -> bool:
        if self.disp.button_state[key] == False:
            self.update_last_input_time()
            return True
        else:
            return False

    def has_any_input(self) -> bool:
        for key in B.ALL_KEYS:
            if self.disp.button_state[key] == False:
                return True
        return False




# class used as short hand for static button/channel lookup values
# TODO: Implement `release_lock` functionality as a global somewhere. Mixes up design
#   patterns to have a static constants class plus a settable global value.
class B:
    # KEY_UP = 6
    # KEY_DOWN = 19
    # KEY_LEFT = 5
    # KEY_RIGHT = 26
    # KEY_PRESS = 13
    # KEY1 = 21
    # KEY2 = 20
    # KEY3 = 16

    KEY_UP = "UP"
    KEY_DOWN = "DOWN"
    KEY_LEFT = "LL"
    KEY_RIGHT = "RR"
    KEY_PRESS = "PRESS"
    KEY1 = "KEY1"
    KEY2 = "KEY2"
    KEY3 = "KEY3"
    # KEY1 = "K1"
    # KEY2 = "K2"
    # KEY3 = "K3"
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

    release_lock = True # released when True, locked when False
