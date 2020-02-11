#!/usr/bin/env python
import pika # python client
import sys
import rabbit_config as rcfg
import socket
import subprocess
import time
import json

hostname = socket.gethostname().split(".", 1)[0]
connect_host = rcfg.Server if hostname != rcfg.Server else "localhost"
queue_name = "ood_account_create"
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

print "connection established. Listening for messages:"

# create exchange to pass messages
channel.exchange_declare(exchange=rcfg.Exchange, exchange_type='direct')

# creates a random name for the newly generated queue
result = channel.queue_declare(queue=queue_name, exclusive=False)

channel.queue_bind(exchange=rcfg.Exchange, queue=queue_name, routing_key=queue_name)

def slurm_account_create(ch, method, properties, body):
    msg = json.loads(body)
    print("Message received {}".format(msg))
    username = msg['username']
    user_uid = str(msg['uid'])
    user_gid = str(msg['gid'])
    try:
        subprocess.call(["sudo", "groupadd", "-r", "-g", user_gid, username])
        subprocess.call(["sudo", "useradd", "-u", user_uid, "-g", user_gid, "-m", username])
    except:
        print("Failed to create user")

    channel.basic_ack(delivery_tag=method.delivery_tag)

    channel.basic_publish(exchange=rcfg.Exchange, routing_key='slurm_add_account', body=json.dumps(msg))


# ingest messages
channel.basic_consume(queue=queue_name, on_message_callback=slurm_account_create)

# initiate message ingestion
try:
    channel.start_consuming()
except KeyboardInterrupt:
    print("Disconnecting from broker.")
    channel.stop_consuming()

connection.close()
