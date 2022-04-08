#!/usr/bin/env python
import os
import json
import pika
import rc_util
from os import popen
from pathlib import Path
from rc_rmq import RCRMQ
import rabbit_config as rcfg

task = "ssh_access"

args = rc_util.get_args()
logger = rc_util.get_logger(args)

# Instantiate rabbitmq object
rc_rmq = RCRMQ({"exchange": "RegUsr", "exchange_type": "topic"})


def ssh_access(ch, method, properties, body):
    msg = json.loads(body)
    username = msg["username"]
    action = msg["action"]
    msg["success"] = False

    corr_id = properties.correlation_id
    reply_to = properties.reply_to

    try:
        block_ssh_cmd = f'/cm/local/apps/cmd/bin/cmsh -n -c "group; use nossh; append members {username}; commit;"'
        unblock_ssh_cmd = f'/cm/local/apps/cmd/bin/cmsh -n -c "group; use nossh; removefrom members {username}; commit;"'

        if action == 'lock':
            block_ssh = popen(block_ssh_cmd).read().rstrip()
        elif action == 'unlock':
            unblock_ssh = popen(unblock_ssh_cmd).read().rstrip()

        msg["success"] = True

    except Exception:
        msg["success"] = False
        msg["errmsg"] = "Exception raised, while blocking user's ssh access, check the logs for stack trace"
        logger.error("", exc_info=True)

    # send response to callback queue with it's correlation ID
    if reply_to:
        rc_rmq.publish_msg(
            {"routing_key": reply_to,
             "props": pika.BasicProperties(
                         correlation_id=corr_id,
                          ),
             "msg": msg}
        )

    logger.debug(f"User {username} confirmation sent for {action}ing {task}")

    ch.basic_ack(delivery_tag=method.delivery_tag)


logger.info(f"Start listening to queue: {task}")
rc_rmq.bind_queue(queue=task, routing_key='lock.*', durable=True)
rc_rmq.bind_queue(queue=task, routing_key='unlock.*', durable=True)
rc_rmq.bind_queue(queue=task, routing_key='ssh.*', durable=True)

rc_rmq.start_consume(
    {"queue": task, "cb": ssh_access}
)

logger.info("Disconnected")
rc_rmq.disconnect()
