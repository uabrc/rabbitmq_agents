#!/usr/bin/env python
import os
import json
import rc_util
from pathlib import Path
from rc_rmq import RCRMQ
import rabbit_config as rcfg

task = "block_ssh"

args = rc_util.get_args()
logger = rc_util.get_logger(args)

# Instantiate rabbitmq object
rc_rmq = RCRMQ({"exchange": "", "exchange_type": "topic"})


def block_ssh(ch, method, properties, body):
    msg = json.loads(body)
    username = msg["username"]
    msg["task"] = task
    msg["success"] = False

    reply_to = properties.reply_to

    block_ssh_cmd = f"/cm/local/apps/cmd/bin/cmsh -n -c "group; use nossh; append members {username}; commit;""
    block_ssh = popen(block_ssh_cmd).read().rstrip()

    msg["success"] = True

    except Exception:
        msg["success"] = False
        msg["errmsg"] = "Exception raised, check the logs for stack trace"
        logger.error("", exc_info=True)

    # send confirm message
    rc_rmq.publish_msg(
        {"routing_key": reply_to,
         "props": pika.BasicProperties(
                            reply_to = callback_queue,
                            ),
         "msg": msg}
    )

    logger.debug(f"User {username} confirmation sent for {task}")

    ch.basic_ack(delivery_tag=method.delivery_tag)


logger.info(f"Start listening to queue: {task}")
rc_rmq.start_consume(
    {"queue": task, "routing_key": "block.*", "cb": block_ssh}
)
rc_rmq.start_consume(
    {"queue": task, "routing_key": "block.ssh.*", "cb": block_ssh}
)

logger.info("Disconnected")
rc_rmq.disconnect()
