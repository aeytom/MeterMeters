from BaseMeter import BaseMeter
from Config import Config
from time import sleep
import py_qmc5883l

class MagnetMeter(BaseMeter):
    RANGE_HYSTERESIS = 0.2
    RANGE_CORRECTION_FACTOR = 0.05
    SAMPLING_DELAY = 0.2

    def __init__(self, config, meter=0.0):
        if (meter == 0.0):
            parameters = {
                "maxVal": -99999,
                "minVal": 99999
            }
        else:
            parameters = {}
        BaseMeter.__init__(self, config=config, name="gas", measurement="gas", meter=meter, parameters=parameters)
        self.logger().info("%s init magnet runner %d <<< %d - meter=%.3f" %
                    (self.name, self.parameters["minVal"], self.parameters["maxVal"], self.meter))

    def run(self):
        sensor = py_qmc5883l.QMC5883L(output_range=py_qmc5883l.RNG_8G)
        expect = -1
        while True:
            sleep(MagnetMeter.SAMPLING_DELAY)
            m = sensor.get_magnet_raw()
            val = m[0]
            if (self.parameters["minVal"] > val):
                self.parameters["minVal"] = val
                continue
            if (self.parameters["maxVal"] < val):
                self.parameters["maxVal"] = val
                continue
            range = self.parameters["maxVal"] - self.parameters["minVal"]
            if (range < 10000):
                continue
            self.logger().debug("gas %6d . %6d . %6d --- %.3f %d" %
                  (self.parameters["minVal"], val, self.parameters["maxVal"], self.meter, expect))
            if (expect == -1):
                if (val < (self.parameters["minVal"] + MagnetMeter.RANGE_HYSTERESIS * range)):
                    expect = 1
                    self.parameters["minVal"] = self.parameters["minVal"] + \
                        MagnetMeter.RANGE_CORRECTION_FACTOR * range
                    continue
            if (expect == 1):
                if (val > (self.parameters["maxVal"] - MagnetMeter.RANGE_HYSTERESIS * range)):
                    expect = -1
                    self.parameters["maxVal"] = self.parameters["maxVal"] - \
                        MagnetMeter.RANGE_CORRECTION_FACTOR * range
                    self.addMeter(0.001)
                    self.writeInflux()
                    continue