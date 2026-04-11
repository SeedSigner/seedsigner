from unittest.mock import MagicMock, Mock, patch

# Must import test base before the Controller
from base import BaseTest

from seedsigner.hardware.ups import UPS
from seedsigner.models.settings import Settings
from seedsigner.models.settings_definition import SettingsConstants, SettingsDefinition



class TestUPS(BaseTest):
    @classmethod
    def setup_class(cls):
        super().setup_class()

    def setup_method(self):
        super().setup_method()
        # Reset the UPS singleton so each test gets a fresh instance
        UPS._instance = None


    # -------------------------------------------------------------------------
    # probe() failure modes
    # -------------------------------------------------------------------------

    def test_probe_missing_smbus2_returns_false(self):
        """probe() should return False when smbus2 is not installed."""
        with patch.dict('sys.modules', {'smbus2': None}):
            ups = UPS.__new__(UPS)
            ups._present = False
            assert ups.probe() is False

    def test_probe_bus_missing_returns_false(self):
        """probe() should return False when /dev/i2c-1 does not exist."""
        mock_smbus2 = MagicMock()
        mock_smbus2.SMBus.return_value.__enter__.side_effect = FileNotFoundError
        with patch.dict('sys.modules', {'smbus2': mock_smbus2}):
            ups = UPS.__new__(UPS)
            ups._present = False
            assert ups.probe() is False

    def test_probe_oserror_returns_false(self):
        """probe() should return False on I2C read errors."""
        mock_smbus2 = MagicMock()
        mock_smbus2.SMBus.return_value.__enter__.return_value.read_i2c_block_data.side_effect = OSError
        with patch.dict('sys.modules', {'smbus2': mock_smbus2}):
            ups = UPS.__new__(UPS)
            ups._present = False
            assert ups.probe() is False

    def test_probe_permission_error_returns_false(self):
        """probe() should return False when I2C access is denied."""
        mock_smbus2 = MagicMock()
        mock_smbus2.SMBus.return_value.__enter__.side_effect = PermissionError
        with patch.dict('sys.modules', {'smbus2': mock_smbus2}):
            ups = UPS.__new__(UPS)
            ups._present = False
            assert ups.probe() is False

    def test_probe_success_sets_present(self):
        """probe() should return True and configure_instance should notify Settings."""
        mock_smbus2 = MagicMock()
        bus_mock = mock_smbus2.SMBus.return_value.__enter__.return_value
        # Return non-zero bus voltage bytes to indicate chip is present
        bus_mock.read_i2c_block_data.return_value = [0x1A, 0x40]
        with patch.dict('sys.modules', {'smbus2': mock_smbus2}):
            ups = UPS.__new__(UPS)
            ups._present = False
            result = ups.probe()
        assert result is True


    # -------------------------------------------------------------------------
    # Voltage-to-percent math
    # -------------------------------------------------------------------------

    def test_read_percent_not_present(self):
        """read_percent() should return None when HAT is not present."""
        ups = UPS.__new__(UPS)
        ups._present = False
        assert ups.read_percent() is None

    def test_read_percent_from_voltage_edges(self):
        """read_percent() should correctly map voltage to 0-100, clamped."""
        ups = UPS.__new__(UPS)
        ups._present = True

        cases = [
            (3.0, 0),    # VMIN  → 0 %
            (3.6, 50),   # midpoint
            (4.2, 100),  # VMAX  → 100 %
            (2.5, 0),    # below VMIN → clamped to 0
            (5.0, 100),  # above VMAX → clamped to 100
        ]
        for voltage, expected_pct in cases:
            with patch.object(ups, 'read_voltage', return_value=voltage):
                assert ups.read_percent() == expected_pct, f"voltage={voltage}"

    def test_read_percent_none_on_read_failure(self):
        """read_percent() should return None when read_voltage returns None."""
        ups = UPS.__new__(UPS)
        ups._present = True
        with patch.object(ups, 'read_voltage', return_value=None):
            assert ups.read_percent() is None


    # -------------------------------------------------------------------------
    # is_charging()
    # -------------------------------------------------------------------------

    def test_is_charging_positive_current(self):
        """is_charging() should return True when current exceeds the deadband."""
        ups = UPS.__new__(UPS)
        ups._present = True
        with patch.object(ups, 'read_current_ma', return_value=200.0):
            assert ups.is_charging() is True

    def test_is_charging_negative_current(self):
        """is_charging() should return False when current is negative (discharging)."""
        ups = UPS.__new__(UPS)
        ups._present = True
        with patch.object(ups, 'read_current_ma', return_value=-100.0):
            assert ups.is_charging() is False

    def test_is_charging_in_deadband(self):
        """is_charging() should return False for near-zero current (within 5 mA deadband)."""
        ups = UPS.__new__(UPS)
        ups._present = True
        with patch.object(ups, 'read_current_ma', return_value=3.0):
            assert ups.is_charging() is False

    def test_is_charging_read_failure(self):
        """is_charging() should return None when current cannot be read."""
        ups = UPS.__new__(UPS)
        ups._present = True
        with patch.object(ups, 'read_current_ma', return_value=None):
            assert ups.is_charging() is None


    # -------------------------------------------------------------------------
    # Settings integration
    # -------------------------------------------------------------------------

    def test_ups_absent_collapses_options(self):
        """handle_ups_state_change(ABSENT) should restrict the entry to DISABLED only."""
        Settings.handle_ups_state_change(UPS.ACTION__ABSENT)
        entry = SettingsDefinition.get_settings_entry(SettingsConstants.SETTING__BATTERY_INDICATOR)
        assert entry.selection_options == SettingsConstants.OPTIONS__ONLY_DISABLED
        assert self.settings.get_value(SettingsConstants.SETTING__BATTERY_INDICATOR) == SettingsConstants.OPTION__DISABLED
        assert entry.help_text == SettingsConstants.BATTERY_INDICATOR__NOT_DETECTED__HELP_TEXT

    def test_ups_detected_restores_options(self):
        """handle_ups_state_change(DETECTED) should open up ENABLED/DISABLED options."""
        # Start collapsed
        Settings.handle_ups_state_change(UPS.ACTION__ABSENT)
        # Then detect
        Settings.handle_ups_state_change(UPS.ACTION__DETECTED)
        entry = SettingsDefinition.get_settings_entry(SettingsConstants.SETTING__BATTERY_INDICATOR)
        assert entry.selection_options == SettingsConstants.OPTIONS__ENABLED_DISABLED
        assert entry.help_text == SettingsConstants.BATTERY_INDICATOR__DETECTED__HELP_TEXT

    def test_battery_indicator_default_disabled(self):
        """Battery indicator should default to DISABLED."""
        assert self.settings.get_value(SettingsConstants.SETTING__BATTERY_INDICATOR) == SettingsConstants.OPTION__DISABLED
