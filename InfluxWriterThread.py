
import logging
import threading
import influxdb

from Config import Config
from InfluxClient import InfluxClient

class WriterThread(threading.Thread):
    """
    """

    lock = threading.Lock()
    queueLock = threading.Lock()
    queue = []

    def __init__(self, config, body):
        threading.Thread.__init__(self)
        iconfig = config.Influx()
        self.client = InfluxClient(iconfig)
        self.logger = config.Logger()
        self.points = body

    def run(self):
        """
        push datapoints to influx db

        - add point to syncronized queue
        - copy queue content to local variable
        - write points to influxdb
        - restore queue on error
        """
        # get current queue
        WriterThread.queueLock.acquire()
        WriterThread.queue.extend(self.points)
        queue = WriterThread.queue.copy()
        WriterThread.queue.clear()
        WriterThread.queueLock.release()

        if Config.debugLevel > 0:
            self.logger.debug("write influxdb count=%d" % (len(queue)))

        # post queue items to db
        try:
            WriterThread.lock.acquire()
            self.client.write_points(queue)
            WriterThread.lock.release()
        except influxdb.exceptions.InfluxDBClientError as ex:
            WriterThread.lock.release()
            self.logger.exception(ex)
            # restore queue
            WriterThread.queueLock.acquire()
            WriterThread.queue.extend(queue)
            WriterThread.queueLock.release()
