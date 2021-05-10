import json
import pika
import socket
import rabbit_config as rcfg


class RCRMQ(object):

    USER = "guest"
    PASSWORD = "guest"
    HOST = "localhost"
    PORT = 5672
    VHOST = "/"
    EXCHANGE = ""
    EXCHANGE_TYPE = "direct"
    QUEUE = None
    DURABLE = True
    ROUTING_KEY = None
    DEBUG = False

    def __init__(self, config=None, debug=False):
        if config:
            if "exchange" in config:
                self.EXCHANGE = config["exchange"]
            if "exchange_type" in config:
                self.EXCHANGE_TYPE = config["exchange_type"]

        hostname = socket.gethostname().split(".", 1)[0]

        self.HOST = rcfg.Server if hostname != rcfg.Server else "localhost"
        self.USER = rcfg.User
        self.PASSWORD = rcfg.Password
        self.VHOST = rcfg.VHost
        self.PORT = rcfg.Port
        self.DEBUG = debug

        if self.DEBUG:
            print(
                """
            Created RabbitMQ instance with:
              Exchange name: {},
              Exchange type: {},
              Host: {},
              User: {},
              VHost: {},
              Port: {}
            """.format(
                    self.EXCHANGE,
                    self.EXCHANGE_TYPE,
                    self.HOST,
                    self.USER,
                    self.VHOST,
                    self.PORT,
                )
            )

        self._consumer_tag = None
        self._connection = None
        self._consuming = False
        self._channel = None
        self._parameters = pika.ConnectionParameters(
            self.HOST,
            self.PORT,
            self.VHOST,
            pika.PlainCredentials(self.USER, self.PASSWORD),
        )

    def connect(self):
        if self.DEBUG:
            print(
                "Connecting...\n"
                + "Exchange: "
                + self.EXCHANGE
                + " Exchange type: "
                + self.EXCHANGE_TYPE
            )

        self._connection = pika.BlockingConnection(self._parameters)
        self._channel = self._connection.channel()
        self._channel.exchange_declare(
            exchange=self.EXCHANGE,
            exchange_type=self.EXCHANGE_TYPE,
            durable=True,
        )

    def bind_queue(self):
        self._channel.queue_declare(queue=self.QUEUE, durable=self.DURABLE)
        self._channel.queue_bind(
            exchange=self.EXCHANGE,
            queue=self.QUEUE,
            routing_key=self.ROUTING_KEY,
        )

    def disconnect(self):
        self._channel.close()
        self._connection.close()
        self._connection = None

    def delete_queue(self):
        self._channel.queue_delete(self.QUEUE)

    def publish_msg(self, obj):
        if "routing_key" in obj:
            self.ROUTING_KEY = obj["routing_key"]

        if self._connection is None:
            self.connect()

        self._channel.basic_publish(
            exchange=self.EXCHANGE,
            routing_key=self.ROUTING_KEY,
            body=json.dumps(obj["msg"]),
        )

    def start_consume(self, obj):
        if "queue" in obj:
            self.QUEUE = obj["queue"]
            self.ROUTING_KEY = (
                obj["routing_key"] if "routing_key" in obj else self.QUEUE
            )
        if "durable" in obj:
            self.DURABLE = obj["durable"]

        if self.DEBUG:
            print(
                "Queue: "
                + self.QUEUE
                + "\nRouting_key: "
                + self.ROUTING_KEY
            )

        if self._connection is None:
            self.connect()

        self.bind_queue()

        self._consumer_tag = self._channel.basic_consume(
            self.QUEUE, obj["cb"]
        )
        self._consuming = True
        try:
            self._channel.start_consuming()
        except KeyboardInterrupt:
            self._channel.stop_consuming()

    def stop_consume(self):
        self._channel.basic_cancel(self._consumer_tag)
