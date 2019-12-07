#!/usr/bin/python3

from datetime import datetime, timedelta
from influxdb import InfluxDBClient
from RPi import GPIO
from time import sleep
import sqlite3
import sys


class FerrarisMeter:
    """ hold data for Ferraris meter counting"""
    ts = None
    name = "counter"
    count = 0
    gpio_channel = 0
    rotations_per_kilo_watt_hour = 375
    measure_base = 0.0

    def __init__(self, name, gpio_channel, rpkwh, meter):
        self.name = name
        self.gpio_channel = gpio_channel
        self.rotations_per_kilo_watt_hour = rpkwh
        self.meter_base = meter
        print("init gpio_channel '%d' %d %.2f" % (gpio_channel, rpkwh, meter))
        db.putCInfo(name, gpio_channel, rpkwh)
        GPIO.setup(gpio_channel, GPIO.IN)
        GPIO.add_event_detect(gpio_channel, GPIO.BOTH,
                              callback=self.measure, bouncetime=200)

    def get(self):
        val = "on" if GPIO.input(self.gpio_channel) else "off"
        print("gpio_channel %d val %s" % (self.gpio_channel, val))

    def measure(self, gpio_channel):
        now = datetime.now()
        if GPIO.input(self.gpio_channel):
            if self.ts == None:
              self.ts = now
        elif self.ts != None:
            delta = now - self.ts
            if delta.total_seconds() > 1 :
                self.ts = None
                self.count = self.count + 1
                meter = self.meter_base + (self.count / self.rotations_per_kilo_watt_hour)
                wattage = 3600 * 1000 / (self.rotations_per_kilo_watt_hour * delta.total_seconds())
                print("%s %s gpio %2d - %5.2f (%6d) delta %f" % (str(now), self.name,
                                                                    self.gpio_channel, meter, self.count, delta.total_seconds()))
                db = PersistentMeter(db_name)
                db.write(self.name, meter)
                self.writeInflux(meter, wattage, delta.total_seconds())

    def writeInflux(self, meter, wattage, delta):
        now = datetime.now()
        json_body = [
            {
                "measurement": "meter",
                "time": now.isoformat(),
                "tags": {
                    'meter': self.name
                },
                "fields": {
                    "value": meter,
                    "wattage": wattage,
                    "delta": delta
                }
            }
        ]
        influx_client.write_points(json_body)

class PersistentMeter:
    def __init__(self, dsn):
        self.db = sqlite3.connect(dsn)
        c = self.db.cursor()
        c.execute(
            '''CREATE TABLE IF NOT EXISTS meters (date text, name text, meter real)''')
        c.execute(
            '''CREATE TABLE IF NOT EXISTS cinfo (name text PRIMARY KEY, gpio INTEGER, rpv INTEGER)''')
        self.db.commit()

    def write(self, name, meter):
        c = self.db.cursor()
        now = datetime.now()
        params = (now.isoformat(), name, meter,)
        c.execute('INSERT INTO meters VALUES (?,?,?)', params)
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


db_name = 'counters.db'
influx_host = 'leothinksuse.fritz.box'
influx_port = 8086
influx_db = 'homemeter'
influx_user = 'homemeter'
influx_password = 'istgeheim'


GPIO.setmode(GPIO.BCM)
db = PersistentMeter(db_name)

influx_client = InfluxDBClient(host=influx_host, port=influx_port,
                           database=influx_db, username=influx_user, password=influx_password)
influx_client.create_database(influx_db)

if (len(sys.argv) >= 2):
    left_dat = FerrarisMeter('solar', 17, 375, float(sys.argv[1]))
    right_dat = FerrarisMeter('current', 27, 75, float(sys.argv[2]))
else:
    left_dat = db.getUpDown('solar')
    right_dat = db.getUpDown('current')

tic = 0
try:
    while True:
        tic = tic + 1
        sleep(1)
except KeyboardInterrupt:
    GPIO.cleanup()
    print("tics %d" % tic)
