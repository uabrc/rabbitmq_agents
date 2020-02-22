import json
import pika
import socket
import rabbitmq_config as rcfg

class RCRMQ(object):

    USER = 'guest'
    PASSWORD = 'guest'
    HOST = 'localhost'
    PORT = 5672
    VHOST = '/'
    EXCHANGE = ''
    EXCHANGE_TYPE = 'direct'
    QUEUE = None
    DURABLE = False
    ROUTING_KEY = None

    def __init__(self, config=None):
        if config:
            if 'exchange' in config:
                self.EXCHANGE = config['exchange']
            if 'exchange_type' in config:
                self.EXCHANGE_TYPE = config['exchange_type']

        hostname = socket.gethostname().split(".", 1)[0]

        self.HOST = rcfg.Server if hostname != rcfg.Server else "localhost"
        self.USER = rcfg.User
        self.PASSWORD = rcfg.Password
        self.VHOST = rcfg.VHost
        self.PORT = rcfg.Port
        self._parameters = pika.ConnectionParameters(
                self.HOST,
                self.PORT,
                self.VHOST,
                pika.PlainCredentials(self.USER, self.PASSWORD))

    def connect(self):
        self._connection = pika.BlockingConnection(self._parameters)
        self._channel = self._connection.channel()
        self._channel.exchange_declare(
                exchange=self.EXCHANGE, 
                exchange_type=self.EXCHANGE_TYPE,
                durable=True)

        if self.QUEUE is not None:
            self._channel.queue_declare(queue=self.QUEUE, durable=self.DURABLE)
            self._channel.queue_bind(exchange=self.EXCHANGE,
                    queue=self.QUEUE,
                    routing_key=self.ROUTING_KEY)

    def disconnect(self):
        self._channel.close()
        self._connection.close()

    def publish_msg(self, obj):
        if 'routing_key' in obj:
            self.ROUTING_KEY = obj['routing_key']

        self.connect()

        self._channel.basic_publish(exchange=self.EXCHANGE,
                routing_key=self.ROUTING_KEY,
                body=json.dumps(obj['msg']))

        self.disconnect()

    def start_consume(self, obj):
        if 'queue' in obj:
            self.QUEUE = obj['queue']
            self.ROUTING_KEY = obj['routing_key'] if 'routing_key' in obj else self.QUEUE
        if 'durable' in obj:
            self.DURABLE = obj['durable']

        self.connect()

        self._consumer_tag = self._channel.basic_consume(self.QUEUE,obj['cb'])
        self._channel.start_consuming()

        self.disconnect()

    def stop_consume(self):
        self._channel.basic_cancel(self._consumer_tag)
        if not self.DURABLE:
            self._channel.queue_delete(self.QUEUE)
