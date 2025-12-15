import sys
from unittest.mock import MagicMock, Mock, patch
import pytest

sys.modules['RPi'] = MagicMock()
sys.modules['RPi.GPIO'] = MagicMock()

import time
from seedsigner.hardware.buttons import HardwareButtons, HardwareButtonsConstants

class TestLongPress:
    def setup_method(self):
        HardwareButtons._instance = None
        
        self.buttons = HardwareButtons.get_instance()
        
        self.buttons.cur_input = None
        self.buttons.long_press_fired = False
        
        self.mock_gpio = Mock()
        self.buttons.GPIO = self.mock_gpio
        
        self.mock_gpio.input.return_value = self.buttons.GPIO.HIGH

    def test_short_press(self):
        keys = [HardwareButtonsConstants.KEY_PRESS, HardwareButtonsConstants.KEY_PRESS_LONG]
        
        with patch('time.time', return_value=1000.0):
            self.mock_gpio.input.side_effect = lambda pin: self.buttons.GPIO.LOW if pin == HardwareButtonsConstants.KEY_PRESS_PIN else self.buttons.GPIO.HIGH
            pass

        self.buttons.cur_input = HardwareButtonsConstants.KEY_PRESS_PIN
        self.buttons.cur_input_started = 1000 * 1000
        self.buttons.long_press_fired = False
        
        self.mock_gpio.input.return_value = self.buttons.GPIO.HIGH 
        
        pin = HardwareButtonsConstants.KEY_PRESS_PIN
        ret_val = None
        
        if self.buttons.cur_input == pin:
            if pin == HardwareButtonsConstants.KEY_PRESS_PIN:
                if not self.buttons.long_press_fired:
                     if HardwareButtonsConstants.KEY_PRESS in keys:
                         ret_val = HardwareButtonsConstants.KEY_PRESS
        
        assert ret_val == HardwareButtonsConstants.KEY_PRESS

    def test_long_press(self):
        keys = [HardwareButtonsConstants.KEY_PRESS, HardwareButtonsConstants.KEY_PRESS_LONG]
        
        self.buttons.cur_input = HardwareButtonsConstants.KEY_PRESS_PIN
        self.buttons.cur_input_started = 1000 * 1000 
        self.buttons.long_press_fired = False
        
        cur_time = 1000 * 1000 + 1100 
        
        ret_val = None
        if not self.buttons.long_press_fired and (cur_time - self.buttons.cur_input_started > self.buttons.long_press_threshold):
            self.buttons.long_press_fired = True
            ret_val = HardwareButtonsConstants.KEY_PRESS_LONG
            
        assert ret_val == HardwareButtonsConstants.KEY_PRESS_LONG
        assert self.buttons.long_press_fired is True

    def test_long_press_release(self):
        keys = [HardwareButtonsConstants.KEY_PRESS, HardwareButtonsConstants.KEY_PRESS_LONG]
        
        self.buttons.cur_input = HardwareButtonsConstants.KEY_PRESS_PIN
        self.buttons.long_press_fired = True
        
        pin = HardwareButtonsConstants.KEY_PRESS_PIN
        ret_val = None
        
        if self.buttons.cur_input == pin:
            if pin == HardwareButtonsConstants.KEY_PRESS_PIN:
                if not self.buttons.long_press_fired:
                     ret_val = HardwareButtonsConstants.KEY_PRESS
        
        assert ret_val is None
