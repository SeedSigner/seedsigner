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

        return

    def wait_for(self, keys = [], check_release = True, release_keys = []) -> int:
        if not release_keys:
            release_keys = keys
        while True:
            for i in keys:
                if check_release == False or ((check_release == True and i in release_keys and B.release_lock == True) or check_release == True and i not in release_keys):
                    # when check release is False or the release lock is released (True)
                    if self.GPIO.input(i) == GPIO.LOW or self.override_ind == True:
                        B.release_lock = False
                        if self.override_ind == True:
                            self.override_ind = False
                            return B.OVERRIDE
                        return i
            time.sleep(0.01) # wait 10 ms to give CPU chance to do other things

    def add_events(self, keys = []):
        for i in keys:
            GPIO.add_event_detect(i, self.GPIO.RISING, callback=Buttons.rising_callback)

    def rising_callback(channel):
        B.release_lock = True
        return

    def trigger_override(self) -> bool:
        if self.override_ind == False:
            self.override_ind = True
            return True

        return False

    def check_for_low(self, key) -> bool:
        if self.GPIO.input(key) == self.GPIO.LOW:
            return True
        return False

# class used as short hand for static button/channel lookup values

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
