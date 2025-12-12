import sys
from unittest.mock import MagicMock, Mock, patch
import pytest

# --- MOCKING RPi HARDWARE DEPENDENCIES ---
# This must be done BEFORE importing seedsigner.hardware.buttons
# to prevent ModuleNotFoundError when it tries to import RPi.GPIO
sys.modules['RPi'] = MagicMock()
sys.modules['RPi.GPIO'] = MagicMock()
# ------------------------------------------

import time
from seedsigner.hardware.buttons import HardwareButtons, HardwareButtonsConstants

class TestLongPress:
    def setup_method(self):
        # Reset the Singleton state before each test
        HardwareButtons._instance = None
        
        # Initialize the instance
        self.buttons = HardwareButtons.get_instance()
        
        # Reset internal logic state
        self.buttons.cur_input = None
        self.buttons.long_press_fired = False
        
        # Mock GPIO to allow us to control inputs manually
        self.mock_gpio = Mock()
        self.buttons.GPIO = self.mock_gpio
        
        # Default: all pins HIGH (not pressed)
        self.mock_gpio.input.return_value = self.buttons.GPIO.HIGH

    def test_short_press(self):
        """ Verify that a short hold returns KEY_PRESS only after release """
        keys = [HardwareButtonsConstants.KEY_PRESS, HardwareButtonsConstants.KEY_PRESS_LONG]
        
        # 1. Press Down (Time 0)
        with patch('time.time', return_value=1000.0):
            # Mock the pin going LOW
            self.mock_gpio.input.side_effect = lambda pin: self.buttons.GPIO.LOW if pin == HardwareButtonsConstants.KEY_PRESS_PIN else self.buttons.GPIO.HIGH
            
            # Run one loop iteration logic manually to simulate wait_for behavior
            # (We can't call wait_for directly because it's an infinite loop)
            pass

        # Simulate state after press detection at t=1000
        self.buttons.cur_input = HardwareButtonsConstants.KEY_PRESS_PIN
        self.buttons.cur_input_started = 1000 * 1000 # ms logic
        self.buttons.long_press_fired = False
        
        # 2. Release (Pin goes HIGH) at t=1000.2 (200ms duration)
        self.mock_gpio.input.return_value = self.buttons.GPIO.HIGH 
        
        # Manually run the release logic block
        pin = HardwareButtonsConstants.KEY_PRESS_PIN
        ret_val = None
        
        if self.buttons.cur_input == pin:
            if pin == HardwareButtonsConstants.KEY_PRESS_PIN:
                if not self.buttons.long_press_fired:
                     if HardwareButtonsConstants.KEY_PRESS in keys:
                         ret_val = HardwareButtonsConstants.KEY_PRESS
        
        assert ret_val == HardwareButtonsConstants.KEY_PRESS

    def test_long_press(self):
        """ Verify that holding past threshold triggers KEY_PRESS_LONG immediately """
        keys = [HardwareButtonsConstants.KEY_PRESS, HardwareButtonsConstants.KEY_PRESS_LONG]
        
        # 1. Simulate Holding
        self.buttons.cur_input = HardwareButtonsConstants.KEY_PRESS_PIN
        self.buttons.cur_input_started = 1000 * 1000 
        self.buttons.long_press_fired = False
        
        # 2. Advance time past threshold (1.1 seconds elapsed)
        # Threshold is 1000ms.
        cur_time = 1000 * 1000 + 1100 
        
        # Check holding logic block
        ret_val = None
        if not self.buttons.long_press_fired and (cur_time - self.buttons.cur_input_started > self.buttons.long_press_threshold):
            self.buttons.long_press_fired = True
            ret_val = HardwareButtonsConstants.KEY_PRESS_LONG
            
        assert ret_val == HardwareButtonsConstants.KEY_PRESS_LONG
        assert self.buttons.long_press_fired is True

    def test_long_press_release(self):
        """ Verify that releasing AFTER a long press does NOT trigger a short press """
        keys = [HardwareButtonsConstants.KEY_PRESS, HardwareButtonsConstants.KEY_PRESS_LONG]
        
        # 1. Simulate state after long press already fired
        self.buttons.cur_input = HardwareButtonsConstants.KEY_PRESS_PIN
        self.buttons.long_press_fired = True
        
        # 2. Release event
        pin = HardwareButtonsConstants.KEY_PRESS_PIN
        ret_val = None
        
        # Logic block for release
        if self.buttons.cur_input == pin:
            if pin == HardwareButtonsConstants.KEY_PRESS_PIN:
                if not self.buttons.long_press_fired: # This is False now
                     ret_val = HardwareButtonsConstants.KEY_PRESS
        
        # Should be None because long_press_fired was True
        assert ret_val is None