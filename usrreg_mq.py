import rabbitmq_config as rcfg

class UserRegMQ(object):

    USER = 'guest'
    PASSWORD = 'guest'
    HOST = 'localhost'
    PORT = 5672
    VHOST = '/'
    EXCHANGE = ''
    EXCHANGE_TYPE = 'direct'
    QUEUE = ''

    def __init__(self, config=None):
        if config:
            if 'exchange' in config:
                self.EXCHANGE = config['exchange']
            if 'queue' in config:
                self.QUEUE = config['queue']

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
                exchange_type=self.EXCHANGE_TYPE
                durable=True)

    def close(self):
        self._connection.close()

    def publish_msg(self, obj):
        if self._channel is None or not self._channel.is_open:
            return
        
        # Establish connection to RabbitMQ server
        self.connect()
        self._channel.basic_publish(exchange=self.EXCHANGE, routing_key=obj['routing_key'], body=json.dumps(obj['msg']))
        self.disconnect()

