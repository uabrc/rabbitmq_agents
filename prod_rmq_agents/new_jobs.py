#!/usr/bin/env python
import os
import json
import pika
import rc_util
from os import popen
from pathlib import Path
from rc_rmq import RCRMQ
import rabbit_config as rcfg

task = "new_jobs"

args = rc_util.get_args()
logger = rc_util.get_logger(args)

# Instantiate rabbitmq object
rc_rmq = RCRMQ({"exchange": rcfg.Exchange, "exchange_type": "topic"})


def new_jobs(ch, method, properties, body):
    msg = json.loads(body)
    username = msg["username"]
    action = msg["action"]
    msg["task"] = task
    queuename = msg["queuename"]

    try:
        block_new_jobs_cmd = f"/cm/shared/apps/slurm/19.05.5/bin/sacctmgr --immediate update user {username} set maxjobs=0"
        unblock_new_jobs_cmd = f"/cm/shared/apps/slurm/19.05.5/bin/sacctmgr --immediate update user {username} set maxjobs=-1"

        if action == 'lock':
            block_new_jobs = popen(block_new_jobs_cmd).read().rstrip()
        elif action == 'unlock':
            unblock_new_jobs = popen(unblock_new_jobs_cmd).read().rstrip()

        msg["success"] = True
        logger.info(f"Succeeded in blocking {username}'s jobs getting to run state")

    except Exception:
        msg["success"] = False
        msg["errmsg"] = "Exception raised while setting maxjobs that can enter run state, check the logs for stack trace"
        logger.error("", exc_info=True)


    rc_rmq.publish_msg(
        {"routing_key": f'acctmgr.done.{queuename}', 
         "msg": msg}
    )

    logger.debug(f"User {username} confirmation sent for {action}ing {task}")

    ch.basic_ack(delivery_tag=method.delivery_tag)


logger.info(f"Start listening to queue: {task}")
rc_rmq.bind_queue(queue=task, routing_key='lock.*', durable=True)
rc_rmq.bind_queue(queue=task, routing_key='unlock.*', durable=True)
rc_rmq.bind_queue(queue=task, routing_key='newjobs.*', durable=True)
rc_rmq.start_consume(
    {"queue": task, "cb": new_jobs}
)

logger.info("Disconnected")
rc_rmq.disconnect()
