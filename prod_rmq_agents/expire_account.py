#!/usr/bin/env python
import json
from datetime import date, timedelta
from os import popen

import rabbit_config as rcfg
import rc_util
from rc_rmq import RCRMQ

task = "expire_account"

args = rc_util.get_args()
logger = rc_util.get_logger(args)

# Instantiate rabbitmq object
rc_rmq = RCRMQ({"exchange": rcfg.Exchange, "exchange_type": "topic"})


def expire_account(ch, method, properties, body):
    msg = json.loads(body)
    username = msg["username"]
    action = msg["action"]
    msg["task"] = task
    queuename = msg["queuename"]
    yesterday = date.today() - timedelta(days=1)

    try:
        expire_account_cmd = (
            f'/cm/local/apps/cmd/bin/cmsh -n -c "user;use {username}; set'
            f' expirationdate {yesterday}; commit;"'
        )
        unexpire_account_cmd = (
            f'/cm/local/apps/cmd/bin/cmsh -n -c "user;use {username}; set'
            ' expirationdate 2037/12/31; commit;"'
        )

        if action == "lock":
            block_ssh = popen(expire_account_cmd).read().rstrip()
        elif action == "unlock":
            unblock_ssh = popen(unexpire_account_cmd).read().rstrip()

        msg["success"] = True
        logger.info(f"ssh expiration set to yesterday for user {username}")

    except Exception:
        msg["success"] = False
        msg["errmsg"] = (
            "Exception raised, while expiring user's ssh access, check the"
            " logs for stack trace"
        )
        logger.error("", exc_info=True)

    # send response to callback queue with it's correlation ID
    rc_rmq.publish_msg(
        {"routing_key": f"acctmgr.done.{queuename}", "msg": msg}
    )

    logger.debug(f"User {username} confirmation sent for {action}ing {task}")

    ch.basic_ack(delivery_tag=method.delivery_tag)


logger.info(f"Start listening to queue: {task}")
rc_rmq.bind_queue(queue=task, routing_key="lock.*", durable=True)
rc_rmq.bind_queue(queue=task, routing_key="unlock.*", durable=True)
rc_rmq.bind_queue(queue=task, routing_key="expiration.*", durable=True)

rc_rmq.start_consume({"queue": task, "cb": expire_account})

logger.info("Disconnected")
rc_rmq.disconnect()
