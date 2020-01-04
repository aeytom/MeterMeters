import logging
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
    host = 'leothinksuse.fritz.box'
    port = 8086
    db = 'homemeter'
    user = 'homemeter'
    password = 'istgeheim'
