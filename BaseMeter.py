
from datetime import datetime, timedelta
from InfluxWriterThread import InfluxWriterThread


class BaseMeter:
    """ base class of all meters """

    meter = 0.0
    currentDiff = 0.0

    def __init__(self, logger, influx_client, name, meter=0.0, measurement="meter"):
        self.logger = logger
        self.name = name
        self.ts = datetime.now()
        self.influx_client = influx_client
        self.meter = meter
        self.measurement = measurement

    def setMeter(self, meter):
        self.meter = meter

    def setCurrent(self, meter):
        if (meter > 0):
            self.currentDiff = meter - self.meter

    def writeInflux(self):
        self.ts = datetime.now()
        self.logger.info("%s meter %s val=%f" %
                         (__name__, self.name, self.meter))
        json_body = [
            {
                "measurement": self.measurement,
                "time": self.ts.isoformat(),
                "tags": {
                    "meter": self.name
                },
                "fields": {
                    "value": self.meter,
                }
            }
        ]
        InfluxWriterThread(self.influx_client, json_body, self.logger)

    def tick(self):
        if ((datetime.now() - self.ts).total_seconds() > 240):
            if (self.currentDiff != 0.0):
                self.logger.info("fix meter to %.3f diff=%.3f" % (self.meter, self.c))
                self.setMeter(self.meter + self.currentDiff * 0.1)
                self.currentDiff = self.currentDiff * 0.9
                if (abs(self.currentDiff) < 0.01):
                    self.currentDiff = 0.0
            self.writeInflux()
