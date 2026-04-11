import logging

from seedsigner.models.singleton import Singleton

logger = logging.getLogger(__name__)


class UPS(Singleton):
    ACTION__DETECTED = "ups__detected"
    ACTION__ABSENT   = "ups__absent"

    I2C_BUS     = 1
    INA219_ADDR = 0x43

    REG_CONFIG      = 0x00
    REG_SHUNT_VOLT  = 0x01  # signed 16-bit, 10 uV/LSB
    REG_BUS_VOLTAGE = 0x02  # bits [15:3], LSB = 4 mV

    SHUNT_OHMS = 0.1  # Waveshare UPS HAT (C) shunt resistor

    VMIN = 3.0   # 0 %
    VMAX = 4.2   # 100 %


    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            ups = cls.__new__(cls)
            ups._present = False
            cls._instance = ups
        return cls._instance


    @classmethod
    def configure_instance(cls):
        from seedsigner.models.settings import Settings
        instance = cls.get_instance()
        instance._present = instance.probe()
        action = cls.ACTION__DETECTED if instance._present else cls.ACTION__ABSENT
        Settings.handle_ups_state_change(action)


    def probe(self) -> bool:
        """Probe for an INA219 at I2C_ADDR. Returns True if the chip responds."""
        try:
            from smbus2 import SMBus
            with SMBus(self.I2C_BUS) as bus:
                # Write default config: 32 V range, 320 mV shunt, 12-bit, continuous
                config = 0x399F
                bus.write_i2c_block_data(
                    self.INA219_ADDR,
                    self.REG_CONFIG,
                    [(config >> 8) & 0xFF, config & 0xFF],
                )
                raw = bus.read_i2c_block_data(self.INA219_ADDR, self.REG_BUS_VOLTAGE, 2)
            return (raw[0] << 8 | raw[1]) != 0
        except Exception:
            return False


    def is_present(self) -> bool:
        return self._present


    def read_voltage(self) -> float | None:
        """Return bus voltage in volts, or None on read failure."""
        if not self._present:
            return None
        try:
            from smbus2 import SMBus
            with SMBus(self.I2C_BUS) as bus:
                raw = bus.read_i2c_block_data(self.INA219_ADDR, self.REG_BUS_VOLTAGE, 2)
            # Bits [15:3] are the bus voltage; LSB = 4 mV
            return ((raw[0] << 8 | raw[1]) >> 3) * 0.004
        except Exception:
            return None


    def read_current_ma(self) -> float | None:
        """Return shunt current in mA (positive = charging), or None on read failure."""
        if not self._present:
            return None
        try:
            from smbus2 import SMBus
            with SMBus(self.I2C_BUS) as bus:
                raw = bus.read_i2c_block_data(self.INA219_ADDR, self.REG_SHUNT_VOLT, 2)
            shunt_raw = raw[0] << 8 | raw[1]
            if shunt_raw > 0x7FFF:
                shunt_raw -= 0x10000
            shunt_uv = shunt_raw * 10  # 10 uV/LSB
            return (shunt_uv / 1000.0) / self.SHUNT_OHMS
        except Exception:
            return None


    def read_percent(self) -> int | None:
        """Return battery level as 0-100, or None if voltage cannot be read."""
        v = self.read_voltage()
        if v is None:
            return None
        pct = (v - self.VMIN) / (self.VMAX - self.VMIN) * 100.0
        return max(0, min(100, int(round(pct))))


    def is_charging(self) -> bool | None:
        """Return True if charging, False if discharging, None on read failure.

        Uses a 5 mA deadband to avoid jitter at rest.
        """
        ma = self.read_current_ma()
        if ma is None:
            return None
        return ma > 5
