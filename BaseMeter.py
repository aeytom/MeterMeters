
from datetime import datetime, timedelta
from InfluxWriterThread import WriterThread
import json
import sqlite3


class BaseMeter:
    """ 
    base class of all meters 
    """

    def __init__(self, config, name, meter=0.0, measurement="meter", sqlite_dsn="counters.db", parameters={}):
        self.config = config
        self.name = name
        self.ts = datetime.now()
        self.measurement = measurement
        self.parameters = parameters
        self._init_sqlite(sqlite_dsn)
        self.restoreState()
        if (meter > 0):
            self.setMeter(meter)
        self.ticks = 0
        self.startMeter = self.getMeter()

    def _init_sqlite(self, dsn):
        """
        initialize internal sqlite database connection to prepare persistense of meter state
        """
        self.sqlite_dsn = dsn
        self.sqlite_db = self.db = sqlite3.connect(dsn)
        c = self.sqlite_db.cursor()
        c.execute(
            '''CREATE TABLE IF NOT EXISTS info (date text, name text PRIMARY KEY, meter real, parameters text)''')
        self.sqlite_db.commit()

    def addMeter(self, diff):
        """
        increment the meter value with the given difference
        """
        meter = self.getMeter() + diff
        self.setMeter(meter)

    def addTick(self, diff):
        """
        increment internal counter by one and update the current meter value

        similar to addMeter but uses a internal counter to avoid rounding errors
        """
        self.ticks = self.ticks + 1
        meter = self.startMeter + self.ticks * diff
        self.setMeter(meter)

    def getMeter(self):
        """
        get current internal meter value
        """
        return self.meter

    def setMeter(self, meter):
        """
        set current meter value
        """
        if (float(meter) > 0):
            self.meter = float(meter)
            self.saveState()

    def saveState(self):
        """
        save/backup current meter state
        """
        self.sqlite_db = self.db = sqlite3.connect(self.sqlite_dsn)
        c = self.sqlite_db.cursor()
        params = (self.name,)
        c.execute('DELETE FROM info WHERE name=?', params)
        params = (datetime.now().isoformat(), self.name,
                  self.meter, json.dumps(self.parameters),)
        c.execute('INSERT INTO info VALUES (?,?,?,?)', params)
        self.sqlite_db.commit()

    def restoreState(self):
        """
        restore meter state from saved state
        """
        self.sqlite_db = self.db = sqlite3.connect(self.sqlite_dsn)
        c = self.sqlite_db.cursor()
        params = (self.name,)
        c.execute('SELECT meter, parameters from info WHERE name=?', params)
        row = c.fetchone()
        if (row != None):
            self.meter = float(row[0])
            self.parameters = json.loads(row[1])

    def setCurrent(self, raw):
        """
        set corrected meter value at runtime

        reset internal counter
        """
        meter = float(raw)
        if (meter > 0.0):
            self.logger().info('set corrected meter %.3f diff=%.3f' %
                               (meter, meter - self.meter))
            self.setMeter(meter)
            self.startMeter = meter
            self.ticks = 0

    def writeInflux(self):
        """
        write current meter state to influxdb
        """
        self.ts = datetime.now()
        self.logger().info("%s meter %s val=%f (%f + %d * diff)" %
                           (__name__, self.name, self.meter, self.startMeter, self.ticks))
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
        writer = WriterThread(self.config, json_body)
        writer.start()

    def tick(self):
        """
        trigger periodic write to influxdb
        """
        if ((datetime.now() - self.ts).total_seconds() > 240):
            self.writeInflux()

    def logger(self):
        return self.config.Logger()
