
from influxdb import InfluxDBClient
import threading


class InfluxWriterThread(threading.Thread):

    lock = threading.Lock

    def __init__(self, client, body, logger):
        threading.Thread.__init__(self)
        self.client = client
        self.body = body
        self.logger = logger

    def run(self):
        InfluxWriterThread.lock.acquire()
        try:
            self.client.write_points(self.body)
        except influxdb.exceptions.InfluxDBClientError as ex:
            self.logger.exception(ex)
        InfluxWriterThread.lock.release()
