#!/usr/bin/env python
import pika
import sys
import socket
import json
import rabbitmq_config as rcfg

if len(sys.argv) < 3:
    sys.stderr.write("Usage: {} TAG USERNAME ".format(sys.argv[0]))
    exit(1)

node = sys.argv[1]
user_name = sys.argv[2]

message = {
    "username": user_name,
    "fullname": "Full Name",
    "reason": "Reason1, Reason2."
}

hostname = socket.gethostname().split(".", 1)[0]
connect_host = rcfg.Server if hostname != rcfg.Server else "localhost"

# Set up credentials to connect to RabbitMQ server
credentials = pika.PlainCredentials(rcfg.User, rcfg.Password)
parameters = pika.ConnectionParameters(connect_host,
                                   rcfg.Port,
                                   rcfg.VHost,
                                   credentials)

# Establish connection to RabbitMQ server
connection = pika.BlockingConnection(parameters)
channel = connection.channel()
channel.exchange_declare(exchange=rcfg.Exchange, exchange_type='direct')

channel.basic_publish(exchange=rcfg.Exchange, routing_key=node, body=json.dumps(message))
print(" [x] Sent {}: {}".format(node, json.dumps(message)))

# creates a named queue
result = channel.queue_declare(queue=user_name, exclusive=False, durable=True)

# bind the queue with exchange
channel.queue_bind(exchange=rcfg.Exchange, queue=user_name, routing_key=user_name)

def work(ch, method, properties, body):
    msg = json.loads(body)
    print("Received message from {}: \n\t{}".format(method.routing_key, msg))
    #queue_unbind(queue, exchange=None, routing_key=None, arguments=None, callback=None)
    channel.queue_delete(method.routing_key)

# ingest messages, and assume delivered via auto_ack
channel.basic_consume(queue=sys.argv[2], on_message_callback=work, auto_ack=True)
print("Subscribing to queue: {}".format(sys.argv[2]))

# initiate message ingestion
try:
    channel.start_consuming()
except KeyboardInterrupt:
    print("Disconnecting from broker.")
    channel.stop_consuming()
connection.close()
