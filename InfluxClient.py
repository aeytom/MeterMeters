
from influxdb import InfluxDBClient

class InfluxClient:
    """
    provide an influxdb client
    """

    def __init__(self, config):
        self.client = InfluxDBClient(host=config.host, port=config.port,
                                     database=config.db, username=config.user, password=config.password)
        self.client.create_database(config.db)

    def write_points(self, points):
        return self.client.write_points(points)
