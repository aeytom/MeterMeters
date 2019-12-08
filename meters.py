#!/usr/bin/python3

from datetime import datetime, timedelta
from influxdb import InfluxDBClient
from RPi import GPIO
from systemd import journal
from systemd.daemon import notify, Notification
from time import sleep
import getopt
import logging
import os
import py_qmc5883l
import signal
import sys
import sqlite3

from BaseMeter import BaseMeter


class FerrarisMeter(BaseMeter):
    """ hold data for Ferraris meter counting"""

    def __init__(self, name, gpio_channel, rpkwh, meter):
        BaseMeter.__init__(self, name=name, meter=meter,
                           influx_client=influx_client, logger=logger, parameters={
                               "gpio_channel": gpio_channel,
                               "rotations_per_kilo_watt_hour": rpkwh})

        self.tsMeasure = None
        self.saveState()
        logger.info("%s init gpio %d rotations_per_kwh=%d meter=%.2f" %
                    (self.name, self.parameters["gpio_channel"], self.parameters["rotations_per_kilo_watt_hour"], self.meter))
        db.putCInfo(name, gpio_channel, rpkwh)
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(gpio_channel, GPIO.IN)
        GPIO.add_event_detect(gpio_channel, GPIO.BOTH,
                              callback=self.measure, bouncetime=200)

    def measure(self, gpio_channel):
        now = datetime.now()
        if GPIO.input(self.parameters["gpio_channel"]):
            if self.tsMeasure == None:
                self.tsMeasure = now
        elif self.tsMeasure != None:
            delta = now - self.tsMeasure
            if delta.total_seconds() > 1:
                self.tsMeasure = None
                self.addMeter(
                    1 / self.parameters["rotations_per_kilo_watt_hour"])
                logger.info("%s gpio %2d - %.2f delta %f" % (self.name,
                                                             self.parameters["gpio_channel"], self.meter, delta.total_seconds()))
                self.writeInflux()


class PersistentMeter:
    def __init__(self, dsn):
        self.db = sqlite3.connect(dsn)
        c = self.db.cursor()
        c.execute(
            '''CREATE TABLE IF NOT EXISTS meters (date text, name text, meter real)''')
        c.execute(
            '''CREATE TABLE IF NOT EXISTS cinfo (name text PRIMARY KEY, gpio INTEGER, rpv INTEGER)''')
        c.execute(
            '''CREATE TABLE IF NOT EXISTS gasinfo (date text, name text, meter real, minval integer, maxval integer)''')
        self.db.commit()

    def write(self, name, meter):
        c = self.db.cursor()
        now = datetime.now()
        params = (now.isoformat(), name, meter,)
        c.execute('INSERT INTO meters VALUES (?,?,?)', params)
        params = (name, (now - timedelta(days=7)).isoformat(),)
        c.execute('DELETE FROM meters WHERE name=? AND date<?', params)
        self.db.commit()

    def putCInfo(self, name, gpio, rpv):
        c = self.db.cursor()
        params = (name,)
        c.execute('DELETE FROM cinfo WHERE name=?', params)
        params = (name, gpio, rpv,)
        c.execute('INSERT INTO cinfo VALUES (?,?,?)', params)
        self.db.commit()

    def getUpDown(self, name):
        c = self.db.cursor()
        params = (name,)
        c.execute('SELECT * FROM cinfo WHERE name=?', params)
        cinfo = c.fetchone()
        c.execute(
            'SELECT meter FROM meters WHERE name=? ORDER BY date DESC LIMIT 1', params)
        mrow = c.fetchone()
        meter = mrow[0] if mrow != None else 0
        return FerrarisMeter(name, cinfo[1], cinfo[2], meter)

    def getGasInfo(self, name):
        c = self.db.cursor()
        params = (name,)
        c.execute('SELECT * FROM gasinfo WHERE name=?', params)
        info = c.fetchone()
        return info

    def putGasInfo(self, name, meter, minval, maxval):
        c = self.db.cursor()
        params = (name,)
        c.execute('DELETE FROM gasinfo WHERE name=?', params)
        params = (datetime.now().isoformat(), name, meter, minval, maxval,)
        c.execute('INSERT INTO gasinfo VALUES (?,?,?,?,?)', params)
        self.db.commit()


class MagnetRunner(BaseMeter):
    RANGE_HYSTERESIS = 0.2
    RANGE_CORRECTION_FACTOR = 0.05
    SAMPLING_DELAY = 0.5

    maxVal = -99999
    minVal = 99999
    ts = datetime.now()

    def __init__(self, meter):
        parameters = {}
        info = db.getGasInfo("gas")
        if (info != None):
            parameters = {"minVal": info[3], "maxVal": info[4]}
            meter = info[2]
        BaseMeter.__init__(self, name="gas", meter=meter,
                           influx_client=influx_client, logger=logger, measurement="gas", parameters=parameters)
        logger.info("%s init magnet runner %d <<< %d - meter=%.3f" %
                    (self.name, self.parameters["minVal"], self.parameters["maxVal"], self.meter))

    def run(self):
        sensor = py_qmc5883l.QMC5883L(output_range=py_qmc5883l.RNG_8G)
        expect = -1
        while True:
            sleep(MagnetRunner.SAMPLING_DELAY)
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
            # logger.info("gas %6d . %6d . %6d --- %.3f %d" %
            #       (self.parameters["minVal"], val, self.parameters["maxVal"], self.meter, expect))
            if (expect == -1):
                if (val < (self.parameters["minVal"] + MagnetRunner.RANGE_HYSTERESIS * range)):
                    expect = 1
                    self.parameters["minVal"] = self.parameters["minVal"] + \
                        MagnetRunner.RANGE_CORRECTION_FACTOR * range
                    continue
            if (expect == 1):
                if (val > (self.parameters["maxVal"] - MagnetRunner.RANGE_HYSTERESIS * range)):
                    expect = -1
                    self.parameters["maxVal"] = self.parameters["maxVal"] - \
                        MagnetRunner.RANGE_CORRECTION_FACTOR * range
                    self.addMeter(0.001)
                    self.writeInflux()
                    continue


def usage():
    logger.error("%s --help --current=[] --solar=[] --gas=[]" % (sys.argv[0]))


def tick_handler(signum, frame):
    signal.setitimer(signal.ITIMER_REAL, ALARM_INTERVAL)
    notify(Notification.WATCHDOG)

    if (solarMeter != None):
        try:
            with open('solar.txt') as f:
                line = f.readline()
                solarMeter.setCurrent(line.strip())
            os.remove('solar.txt')
        except FileNotFoundError:
            pass
        solarMeter.tick()
    if (currentMeter != None):
        try:
            with open('current.txt') as f:
                line = f.readline()
                currentMeter.setCurrent(line.strip())
            os.remove('current.txt')
        except FileNotFoundError:
            pass
        currentMeter.tick()
    if (gasMeter != None):
        try:
            with open('gas.txt') as f:
                line = f.readline()
                gasMeter.setCurrent(line.strip())
            os.remove('gas.txt')
        except FileNotFoundError:
            pass
        gasMeter.tick()


db_name = "counters.db"
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(sys.argv[0])
logger.addHandler(journal.JournaldLogHandler())

ALARM_INTERVAL = int(int(os.getenv("WATCHDOG_USEC", "30000000")) / 3000000)

influx_host = 'leothinksuse.fritz.box'
influx_port = 8086
influx_db = 'homemeter'
influx_user = 'homemeter'
influx_password = 'istgeheim'

db = PersistentMeter(db_name)

influx_client = InfluxDBClient(host=influx_host, port=influx_port,
                               database=influx_db, username=influx_user, password=influx_password)
influx_client.create_database(influx_db)

solarMeter = None
currentMeter = None
gasMeter = None

try:
    opts, args = getopt.getopt(sys.argv[1:], "hc:s:g:", [
        "help", "current=", "solar=", "gas="])
except getopt.GetoptError as err:
    # print help information and exit:
    logger.error(err)  # will print something like "option -a not recognized"
    usage()
    sys.exit(2)
for o, a in opts:
    if o == "-v":
        verbose = True
    elif o in ("-h", "--help"):
        usage()
        sys.exit()
    elif o in ("-g", "--gas"):
        gasMeter = MagnetRunner(float(a))
    elif o in ("-c", "--current"):
        currentMeter = FerrarisMeter('current', 27, 75, float(a))
    elif o in ("-s", "--solar"):
        solarMeter = FerrarisMeter('solar', 17, 375, float(a))
    else:
        assert False, "unhandled option"

if (currentMeter == None and gasMeter == None and solarMeter == None):
    currentMeter = db.getUpDown('current')
    solarMeter = db.getUpDown('solar')
    gasMeter = MagnetRunner(0)

notify(Notification.READY)
notify(Notification.WATCHDOG)
logger.info("Watchdog alarm every %.2f sec" % (ALARM_INTERVAL))
signal.signal(signal.SIGALRM, tick_handler)
signal.setitimer(signal.ITIMER_REAL, ALARM_INTERVAL)

tic = 0
try:
    if (gasMeter != None):
        gasMeter.run()
    else:
        while True:
            tic = tic + 1
            sleep(5)
except KeyboardInterrupt:
    GPIO.cleanup()
    logger.info("tics %d" % tic)


notify(Notification.STOPPING)
