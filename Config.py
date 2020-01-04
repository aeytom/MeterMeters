import logging
import os
import systemd


class Config:
    def __init__(self, loggerName="homemeter"):
        logging.basicConfig(level=logging.CRITICAL)
        logging.getLogger().addHandler(systemd.journal.JournaldLogHandler())
        self.logger = logging.getLogger(loggerName)
        self.logger.setLevel(logging.INFO)

    def Influx(self):
        return Influx()

    def Logger(self):
        return self.logger


class Influx:
    host = os.environ.get('INFLUX_HOST', 'influx.db')
    port = os.environ.get('INFLUX_PORT', 8086)
    db = os.environ.get('INFLUX_DB', 'homemeter')
    user = os.environ.get('INFLUX_USER')
    password = os.environ.get('INFLUX_PASSWORD')
