import RPi.GPIO as GPIO
import time



class Buttons:
    KEY_UP_PIN = 6
    KEY_DOWN_PIN = 19
    KEY_LEFT_PIN = 5
    KEY_RIGHT_PIN = 26
    KEY_PRESS_PIN = 13

    KEY1_PIN = 21
    KEY2_PIN = 20
    KEY3_PIN = 16

    def __init__(self) -> None:
        #init GPIO
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(Buttons.KEY_UP_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)    # Input with pull-up
        GPIO.setup(Buttons.KEY_DOWN_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)  # Input with pull-up
        GPIO.setup(Buttons.KEY_LEFT_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)  # Input with pull-up
        GPIO.setup(Buttons.KEY_RIGHT_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP) # Input with pull-up
        GPIO.setup(Buttons.KEY_PRESS_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP) # Input with pull-up
        GPIO.setup(Buttons.KEY1_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)      # Input with pull-up
        GPIO.setup(Buttons.KEY2_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)      # Input with pull-up
        GPIO.setup(Buttons.KEY3_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)      # Input with pull-up

        self.GPIO = GPIO
        self.override_ind = False

        self.add_events([B.KEY_UP, B.KEY_DOWN, B.KEY_PRESS, B.KEY_LEFT, B.KEY_RIGHT, B.KEY1, B.KEY2, B.KEY3])

        # Track state over time so we can apply input delays/ignores as needed
        self.cur_input = None           # Track which direction or button was last pressed
        self.cur_input_started = None   # Track when that input began
        self.last_input_time = int(time.time() * 1000)  # How long has it been since the last input?
        self.first_repeat_threshold = 175  # Long-press time required before returning continuous input
        self.next_repeat_threshold = 250  # Amount of time where we no longer consider input a continuous hold


    def wait_for(self, keys=[], check_release=True, release_keys=[]) -> int:
        if not release_keys:
            release_keys = keys
        self.override_ind = False
        while True:
            for key in keys:
                if not check_release or ((check_release and key in release_keys and B.release_lock) or check_release and key not in release_keys):
                    # when check release is False or the release lock is released (True)
                    if self.GPIO.input(key) == GPIO.LOW or self.override_ind:
                        B.release_lock = False
                        if self.override_ind:
                            self.override_ind = False
                            return B.OVERRIDE

                        if self.cur_input != key:
                            self.cur_input = key
                            self.cur_input_started = int(time.time() * 1000)  # in milliseconds
                            self.last_input_time = self.cur_input_started
                            return key

                        else:
                            # Still pressing the same input
                            cur_time = int(time.time() * 1000)

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


    def add_events(self, keys=[]):
        for key in keys:
            GPIO.add_event_detect(key, self.GPIO.RISING, callback=Buttons.rising_callback)


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
        return self.GPIO.input(key) == self.GPIO.LOW



# class used as short hand for static button/channel lookup values
# TODO: Implement `release_lock` functionality as a global somewhere. Mixes up design
#   patterns to have a static constants class plus a settable global value.
class B:
    KEY_UP = 6
    KEY_DOWN = 19
    KEY_LEFT = 5
    KEY_RIGHT = 26
    KEY_PRESS = 13
    KEY1 = 21
    KEY2 = 20
    KEY3 = 16
    OVERRIDE = 1000

    release_lock = True # released when True, locked when False
