#!/usr/bin/python3

from systemd import journal
from systemd.daemon import notify, Notification
from time import sleep
import getopt
import os
import signal
import sys

from BaseMeter import BaseMeter
from Config import Config
from FerrarisMeter import FerrarisMeter
from MagnetMeter import MagnetMeter



def usage():
    config.Logger().error("%s --help --verbose --current=[] --solar=[] --gas=[]" % (sys.argv[0]))


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


ALARM_INTERVAL = int(int(os.getenv("WATCHDOG_USEC", "30000000")) / 3000000)

config = Config()
solarMeter = None
currentMeter = None
gasMeter = None

try:
    opts, args = getopt.getopt(sys.argv[1:], "hc:s:g:", [
        "help", "current=", "solar=", "gas="])
except getopt.GetoptError as err:
    # print help information and exit:
    config.Logger().error(err)  # will print something like "option -a not recognized"
    usage()
    sys.exit(2)
for o, a in opts:
    if o == "-v":
        verbose = True
    elif o in ("-h", "--help"):
        usage()
        sys.exit()
    elif o in ("-g", "--gas"):
        gasMeter = MagnetMeter(config, float(a))
    elif o in ("-c", "--current"):
        currentMeter = FerrarisMeter(config, name="current", gpio=27, rpkwh=75, meter=float(a))
    elif o in ("-s", "--solar"):
        solarMeter = FerrarisMeter(config, name="solar", gpio=17, rpkwh=375, meter=float(a))
    elif o in ("-v", "--verbose"):
        Config.debugLevel = Config.debugLevel + 1
    else:
        assert False, "unhandled option"

if (currentMeter == None and gasMeter == None and solarMeter == None):
    currentMeter = FerrarisMeter(config, "current")
    solarMeter = FerrarisMeter(config, "solar")
    gasMeter = MagnetMeter(config)

notify(Notification.READY)
notify(Notification.WATCHDOG)
config.Logger().info("Watchdog alarm every %.2f sec" % (ALARM_INTERVAL))
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
    config.Logger().info("bye bye")


notify(Notification.STOPPING)
