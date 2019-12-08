
from influxdb import InfluxDBClient
import threading

class WriterThread(threading.Thread):

    lock = threading.Lock()
    lockQueue = threading.Lock()
    queue = []

    def __init__(self, client, body, logger):
        threading.Thread.__init__(self)
        self.client = client
        self.logger = logger
        self.addPoint(body)

    def addPoint(self, body):
        self.lockQueue.acquire()
        self.queue.extend(body)
        self.lockQueue.release();

    def run(self):
        # get current queue
        self.lockQueue.acquire()
        queue = self.queue.copy()
        self.queue.clear()
        self.lockQueue.release()

        # post queue items to db
        WriterThread.lock.acquire()
        try:
            self.client.write_points(queue)
        except influxdb.exceptions.InfluxDBClientError as ex:
            self.logger.exception(ex)
            # restore queue
            self.lockQueue.acquire()
            queue.extend(self.queue)
            self.queue = queue
            self.lockQueue.release()
        WriterThread.lock.release()
