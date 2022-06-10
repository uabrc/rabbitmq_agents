#!/usr/bin/env python
import json

from rc_rmq import RCRMQ

task = "task_name"

# Instantiate rabbitmq object
rc_rmq = RCRMQ({"exchange": "RegUsr", "exchange_type": "topic"})


# Define your callback function
def on_message(ch, method, properties, body):

    # Retrieve routing key
    routing_key = method.routing_key
    print(routing_key)

    # Retrieve message
    msg = json.loads(body)
    print(msg)

    # Do Something
    print(f"[{task}]: Callback called.")

    # Acknowledge message
    ch.basic_ack(delivery_tag=method.delivery_tag)


print(f"Start listening to queue: {task}")
rc_rmq.start_consume(
    {
        "queue": task,  # Define your Queue name
        "routing_key": "#",  # Define your routing key
        "cb": on_message,  # Pass in callback function you just define
    }
)
