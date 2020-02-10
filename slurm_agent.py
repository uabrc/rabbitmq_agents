#!/usr/bin/env python
import pika # python client
import sys
import rabbit_config as rcfg
import socket

import time

hostname = socket.gethostname().split(".", 1)[0]
connect_host = rcfg.Server if hostname != rcfg.Server else "localhost"
queue_name = "slurm_add_account"
duration = 2

# Set up credentials to connect to RabbitMQ server
credentials = pika.PlainCredentials(rcfg.User, rcfg.Password)
parameters = pika.ConnectionParameters(connect_host,
                                   rcfg.Port,
                                   rcfg.VHost,
                                   credentials)

# Establish connection to RabbitMQ server
connection = pika.BlockingConnection(parameters)
channel = connection.channel()

# create exchange to pass messages
channel.exchange_declare(exchange=rcfg.Exchange, exchange_type='direct')

# creates a random name for the newly generated queue
result = channel.queue_declare(queue=queue_name, exclusive=False)

channel.queue_bind(exchange=rcfg.Exchange, queue=queue_name, routing_key=queue_name)

