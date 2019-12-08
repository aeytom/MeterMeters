import logging
import systemd

class Config:
    def __init__(self, loggerName):
        logging.basicConfig(level=logging.DEBUG)
        self.logger = logging.getLogger(loggerName)
        self.logger.addHandler(systemd.journal.JournaldLogHandler())

    def influx(self): 
        return Influx()

    def logger(self, name=None):
        return self.logger


class Influx:
    host = 'leothinksuse.fritz.box'
    port = 8086
    db = 'homemeter'
    user = 'homemeter'
    password = 'istgeheim'
