#!/usr/bin/env python
import sys
import json
import pika
import socket
import rabbitmq_config as rcfg

if len(sys.argv) < 2:
    sys.stderr.write("Usage: {} USERNAME [FULL_NAME] [REASON]".format(sys.argv[0]))
    exit(1)

node = 'ohpc'
user_name = sys.argv[1]
full_name = sys.argv[2] if len(sys.argv) >= 3 else ''
reason    = sys.argv[3] if len(sys.argv) >= 4 else ''

message = {
    "username": user_name,
    "fullname": full_name,
    "reason": reason
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
print("Account for user: {}, requested.".format(user_name))

connection.close()
