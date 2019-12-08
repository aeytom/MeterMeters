
from BaseMeter import BaseMeter
from Config import Config
from datetime import datetime, timedelta
from RPi import GPIO


class FerrarisMeter(BaseMeter):
    """ hold data for Ferraris meter counting"""

    def __init__(self, config, name="current", gpio=27, rpkwh=75, meter=0.0):
        if (meter > 0):
            parameters = {
                "gpio_channel": gpio,
                "rotations_per_kilo_watt_hour": rpkwh
            }
        else:
            parameters = {}
        BaseMeter.__init__(self, config=config, name=name,
                           meter=meter, parameters=parameters)

        self.tsMeasure = None
        self.logger().info("%s init gpio %d rotations_per_kwh=%d meter=%.2f" %
                           (self.name, self.gpio(), self.rpkwh(), self.meter))
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self.gpio(), GPIO.IN)
        GPIO.add_event_detect(self.gpio(), GPIO.BOTH,
                              callback=self.measure, bouncetime=200)

    def gpio(self):
        return self.parameters["gpio_channel"]

    def rpkwh(self):
        return self.parameters["rotations_per_kilo_watt_hour"]

    def measure(self, gpio_channel):
        now = datetime.now()
        if GPIO.input(self.gpio()):
            if self.tsMeasure == None:
                self.tsMeasure = now
        elif self.tsMeasure != None:
            delta = now - self.tsMeasure
            if delta.total_seconds() > 1:
                self.tsMeasure = None
                self.addMeter(
                    1 / self.rpkwh())
                self.logger().info("%s gpio %2d - %.2f delta %f" % (self.name,
                                                                    self.gpio(), self.meter, delta.total_seconds()))
                self.writeInflux()
