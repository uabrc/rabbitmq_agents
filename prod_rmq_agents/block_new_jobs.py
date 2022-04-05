#!/usr/bin/env python
import os
import json
import rc_util
from pathlib import Path
from rc_rmq import RCRMQ
import rabbit_config as rcfg

task = "block_new_jobs"

args = rc_util.get_args()
logger = rc_util.get_logger(args)

# Instantiate rabbitmq object
rc_rmq = RCRMQ({"exchange": "", "exchange_type": "topic"})


def block_new_jobs(ch, method, properties, body):
    msg = json.loads(body)
    username = msg["username"]
    msg["task"] = task
    msg["success"] = False

    reply_to = properties.reply_to

    try:
        block_ssh_cmd = f"/cm/shared/apps/slurm/19.05.5/bin/sacctmgr --immediate update user {username} set maxjobs=0"
        block_ssh = popen(block_ssh_cmd).read().rstrip()

    msg["success"] = True

    except Exception:
        msg["success"] = False
        msg["errmsg"] = "Exception raised while setting maxjobs that can enter run state, check the logs for stack trace"
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
    {"queue": task, "routing_key": "block.*", "cb": block_new_jobs}
)
rc_rmq.start_consume(
    {"queue": task, "routing_key": "block.newjobs.*", "cb": block_new_jobs}
)

logger.info("Disconnected")
rc_rmq.disconnect()
